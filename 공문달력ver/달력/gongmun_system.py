# -*- coding: utf-8 -*-
"""
gongmun_system.py  -  윈도우와 맞닿는 부분 (화면 그리기와 상관없는 도우미)

  1) 파일 끌어다 놓기     : 창에 PDF 를 끌어 놓으면 경로를 받는다 (추가 설치 없이 ctypes)
  2) 윈도우 시작 시 실행  : 로그인할 때 위젯이 자동으로 뜨게 등록/해제
  3) 폴더 감시           : 다운로드 폴더에 새 PDF 가 들어오면 알려 준다
"""
import os
import queue
import sys
import time

IS_WIN = sys.platform == "win32"


# ──────────────────────────────────────────────────────────────
# 1. 파일 끌어다 놓기 (Windows WM_DROPFILES)
#    창 프로시저 안에서는 Tk 를 부르면 안 되므로 큐에 넣고, after() 로 꺼내 쓴다.
#    (공문 제목 바꾸기 프로그램의 방식을 그대로 가져옴)
# ──────────────────────────────────────────────────────────────
def enable_file_drop(win, on_drop):
    """win(창)에 파일을 끌어 놓으면 on_drop([경로, ...]) 를 부른다. 안 되는 환경이면 False."""
    if not IS_WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        WM_DROPFILES, WM_COPYGLOBALDATA, GWLP_WNDPROC = 0x0233, 0x0049, -4
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallWindowProcW.restype = LRESULT
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [ctypes.c_void_p]

        win.update_idletasks()
        hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
        sink = queue.Queue()

        def wndproc(h, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                paths = []
                count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                for i in range(count):
                    n = shell32.DragQueryFileW(wparam, i, None, 0)
                    buf = ctypes.create_unicode_buffer(n + 1)
                    shell32.DragQueryFileW(wparam, i, buf, n + 1)
                    paths.append(buf.value)
                shell32.DragFinish(wparam)
                sink.put(paths)
                return 0
            return user32.CallWindowProcW(prev, h, msg, wparam, lparam)

        proc = WNDPROC(wndproc)
        prev = user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, ctypes.cast(proc, ctypes.c_void_p))
        if not prev:
            return False
        win._drop_proc_ref = proc                       # 가비지 수집 방지
        try:
            for m in (WM_DROPFILES, WM_COPYGLOBALDATA):
                user32.ChangeWindowMessageFilterEx(hwnd, m, 1, None)
        except Exception:
            pass
        shell32.DragAcceptFiles(hwnd, True)

        def poll():
            try:
                while True:
                    on_drop(sink.get_nowait())
            except queue.Empty:
                pass
            if win.winfo_exists():
                win.after(150, poll)
        win.after(150, poll)
        return True
    except Exception:
        return False


def expand_paths(paths, exts=(".pdf", ".hwpx", ".txt")):
    """끌어 놓은 것 중 폴더는 안의 파일까지 펼쳐서, 공문 파일만 돌려준다."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                full = os.path.join(p, name)
                if os.path.isfile(full) and name.lower().endswith(exts):
                    out.append(full)
        elif os.path.isfile(p) and p.lower().endswith(exts):
            out.append(p)
    return out


# ──────────────────────────────────────────────────────────────
# 2. 윈도우 시작할 때 위젯 자동 실행 (HKCU\...\Run 에 한 줄 등록)
# ──────────────────────────────────────────────────────────────
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "GongmunCalendarWidget"


def autostart_command():
    if getattr(sys, "frozen", False):                   # exe 로 만든 경우
        return '"%s" --widget' % sys.executable
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")   # 검은 창 없이 실행
    if os.path.isfile(pyw):
        exe = pyw
    script = os.path.abspath(sys.modules["__main__"].__file__)
    return '"%s" "%s" --widget' % (exe, script)


def autostart_supported():
    return IS_WIN


def autostart_enabled():
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(on):
    if not IS_WIN:
        raise OSError("윈도우에서만 쓸 수 있는 기능입니다.")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, _RUN_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(k, _RUN_NAME)
            except FileNotFoundError:
                pass


# ──────────────────────────────────────────────────────────────
# 3. 폴더 감시 (다운로드 폴더에 새 공문이 들어오면)
# ──────────────────────────────────────────────────────────────
def default_download_dir():
    home = os.path.expanduser("~")
    for name in ("Downloads", "다운로드"):
        p = os.path.join(home, name)
        if os.path.isdir(p):
            return p
    return home


class FolderWatcher:
    """check() 를 주기적으로 부르면, 감시를 켠 뒤 새로 생긴(다 받아진) 파일 목록을 돌려준다."""

    PARTIAL = (".crdownload", ".part", ".tmp", ".download")

    def __init__(self, folder, exts=(".pdf", ".hwpx")):
        self.folder = folder
        self.exts = exts
        self.seen = set(self._list())                   # 이미 있던 파일은 무시
        self.pending = {}                               # 받는 중인 파일: 경로 -> (크기, 처음 본 시각)

    def _list(self):
        try:
            return [os.path.join(self.folder, n) for n in os.listdir(self.folder)
                    if n.lower().endswith(self.exts) and not n.startswith("~$")]
        except OSError:
            return []

    def check(self):
        ready = []
        now = time.time()
        for p in self._list():
            if p in self.seen:
                continue
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            old = self.pending.get(p)
            if old and old[0] == size and size > 0 and now - old[1] >= 1.5:   # 크기가 그대로면 다 받은 것
                self.seen.add(p)
                self.pending.pop(p, None)
                ready.append(p)
            elif not old or old[0] != size:
                self.pending[p] = (size, now)
        return ready


# ──────────────────────────────────────────────────────────────
# 4. 바탕화면에 깔린 창 (달력 위젯)
#    다른 창들 '아래'에 두고, 바탕화면 보기(Win+D)를 눌러도 사라지지 않게 바탕화면(Progman)에 붙인다.
# ──────────────────────────────────────────────────────────────
def _hwnd(win):
    import ctypes
    win.update_idletasks()
    return ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()


def pin_to_desktop(win):
    """창을 바탕화면 층에 붙인다. 성공하면 True"""
    if not IS_WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = wintypes.HWND
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        hwnd = _hwnd(win)
        progman = user32.FindWindowW("Progman", None)
        if progman:
            user32.SetWindowLongPtrW(hwnd, -8, progman)  # GWLP_HWNDPARENT: 주인을 바탕화면으로
        send_to_bottom(win)
        return True
    except Exception:
        return False


def unpin_from_desktop(win):
    if not IS_WIN:
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW(_hwnd(win), -8, None)
    except Exception:
        pass


def send_to_bottom(win):
    """창을 맨 아래(다른 창들 뒤)로 보낸다"""
    if not IS_WIN:
        try:
            win.lower()
        except Exception:
            pass
        return
    try:
        import ctypes
        HWND_BOTTOM, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 1, 0x0001, 0x0002, 0x0010
        ctypes.windll.user32.SetWindowPos(_hwnd(win), HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
    except Exception:
        pass
