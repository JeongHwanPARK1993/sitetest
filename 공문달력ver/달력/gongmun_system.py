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
import threading
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


# ──────────────────────────────────────────────────────────────
# 4-2. 화면 범위 (모니터가 여러 개여도 창이 제자리에 오게)
# ──────────────────────────────────────────────────────────────
def virtual_screen():
    """모든 모니터를 합친 영역 (x, y, 너비, 높이). 윈도우가 아니면 None"""
    if not IS_WIN:
        return None
    try:
        import ctypes
        g = ctypes.windll.user32.GetSystemMetrics
        x, y, w, h = g(76), g(77), g(78), g(79)         # SM_XVIRTUALSCREEN, YVIRTUALSCREEN, CXVIRTUALSCREEN, CYVIRTUALSCREEN
        return (x, y, w, h) if w > 0 and h > 0 else None
    except Exception:
        return None


def fit_window(x, y, w, h, screen):
    """창이 화면 영역(screen=(x,y,w,h)) 안에 적어도 일부는 보이게 위치·크기를 고른다"""
    sx, sy, sw, sh = screen
    w, h = min(w, sw), min(h, sh)
    x = min(max(x, sx - w + 80), sx + sw - 80)           # 창의 80픽셀은 항상 화면 안에 남긴다
    y = min(max(y, sy), sy + sh - 60)
    return x, y, w, h


# ──────────────────────────────────────────────────────────────
# 4-3. 한 번에 하나만 실행 (두 번 켜면 두 번째는 이미 켜진 쪽을 보여 주고 끝낸다)
# ──────────────────────────────────────────────────────────────
_MUTEX = []                                             # 핸들을 붙잡아 둔다 (프로그램이 끝날 때까지 유지)
WM_SHOW_MAIN, WM_SHOW_WIDGETS = 0x8003, 0x8004          # 이미 켜진 프로그램에 보내는 신호


def acquire_single_instance(name="Local\\GongmunCalendarSingleInstance", widgets_only=False, signal=True):
    """처음 켠 프로그램이면 True. 이미 켜져 있으면 그쪽에 '보여 줘' 신호를 보내고 False."""
    if not IS_WIN:
        return True
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)      # 오류 번호를 바로 읽을 수 있게
        u = ctypes.windll.user32
        k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateMutexW.restype = wintypes.HANDLE
        handle = k.CreateMutexW(None, False, name)
        already = ctypes.get_last_error() == 183                # ERROR_ALREADY_EXISTS
        _MUTEX.append(handle)
        if not already:
            return True
        if signal:
            u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            u.FindWindowW.restype = wintypes.HWND
            u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            hwnd = u.FindWindowW("GongmunTrayWindow", None)     # 이미 켜진 프로그램의 트레이 창
            if hwnd:
                u.PostMessageW(hwnd, WM_SHOW_WIDGETS if widgets_only else WM_SHOW_MAIN, 0, 0)
        return False
    except Exception:
        return True                                     # 확인을 못 하면 그냥 켠다


# ──────────────────────────────────────────────────────────────
# 5. 트레이 아이콘 (작업표시줄 오른쪽 아래 작은 아이콘)
#    왼쪽 클릭 = 달력 열기/숨기기, 오른쪽 클릭 = 메뉴 (위젯 켜고 끄기, 공문 추가, 설정, 종료)
#    추가 설치 없이 윈도우 기본 기능(Shell_NotifyIcon)만 쓴다.
#    윈도우 메시지는 별도 쓰레드에서 받고, 고른 명령은 queue 로 화면 쪽에 넘긴다 (Tk 는 한 쓰레드에서만 써야 해서).
# ──────────────────────────────────────────────────────────────
class TrayIcon:
    WM_TRAY = 0x8001                                    # WM_APP + 1
    WM_STOP = 0x8002
    CLICK, DBLCLICK, RCLICK, CONTEXT = 0x202, 0x203, 0x205, 0x7B

    def __init__(self, icon_path, tooltip, menu_items):
        """menu_items() -> [(명령, 글자, 체크됨), ...]  빈 글자(None)는 구분선. 오른쪽 클릭 때마다 불러서 최신 상태를 보여 준다."""
        self.icon_path, self.tooltip, self.menu_items = icon_path, tooltip, menu_items
        self.commands = queue.Queue()                   # 화면 쪽이 꺼내 쓰는 명령들
        self.ready = threading.Event()
        self.ok = False
        self.error = ""
        self.hwnd = None
        self._thread = None

    # ---- 시작 / 끝 ----
    def start(self, timeout=5.0):
        if not IS_WIN:
            return False
        self._thread = threading.Thread(target=self._run, name="tray", daemon=True)
        self._thread.start()
        self.ready.wait(timeout)
        return self.ok

    def stop(self):
        if self.ok and self.hwnd:
            try:
                import ctypes
                ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_STOP, 0, 0)
                if self._thread:
                    self._thread.join(2.0)
            except Exception:
                pass
        self.ok = False

    def set_tooltip(self, text):
        self.tooltip = text
        if self.ok:
            try:
                self._notify(1)                         # NIM_MODIFY
            except Exception:
                pass

    # ---- 윈도우 쪽 ----
    def _run(self):
        try:
            import ctypes
            from ctypes import wintypes
            self._ct, self._wt = ctypes, wintypes
            self._define(ctypes, wintypes)
            self._create_window()
            self._notify(0)                             # NIM_ADD
            self.ok = True
        except Exception as e:                          # 트레이를 못 만들어도 프로그램은 계속 쓸 수 있다
            self.error = repr(e)
            self.ok = False
            self.ready.set()
            return
        self.ready.set()
        msg = self._wt.MSG()
        u = self._ct.windll.user32
        while u.GetMessageW(self._ct.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(self._ct.byref(msg))
            u.DispatchMessageW(self._ct.byref(msg))
        self.ok = False

    def _define(self, ct, wt):
        LRESULT = ct.c_ssize_t
        self.WNDPROC = ct.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

        class WNDCLASS(ct.Structure):
            _fields_ = [("style", wt.UINT), ("lpfnWndProc", self.WNDPROC), ("cbClsExtra", ct.c_int),
                        ("cbWndExtra", ct.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                        ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                        ("lpszClassName", wt.LPCWSTR)]

        class GUID(ct.Structure):
            _fields_ = [("a", ct.c_ulong), ("b", ct.c_ushort), ("c", ct.c_ushort), ("d", ct.c_ubyte * 8)]

        class NOTIFYICONDATA(ct.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
                        ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
                        ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", wt.WCHAR * 256),
                        ("uVersion", wt.UINT), ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                        ("guidItem", GUID), ("hBalloonIcon", wt.HICON)]

        self.WNDCLASS, self.NID = WNDCLASS, NOTIFYICONDATA
        u, s = ct.windll.user32, ct.windll.shell32
        u.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        u.DefWindowProcW.restype = LRESULT
        u.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ct.c_int, ct.c_int, ct.c_int, ct.c_int,
                                      wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
        u.CreateWindowExW.restype = wt.HWND
        u.RegisterClassW.argtypes = [ct.POINTER(WNDCLASS)]
        u.RegisterClassW.restype = wt.ATOM
        u.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ct.c_int, ct.c_int, wt.UINT]
        u.LoadImageW.restype = wt.HANDLE
        u.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        u.CreatePopupMenu.restype = wt.HMENU
        u.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ct.c_size_t, wt.LPCWSTR]
        u.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ct.c_int, ct.c_int, ct.c_int, wt.HWND, wt.LPVOID]
        u.DestroyMenu.argtypes = [wt.HMENU]
        u.DestroyWindow.argtypes = [wt.HWND]
        u.SetForegroundWindow.argtypes = [wt.HWND]
        u.RegisterWindowMessageW.argtypes = [wt.LPCWSTR]
        u.RegisterWindowMessageW.restype = wt.UINT
        s.Shell_NotifyIconW.argtypes = [wt.DWORD, ct.POINTER(NOTIFYICONDATA)]
        s.Shell_NotifyIconW.restype = wt.BOOL
        ct.windll.kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
        ct.windll.kernel32.GetModuleHandleW.restype = wt.HINSTANCE

    def _create_window(self):
        ct, wt = self._ct, self._wt
        u = ct.windll.user32
        hinst = ct.windll.kernel32.GetModuleHandleW(None)
        self.taskbar_created = u.RegisterWindowMessageW("TaskbarCreated")   # 탐색기가 다시 시작되면 아이콘을 다시 단다
        self._proc = self.WNDPROC(self._wndproc)        # 가비지 수집 방지
        wc = self.WNDCLASS()
        wc.lpfnWndProc, wc.hInstance, wc.lpszClassName = self._proc, hinst, "GongmunTrayWindow"
        u.RegisterClassW(ct.byref(wc))
        self.hwnd = u.CreateWindowExW(0, "GongmunTrayWindow", "gongmun-tray", 0, 0, 0, 0, 0, None, None, hinst, None)
        if not self.hwnd:
            raise OSError("트레이 창을 만들지 못했습니다")
        size = u.GetSystemMetrics(49)                   # SM_CXSMICON (보통 16)
        self.hicon = u.LoadImageW(None, self.icon_path, 1, size, size, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
        if not self.hicon:
            self.hicon = u.LoadIconW(None, ct.c_void_p(32512))                 # 못 읽으면 기본 아이콘

    def _notify(self, action):
        ct = self._ct
        d = self.NID()
        d.cbSize = ct.sizeof(self.NID)
        d.hWnd, d.uID, d.uFlags = self.hwnd, 1, 0x1 | 0x2 | 0x4          # MESSAGE | ICON | TIP
        d.uCallbackMessage, d.hIcon, d.szTip = self.WM_TRAY, self.hicon, self.tooltip[:120]
        if not ct.windll.shell32.Shell_NotifyIconW(action, ct.byref(d)):
            if action == 0:
                raise OSError("Shell_NotifyIcon 실패")

    def _wndproc(self, hwnd, msg, wparam, lparam):
        ct = self._ct
        try:
            if msg == self.WM_TRAY:
                ev = lparam & 0xFFFF
                if ev in (self.CLICK, self.DBLCLICK):
                    self.commands.put("toggle")
                elif ev in (self.RCLICK, self.CONTEXT):
                    cmd = self._show_menu()
                    if cmd:
                        self.commands.put(cmd)
                return 0
            if msg == WM_SHOW_MAIN:                     # 프로그램을 또 켠 경우: 이미 켜진 쪽을 보여 준다
                self.commands.put("show")
                return 0
            if msg == WM_SHOW_WIDGETS:
                self.commands.put("widgets")
                return 0
            if msg == self.taskbar_created:
                self._notify(0)
                return 0
            if msg == self.WM_STOP:
                ct.windll.user32.DestroyWindow(hwnd)
                return 0
            if msg == 0x2:                              # WM_DESTROY
                self._notify(2)                         # NIM_DELETE
                ct.windll.user32.PostQuitMessage(0)
                return 0
        except Exception as e:
            self.error = repr(e)
        return ct.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self):
        ct, wt = self._ct, self._wt
        u = ct.windll.user32
        items = self.menu_items()
        menu = u.CreatePopupMenu()
        ids = {}
        for n, it in enumerate(items, start=1):
            if it is None:
                u.AppendMenuW(menu, 0x800, 0, None)     # MF_SEPARATOR
                continue
            cmd, text, checked = it
            ids[n] = cmd
            u.AppendMenuW(menu, 0x0 | (0x8 if checked else 0), n, text)    # MF_STRING | MF_CHECKED
        pt = wt.POINT()
        u.GetCursorPos(ct.byref(pt))
        u.SetForegroundWindow(self.hwnd)                # 이걸 안 하면 메뉴 밖을 눌러도 안 닫힌다
        chosen = u.TrackPopupMenu(menu, 0x100 | 0x2 | 0x80, pt.x, pt.y, 0, self.hwnd, None)   # RETURNCMD|RIGHTBUTTON|NONOTIFY
        u.PostMessageW(self.hwnd, 0, 0, 0)
        u.DestroyMenu(menu)
        return ids.get(chosen)


# ──────────────────────────────────────────────────────────────
# 6. 병아리대원 (바탕화면 마스코트) 연결
#    달력이 기한 알림을 inbox.txt 에 적으면 병아리대원이 말풍선으로 묻고,
#    누른 대답(처리했어요/1시간 뒤에/달력에서 볼게요)을 outbox.txt 에 적는다.
# ──────────────────────────────────────────────────────────────
CHICK_MUTEX = "Local\\병아리대원_SingleInstance"


def chick_dir():
    """병아리대원 자료 폴더 (%APPDATA%\\병아리대원\\달력연결)"""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "병아리대원", "달력연결")


def chick_running():
    """병아리대원이 켜져 있는가 (병아리대원이 만드는 '한 번만 실행' 표식으로 확인)"""
    if not IS_WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.OpenMutexW.restype = wintypes.HANDLE
        h = k.OpenMutexW(0x00100000, False, CHICK_MUTEX)      # SYNCHRONIZE
        if h:
            k.CloseHandle(h)
            return True
    except Exception:
        pass
    return False


def chick_write_inbox(asks):
    """asks = [(번호, 할 말), ...] 를 inbox.txt 에 통째로 쓴다 (임시 파일 → 바꿔치기)"""
    d = chick_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "inbox.txt")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for key, msg in asks:
            f.write("%s\t%s\n" % (key, msg.replace("\t", " ").replace("\n", " ")))
    os.replace(tmp, path)


def chick_read_outbox():
    """병아리대원이 적은 대답들 [(번호, 대답)]. 읽은 것은 지운다 (이름을 바꿔서 읽으니 사이에 적힌 대답도 안 잃는다)."""
    d = chick_dir()
    path = os.path.join(d, "outbox.txt")
    if not os.path.exists(path):
        return []
    reading = os.path.join(d, "outbox.reading")
    try:
        os.replace(path, reading)
        with open(reading, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        os.remove(reading)
    except OSError:
        return []
    out = []
    for line in lines:
        key, _, ans = line.partition("\t")
        if key.strip() and ans.strip():
            out.append((key.strip(), ans.strip()))
    return out
