# -*- coding: utf-8 -*-
"""
gongmun_calendar.py  -  업무보조 달력 (화면 부분)

실행:  python gongmun_calendar.py            (전체 화면)
       python gongmun_calendar.py --widget   (바탕화면 위젯만)

화면 구성
  [머리줄]    월 이동 · 오늘 근무팀 · 검색칸
  [도구줄]    ＋공문 추가 · 여러 개 한꺼번에 | 업무 현황 · 내 실적 | 위젯 · 내보내기 · 설정
  [위젯]      바탕화면 달력 위젯(음력·절기·공휴일) / 목록 위젯(오늘 근무·임박 기한) - 골라서 사용
  [왼쪽]      월간 달력 (칸마다 근무팀, 일정을 누르면 선택 / 더블클릭하면 공문 열기)
  [오른쪽]    선택한 날: 일정 · 상세 · 회신 할 일 · 관련 공문  /  임박한 기한
  [아래 줄]   저장 위치 · 다운로드 감시 · 복사 분석 · 알림 상태 (누르면 설정이 열린다)

공문에서 기한을 찾는 규칙은 gongmun_core.py, 용어는 용어사전.txt,
파일 이름 만들기는 gongmun_rename.py, 윈도우 기능(끌어놓기·자동 실행)은 gongmun_system.py 에 있습니다.
"""
import calendar
import datetime as dt
import os
import queue
import re
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
import uuid
from tkinter import filedialog, messagebox, ttk

import author_credit
import gongmun_core as core
import gongmun_rename as rn                        # 공문 PDF 에서 제목·시행기관·시행일자를 읽어 파일 이름을 만든다
import gongmun_kcal as kcal                        # 음력 · 24절기 · 공휴일
import gongmun_system as gs                        # 파일 끌어놓기 · 윈도우 시작 시 실행 · 폴더 감시 · 바탕화면 고정

APP_NAME = "업무보조 달력"
FONT = "맑은 고딕"
KINDS = ["기한", "행사", "메모", "애매", "기타", "변경전"]

# 일정 색깔 (달력 칸 배경, 글자색) - 설정 창에서 고른다. 자동 = 기한에 따라 파랑/노랑/빨강
EVENT_COLORS = {"파랑": ("#e7f1ff", "#1f4e9c"), "초록": ("#e3f6ea", "#1d6b3e"), "노랑": ("#fff3cd", "#7a5b00"),
                "주황": ("#ffe6cc", "#9a4b00"), "빨강": ("#fde2e1", "#a12622"), "보라": ("#efe6ff", "#5b3a9c"),
                "분홍": ("#fde6f1", "#a12a66"), "회색": ("#eceef1", "#4b5563")}
COLOR_NAMES = ["자동"] + list(EVENT_COLORS)
DARK_TEXT = {"파랑": "#8fbcff", "초록": "#6fd69a", "노랑": "#ffd27a", "주황": "#ffb067", "빨강": "#ff8a80",
             "보라": "#c4a5ff", "분홍": "#ff9ccc", "회색": "#b0bcc4"}     # 어두운 달력 위젯에서 쓸 글자색


def resource_path(name):
    """아이콘 같은 프로그램 부속 파일 위치 (exe 로 만들어도 찾을 수 있게)"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def ev_label(ev):
    """달력에 보일 글자 (설정 창에서 바꿀 수 있다. 없으면 공문 제목). 반복 일정은 앞에 ↻"""
    text = ev.get("label") or ev.get("title", "")
    return ("↻ " + text) if ev.get("series") else text


def parse_time_text(tm):
    """'14:00', '14시', '9:5' -> '14:00'. 빈칸이면 ''"""
    tm = tm.strip().replace("시", ":").replace("분", "").rstrip(":")
    if not tm:
        return ""
    h, _, m = tm.partition(":")
    h, m = int(h), int(m or 0)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(tm)
    return "%02d:%02d" % (h, m)
# 근무팀 색 테마: 팀마다 글자색 두 가지 (흰 배경에서 쓸 색, 어두운 배경에서 쓸 색). 4팀 이후는 이어서 돌려 쓴다.
# 칸을 칠하지 않고 '1팀 · 2팀 · 3팀' 글자 색만 바뀐다.
TEAM_THEMES = {
    "기본": {"desc": "파랑 · 초록 · 주황", "colors": [
        ("#2f6fed", "#74a7ff"), ("#2e9d5b", "#5fd08f"), ("#d98200", "#ffb04d"),
        ("#7a4fd6", "#b69cff"), ("#d6336c", "#ff8fb6"), ("#0b7285", "#5fd0e0")]},
    "차분": {"desc": "남색 · 청록 · 갈색", "colors": [
        ("#3d5a99", "#8fa8dd"), ("#2a8577", "#6fc4b6"), ("#a8602c", "#e0a070"),
        ("#6b5b95", "#b5a8d6"), ("#a14a62", "#e0a0b2"), ("#4f7a28", "#a8cf80")]},
    "진하게": {"desc": "보라 · 청록 · 분홍", "colors": [
        ("#6d3df5", "#b39bff"), ("#00897b", "#4fd1c5"), ("#e0245e", "#ff7aa8"),
        ("#f57c00", "#ffb060"), ("#1565c0", "#7db6ff"), ("#558b2f", "#9ed56a")]},
}
_TEAM_THEME = ["기본"]


def set_team_theme(name):
    _TEAM_THEME[0] = name if name in TEAM_THEMES else "기본"      # 예전에 쓰던 '파스텔' 같은 이름은 기본으로


def team_text(team, dark=False):
    """근무팀 글자색. dark=True 면 어두운 배경에서 잘 보이는 밝은 색"""
    cols = TEAM_THEMES[_TEAM_THEME[0]]["colors"]
    return cols[(max(int(team), 1) - 1) % len(cols)][1 if dark else 0]



# 화면 색 (한곳에서 바꾸면 전체가 바뀐다)
PRIMARY = "#2f6fed"
PRIMARY_DARK = "#1d4ed8"
ACCENT_LIGHT = "#eaf1ff"
BG = "#f4f6fa"
CARD = "#ffffff"
BORDER = "#dde2ea"
TEXT = "#1f2430"
SUB = "#6b7280"
STATUS_BG = "#e9edf3"


def setup_style(root):
    """ttk 기본 모양을 깔끔한 평면 디자인으로 맞춘다."""
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=BG)
    st.configure(".", font=(FONT, 10), background=BG, foreground=TEXT)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=CARD)
    st.configure("TLabel", background=BG, foreground=TEXT)
    st.configure("Card.TLabel", background=CARD)
    st.configure("Sub.TLabel", background=BG, foreground=SUB)
    st.configure("Head.TLabel", background=BG, foreground=TEXT, font=(FONT, 12, "bold"))
    st.configure("TButton", padding=(10, 5), width=-1, background=CARD, bordercolor=BORDER, lightcolor=CARD, darkcolor=CARD,
                 focuscolor=CARD)
    st.map("TButton", background=[("active", "#eef2f8"), ("pressed", "#e2e8f2")])
    st.configure("Accent.TButton", background=PRIMARY, foreground="#ffffff", bordercolor=PRIMARY,
                 lightcolor=PRIMARY, darkcolor=PRIMARY, focuscolor=PRIMARY, font=(FONT, 10, "bold"))
    st.map("Accent.TButton", background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK), ("disabled", "#9db7f5")])
    st.configure("Danger.TButton", foreground="#b91c1c")
    st.configure("TLabelframe", background=BG, bordercolor=BORDER, lightcolor=BG, darkcolor=BG)
    st.configure("TLabelframe.Label", background=BG, foreground=PRIMARY_DARK, font=(FONT, 10, "bold"))
    st.configure("Treeview", rowheight=26, font=(FONT, 10), fieldbackground=CARD, background=CARD, bordercolor=BORDER)
    st.configure("Treeview.Heading", font=(FONT, 10, "bold"), background="#eef2f8", relief="flat")
    st.map("Treeview", background=[("selected", "#dbe7ff")], foreground=[("selected", TEXT)])
    st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    st.configure("TNotebook.Tab", padding=(12, 6), font=(FONT, 10), background="#e6eaf1", bordercolor=BORDER)
    st.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", PRIMARY_DARK)])
    for w in ("TCheckbutton", "TRadiobutton"):
        st.configure(w, background=BG)
    st.configure("Card.TCheckbutton", background=CARD)
    st.configure("TEntry", padding=4, fieldbackground=CARD, bordercolor=BORDER)
    st.configure("TCombobox", padding=3)
    st.configure("TMenubutton", padding=(10, 5), background=CARD, bordercolor=BORDER)
    st.configure("Seg.Toolbutton", padding=(12, 5), background="#eef2f8", font=(FONT, 10, "bold"), anchor="center")
    st.map("Seg.Toolbutton", background=[("selected", PRIMARY), ("active", "#dde6f5")],
           foreground=[("selected", "#ffffff")])


def listbox(parent, **kw):
    """모양을 맞춘 목록 상자"""
    opts = dict(font=(FONT, 10), relief="flat", highlightthickness=1, highlightbackground=BORDER,
                highlightcolor=PRIMARY, selectbackground="#dbe7ff", selectforeground=TEXT, activestyle="none",
                exportselection=False, bg=CARD)
    opts.update(kw)
    return tk.Listbox(parent, **opts)


def open_with_default_app(path):
    """파일을 기본 프로그램(PDF 뷰어 등)으로 연다."""
    if sys.platform.startswith("win"):
        os.startfile(path)                              # 윈도우
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def strike(text):
    """글자마다 가운데 줄(취소선)을 긋는다. (목록 상자는 글자별 서식이 안 돼서 이 방법을 쓴다)"""
    return "".join(ch if ch.isspace() else ch + "̶" for ch in text)


def event_colors(ev, today):
    """일정 칸의 색: (배경, 글자). 완료=회색, 지남/당일=빨강, 3일 이내=노랑, 나머지=파랑"""
    if ev.get("done"):
        return "#eceef1", "#8a8f98"
    if ev.get("color") in EVENT_COLORS:
        return EVENT_COLORS[ev["color"]]
    n = core.dday(ev["date"], today)
    if n <= 0:
        return "#fde2e1", "#a12622"
    if n <= 3:
        return "#fff3cd", "#7a5b00"
    return "#e7f1ff", "#1f4e9c"


def parse_date_text(text):
    """'2026-11-25', '2026.11.25', '2026/11/25' 를 날짜로"""
    return dt.date.fromisoformat(text.strip().replace(".", "-").replace("/", "-").strip("-"))


def store_document(app, events, source, text, title, stem, rename_orig, month=None):
    """공문 한 건 저장: (원본 이름 바꾸기) → 공문정리\연도\월 에 사본 → 일정 저장.
    돌려주는 값: (보관 파일, 경고 목록)"""
    warns = []
    if stem and rename_orig and source and os.path.isfile(source):
        try:                                            # 원본 파일도 같은 폴더에서 새 이름으로 바꾼다
            folder, ext = os.path.dirname(source), os.path.splitext(source)[1]
            same = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
            target, n = os.path.join(folder, stem + ext), 2
            while os.path.exists(target) and not same(target, source):
                target, n = os.path.join(folder, "%s (%d)%s" % (stem, n, ext)), n + 1
            if not same(target, source):
                os.rename(source, target)
                source = target
        except OSError as e:
            warns.append("원본 이름 바꾸기 실패 (파일이 열려 있는지 확인): %s" % e)
    try:
        doc_file = core.archive_document(source, text, title, events[0]["date"], stem=stem or None, month=month)
    except OSError as e:
        doc_file = ""
        warns.append("공문 사본 보관 실패 (일정만 등록): %s" % e)
    group = uuid.uuid4().hex                            # 같은 공문에서 나온 일정 묶음
    for ev in events:
        ev["source"], ev["file"], ev["group"] = source, doc_file, group
        app.store.add(ev)
    return doc_file, warns


def doc_month(info, doc_date=None):
    """공문을 정리할 달 'YYYY-MM': PDF 시행일 → 본문 머리말 날짜 → (없으면 None = 일정 날짜의 달)"""
    if info is not None and info.year:
        return "%04d-%02d" % (info.year, info.month)
    if doc_date:
        return doc_date.strftime("%Y-%m")
    return None


def make_event(date_iso, time_text, kind, snippet, common):
    ev = {"date": date_iso, "time": time_text, "kind": kind, "snippet": snippet}
    for k, v in common.items():                         # 할 일 목록은 일정마다 따로 복사
        ev[k] = v
    return ev


# ══════════════════════════════════════════════════════════════
#  공문 추가 창
#   ① 공문 내용(붙여넣기/불러오기/끌어놓기) → ② 공문 정보·파일 이름 → ③ 날짜 → ④ 붙임·할 일 → 등록
# ══════════════════════════════════════════════════════════════
class AddDialog:
    def __init__(self, app, path=None):
        self.app = app
        self.source = ""                                # 불러온 원본 파일 경로
        self.rows = []                                  # 날짜 후보 한 줄 한 줄
        self.rename_info = None                         # PDF 에서 읽은 제목·시행정보 (rn.DocInfo)
        self.emails = []
        self.doc_date = None

        win = self.win = tk.Toplevel(app.root)
        win.title("공문 추가")
        win.geometry("1120x700")
        win.minsize(940, 600)
        win.configure(bg=BG)
        if app.root.winfo_viewable():
            win.transient(app.root)

        self.hint = tk.Label(win, bg=ACCENT_LIGHT, fg=PRIMARY_DARK, font=(FONT, 10), anchor="w", padx=14, pady=7,
                             text="📥 공문 PDF를 이 창에 끌어다 놓거나 [📂 파일 불러오기]를 누르세요.  공문 내용을 복사해서 붙여넣어도 됩니다.")
        self.hint.pack(fill="x")

        bottom = ttk.Frame(win, padding=(12, 8))
        bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="✔ 달력에 등록", style="Accent.TButton", command=self.register).pack(side="right")
        ttk.Button(bottom, text="닫기", command=win.destroy).pack(side="right", padx=6)
        self.status_lb = ttk.Label(bottom, text="", style="Sub.TLabel")
        self.status_lb.pack(side="left")

        pane = ttk.PanedWindow(win, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        left = ttk.LabelFrame(pane, text=" ① 공문 내용 ", padding=8)
        right = ttk.Frame(pane)
        pane.add(left, weight=2)
        pane.add(right, weight=3)

        # ① 공문 내용
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="📂 파일 불러오기", command=self.load_file).pack(side="left")
        ttk.Button(btns, text="🔍 다시 분석", command=self.run_analyze).pack(side="left", padx=6)
        ttk.Label(btns, text="PDF · HWPX · TXT", style="Sub.TLabel").pack(side="right")
        self.text = tk.Text(left, wrap="word", font=(FONT, 10), relief="flat", bg="#fbfcfe", padx=8, pady=6,
                            highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY)
        self.text.pack(fill="both", expand=True)

        # ② 공문 정보 + 파일 이름
        info = ttk.LabelFrame(right, text=" ② 공문 정보 · 파일 이름 ", padding=8)
        info.pack(fill="x", padx=(8, 0))
        s = app.settings
        self.title_var, self.docno_var, self.org_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.name_var = tk.StringVar()
        self.tpl_var = tk.StringVar(value=rn.template_of(s))
        self.datefmt_var = tk.StringVar(value=s.get("rename_date_fmt", rn.DEFAULT_DATE_FORMAT))
        self.rename_orig = tk.BooleanVar(value=bool(s.get("rename_original", False)))

        ttk.Label(info, text="제목").grid(row=0, column=0, sticky="w")
        ttk.Entry(info, textvariable=self.title_var).grid(row=0, column=1, columnspan=4, sticky="we", padx=6, pady=2)
        ttk.Label(info, text="문서번호").grid(row=1, column=0, sticky="w")
        ttk.Entry(info, textvariable=self.docno_var, width=22).grid(row=1, column=1, sticky="w", padx=6, pady=2)
        ttk.Label(info, text="시행기관").grid(row=1, column=2, sticky="e")
        ttk.Entry(info, textvariable=self.org_var, width=18).grid(row=1, column=3, columnspan=2, sticky="w", padx=6, pady=2)
        ttk.Label(info, text="새 파일 이름").grid(row=2, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(info, textvariable=self.name_var).grid(row=2, column=1, columnspan=3, sticky="we", padx=6, pady=(6, 2))
        ttk.Button(info, text="↻ 다시 만들기", command=self.make_name).grid(row=2, column=4, sticky="e", pady=(6, 2))
        ttk.Label(info, text="이름 형식").grid(row=3, column=0, sticky="w")
        ttk.Entry(info, textvariable=self.tpl_var).grid(row=3, column=1, columnspan=2, sticky="we", padx=6, pady=2)
        ttk.Combobox(info, textvariable=self.datefmt_var, values=list(rn.DATE_FORMATS), width=12,
                     state="readonly").grid(row=3, column=3, sticky="w", padx=6)
        self.name_note = ttk.Label(info, text="{시행일자} {제목} {시행기관} {문서번호} 를 쓸 수 있어요", style="Sub.TLabel")
        self.name_note.grid(row=4, column=1, columnspan=4, sticky="w", padx=6)
        ttk.Checkbutton(info, text="불러온 원본 파일 이름도 새 이름으로 바꾸기", variable=self.rename_orig).grid(
            row=5, column=1, columnspan=4, sticky="w", padx=6, pady=(2, 0))
        info.columnconfigure(1, weight=1)
        info.columnconfigure(3, weight=1)

        # ③ 날짜
        dates = ttk.LabelFrame(right, text=" ③ 달력에 올릴 날짜 (체크한 것만 올라갑니다) ", padding=8)
        dates.pack(fill="x", padx=(8, 0), pady=8)
        head = ttk.Frame(dates)
        head.pack(fill="x")
        for i, (t, w) in enumerate([("등록", 4), ("날짜", 13), ("시간", 7), ("구분", 8), ("공문 속 원문", 30)]):
            ttk.Label(head, text=t, font=(FONT, 9, "bold"), width=w).grid(row=0, column=i, sticky="w", padx=4)
        self.rows_frame = ttk.Frame(dates)
        self.rows_frame.pack(fill="x")
        ttk.Button(dates, text="+ 날짜 직접 추가", command=self.add_row).pack(anchor="w", pady=(6, 0))

        # ④ 붙임
        extra = ttk.LabelFrame(right, text=" ④ 붙임 (한 줄에 하나) ", padding=8)
        extra.pack(fill="both", expand=True, padx=(8, 0))
        self.attach_text = tk.Text(extra, height=4, wrap="word", font=(FONT, 9), relief="flat", bg="#fbfcfe",
                                   highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY, padx=4, pady=3)
        self.attach_text.pack(fill="both", expand=True)

        if not gs.enable_file_drop(win, self.on_drop):
            self.hint.config(text="📂 [파일 불러오기]로 공문 PDF/HWPX 를 여세요.  공문 내용을 복사해서 붙여넣어도 됩니다.")
        if path:
            win.after(50, lambda: self.load_file(path))

    # ---- 파일 불러오기 / 끌어놓기 -------------------------------------------
    def on_drop(self, paths):
        files = gs.expand_paths(paths)
        if len(files) == 1:
            self.load_file(files[0])
        elif len(files) > 1:                            # 여러 개면 '한꺼번에 등록' 창으로
            self.app.open_batch(files)
            self.win.destroy()

    def load_file(self, path=None):
        if not path:
            path = filedialog.askopenfilename(
                parent=self.win, title="공문 파일 선택",
                filetypes=[("공문 파일", "*.pdf *.hwpx *.txt"), ("모든 파일", "*.*")])
            if not path:
                return
        try:
            body = core.read_file_text(path)
        except Exception as e:                          # 읽기 실패는 메시지로 알려 준다
            messagebox.showerror("파일 읽기 실패", str(e), parent=self.win)
            return
        self.source = path
        self.text.delete("1.0", "end")
        self.text.insert("1.0", body)
        self.run_analyze()
        if not self.title_var.get().strip():            # 공문에서 제목을 못 찾으면 파일 이름이라도 사용
            self.title_var.set(os.path.splitext(os.path.basename(path))[0])
        self.read_rename_info(path)
        self.win.title("공문 추가 - " + os.path.basename(path))

    # ---- 분석 ----------------------------------------------------------
    def run_analyze(self):
        body = self.text.get("1.0", "end")
        if not body.strip():
            self.status_lb.config(text="공문 내용을 먼저 붙여넣거나 파일을 불러와 주세요.")
            return
        result = core.analyze(body, lex=self.app.lex)
        self.title_var.set(result["title"])             # ← 공문 속 '제목'이 자동으로 들어간다
        if not self.docno_var.get():
            self.docno_var.set(result["doc_no"])
        self.attach_text.delete("1.0", "end")
        self.attach_text.insert("1.0", "\n".join(result["attachments"]))
        self.emails = result["emails"]
        self.doc_date = result.get("doc_date")         # 공문 머리말의 시행·기안 날짜 (정리할 달)

        for r in self.rows:                             # 이전 결과 지우기
            r["widgets"].destroy()
        self.rows = []
        for cd in result["candidates"]:
            self.add_row(cd)
        n = sum(1 for c in result["candidates"] if c["checked"])
        if result["candidates"]:
            self.status_lb.config(text="날짜 %d개를 찾았고 %d개를 미리 체크했어요. 확인하고 [✔ 달력에 등록]을 누르세요."
                                  % (len(result["candidates"]), n))
        else:
            self.status_lb.config(text="날짜를 찾지 못했어요. [+ 날짜 직접 추가]로 넣어 주세요.")

    def add_row(self, cd=None):
        cd = cd if isinstance(cd, dict) else {}
        frame = ttk.Frame(self.rows_frame)
        frame.pack(fill="x", pady=1)
        r = {
            "widgets": frame,
            "check": tk.BooleanVar(value=cd.get("checked", True)),
            "date": tk.StringVar(value=cd["date"].isoformat() if cd.get("date") else ""),
            "time": tk.StringVar(value=cd.get("time", "")),
            "kind": tk.StringVar(value=cd.get("kind", "기한")),
            "snippet": cd.get("snippet", ""),
        }
        ttk.Checkbutton(frame, variable=r["check"]).grid(row=0, column=0, padx=(8, 10))
        ttk.Entry(frame, textvariable=r["date"], width=12).grid(row=0, column=1, padx=4)
        ttk.Entry(frame, textvariable=r["time"], width=7).grid(row=0, column=2, padx=4)
        ttk.Combobox(frame, textvariable=r["kind"], values=KINDS, width=6, state="readonly").grid(row=0, column=3, padx=4)
        ttk.Label(frame, text=r["snippet"], wraplength=330, style="Sub.TLabel").grid(row=0, column=4, padx=4, sticky="w")
        self.rows.append(r)

    # ---- 파일 이름 만들기 -------------------------------------------------
    def read_rename_info(self, path):
        """PDF 면 제목·시행기관·시행일자를 읽어 새 파일 이름을 미리 채운다."""
        self.rename_info = None
        self.name_var.set("")
        if os.path.splitext(path)[1].lower() != ".pdf":
            self.name_note.config(text="PDF 가 아니어서 제목으로 정리합니다. (직접 적어도 돼요)")
            return
        info = rn.analyze(path)
        if not info.ok:
            self.name_note.config(text=info.error + " - 이름을 직접 적어 주세요.")
            return
        self.rename_info = info
        if info.title:
            self.title_var.set(info.title)              # 제목은 시행정보까지 읽는 이 방식이 더 정확하다
        if info.number:
            self.docno_var.set(info.number)             # 이 공문 자신의 번호 (시행 ○○과-1234)
        self.org_var.set(info.org)
        self.make_name(notes=info.notes)

    def make_name(self, notes=None):
        if self.rename_info is None:
            if self.title_var.get().strip():
                self.name_var.set(rn.safe_name(self.title_var.get()))
            return
        info = rn.DocInfo(**{**self.rename_info.__dict__, "title": self.title_var.get().strip() or self.rename_info.title,
                             "org": self.org_var.get().strip() or self.rename_info.org})
        self.name_var.set(rn.build_name(info, self.tpl_var.get(), self.datefmt_var.get()))
        where = core.archive_subdir("%04d-%02d" % (info.year, info.month)) if info.year else core.ARCHIVE_DIR
        self.name_note.config(text=("⚠ 확인 필요: " + " / ".join(notes)) if notes else "✔ 등록하면 " + where + "\\ 에 이 이름으로 정리됩니다.")

    # ---- 등록 ----------------------------------------------------------
    def register(self):
        title = self.title_var.get().strip() or "(제목 없음)"
        lines = lambda t: [a.strip() for a in t.get("1.0", "end").splitlines() if a.strip()]
        text = self.text.get("1.0", "end")
        docno = self.docno_var.get().strip()
        common = {"title": title, "doc_no": docno, "org": self.org_var.get().strip(),
                  "attachments": lines(self.attach_text), "emails": self.emails,
                  "refs": core.find_doc_refs(text, docno), "body": text.strip()}
        new_events = []
        for r in self.rows:
            if not r["check"].get():
                continue
            try:                                        # '2026.11.25' 처럼 점으로 써도 받아 준다
                d = parse_date_text(r["date"].get())
            except ValueError:
                messagebox.showwarning("날짜 확인", "날짜를 YYYY-MM-DD 형식으로 적어 주세요.\n(예: 2026-11-25)", parent=self.win)
                return
            try:
                tm = parse_time_text(r["time"].get())
            except ValueError:
                messagebox.showwarning("시간 확인", "시간은 HH:MM 형식으로 적어 주세요. (예: 18:00)", parent=self.win)
                return
            new_events.append(make_event(d.isoformat(), tm, r["kind"].get(), r["snippet"], common))
        if not new_events:
            messagebox.showinfo("안내", "달력에 올릴 날짜를 체크해 주세요.", parent=self.win)
            return

        stem = rn.safe_name(self.name_var.get().replace(".pdf", ""))
        s = self.app.settings
        s["rename_template"], s["rename_date_fmt"] = self.tpl_var.get(), self.datefmt_var.get()
        s["rename_original"] = self.rename_orig.get()
        core.save_settings(s)
        info = self.rename_info
        month = doc_month(info, self.doc_date)          # 기안(시행)한 달 폴더에 정리
        doc_file, warns = store_document(self.app, new_events, self.source, text, title, stem, self.rename_orig.get(), month)
        self.app.go_to(dt.date.fromisoformat(new_events[0]["date"]))
        msg = "%d건을 달력에 등록했습니다.\n공문 사본: %s" % (len(new_events), doc_file or "없음")
        if warns:
            msg += "\n\n⚠ " + "\n⚠ ".join(warns)
        (messagebox.showwarning if warns else messagebox.showinfo)("등록 완료", msg, parent=self.win)
        self.win.destroy()


# ══════════════════════════════════════════════════════════════
#  여러 공문 한꺼번에 등록
#   파일·폴더를 넣으면 하나씩 읽어 제목 / 날짜 / 새 이름을 보여 주고, 체크한 것을 한 번에 올린다
# ══════════════════════════════════════════════════════════════
class BatchDialog:
    def __init__(self, app, paths=()):
        self.app = app
        self.items = []                                 # 파일 하나당 dict 하나
        self.queue = []                                 # 아직 안 읽은 파일 (창이 멈추지 않게 하나씩 읽는다)
        win = self.win = tk.Toplevel(app.root)
        win.title("여러 공문 한꺼번에 등록")
        win.geometry("1180x620")
        win.minsize(900, 420)
        win.configure(bg=BG)
        if app.root.winfo_viewable():
            win.transient(app.root)

        self.hint = tk.Label(win, bg=ACCENT_LIGHT, fg=PRIMARY_DARK, font=(FONT, 10), anchor="w", padx=14, pady=7,
                             text="📥 공문 PDF 여러 개(또는 폴더)를 이 창에 끌어다 놓으세요.  [등록] 칸을 누르면 체크/해제, 줄을 더블클릭하면 하나씩 자세히 고칠 수 있어요.")
        self.hint.pack(fill="x")
        top = ttk.Frame(win, padding=(12, 8))
        top.pack(fill="x")
        ttk.Button(top, text="📂 파일 추가", command=self.pick_files).pack(side="left")
        ttk.Button(top, text="📁 폴더 추가", command=self.pick_folder).pack(side="left", padx=6)
        ttk.Button(top, text="선택 빼기", command=self.remove_selected).pack(side="left")
        ttk.Button(top, text="모두 비우기", command=self.clear).pack(side="left", padx=6)
        self.rename_orig = tk.BooleanVar(value=bool(app.settings.get("rename_original", False)))
        ttk.Checkbutton(top, text="원본 파일 이름도 새 이름으로 바꾸기", variable=self.rename_orig).pack(side="right")

        cols = ("check", "file", "title", "date", "newname", "state")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="extended")
        for col, text, width in zip(cols, ["등록", "원래 파일", "공문 제목", "올릴 날짜", "새 파일 이름", "상태"],
                                    [50, 150, 320, 150, 330, 160]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center" if col == "check" else "w", stretch=col in ("title", "newname"))
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("warn", foreground="#b45309")
        self.tree.tag_configure("err", foreground="#b91c1c")
        self.tree.tag_configure("done", foreground="#8a8f98")
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double)

        bottom = ttk.Frame(win, padding=(12, 8))
        bottom.pack(fill="x")
        self.sum_lb = ttk.Label(bottom, text="", style="Sub.TLabel")
        self.sum_lb.pack(side="left")
        ttk.Button(bottom, text="✔ 체크한 것 모두 등록", style="Accent.TButton", command=self.register_all).pack(side="right")
        ttk.Button(bottom, text="닫기", command=win.destroy).pack(side="right", padx=6)

        if not gs.enable_file_drop(win, self.add_paths):
            self.hint.config(text="📂 [파일 추가] / [📁 폴더 추가]로 공문을 넣으세요.  [등록] 칸을 누르면 체크/해제, 더블클릭하면 하나씩 자세히 고칠 수 있어요.")
        self.add_paths(paths)

    # ---- 목록 채우기 ----------------------------------------------------
    def pick_files(self):
        paths = filedialog.askopenfilenames(parent=self.win, title="공문 파일 선택",
                                            filetypes=[("공문 파일", "*.pdf *.hwpx *.txt"), ("모든 파일", "*.*")])
        self.add_paths(list(paths))

    def pick_folder(self):
        path = filedialog.askdirectory(parent=self.win, title="공문이 든 폴더 선택")
        if path:
            self.add_paths([path])

    def add_paths(self, paths):
        for p in gs.expand_paths(paths):
            if any(os.path.abspath(it["path"]) == os.path.abspath(p) for it in self.items):
                continue
            it = {"path": p, "iid": uuid.uuid4().hex, "state": "읽는 중…", "tag": "", "check": False,
                  "title": "", "picks": [], "stem": ""}
            self.items.append(it)
            self.tree.insert("", "end", iid=it["iid"])
            self.update_row(it)
            self.queue.append(it)
        self.win.after(20, self.process_next)

    def process_next(self):
        if not self.queue:
            self.update_summary()
            return
        it = self.queue.pop(0)
        if it in self.items:
            self.analyze_item(it)
            self.update_row(it)
        self.update_summary()
        self.win.after(20, self.process_next)

    def analyze_item(self, it):
        path = it["path"]
        try:
            text = core.read_file_text(path)
        except Exception as e:
            it.update(state="읽기 실패: %s" % str(e).splitlines()[0][:40], tag="err", check=False)
            return
        res = core.analyze(text, lex=self.app.lex)
        info = rn.analyze(path) if path.lower().endswith(".pdf") else None
        ok = info is not None and info.ok
        title = (info.title if ok and info.title else res["title"]) or os.path.splitext(os.path.basename(path))[0]
        docno = info.number if ok and info.number else res["doc_no"]
        s = self.app.settings
        stem = rn.build_name(rn.DocInfo(**{**info.__dict__, "title": title}), rn.template_of(s),
                             s.get("rename_date_fmt", rn.DEFAULT_DATE_FORMAT)) if ok else ""
        picks = [c for c in res["candidates"] if c["checked"]]
        it.update(text=text, res=res, info=info if ok else None, title=title, docno=docno, stem=stem, picks=picks,
                  org=info.org if ok else "")
        notes = (info.notes if ok else []) + ([] if ok or not info else [info.error])
        if picks:
            it.update(check=True, state="준비됨" + (" · ⚠ " + notes[0] if notes else ""), tag="warn" if notes else "")
        else:
            it.update(check=False, state="날짜 못 찾음 · 더블클릭해서 입력", tag="warn")

    def update_row(self, it):
        picks = it.get("picks") or []
        when = ""
        if picks:
            c = picks[0]
            when = "%s %s %s" % (c["date"].isoformat(), c.get("time", ""), c["kind"])
            if len(picks) > 1:
                when += " 외 %d" % (len(picks) - 1)
        mark = "✔" if it.get("check") else ("완료" if it.get("done") else "☐")
        self.tree.item(it["iid"], values=(mark, os.path.basename(it["path"]), it.get("title", ""), when,
                                          (it["stem"] + os.path.splitext(it["path"])[1]) if it.get("stem") else "제목으로 정리",
                                          it["state"]),
                       tags=(it["tag"],) if it.get("tag") else ())

    def update_summary(self):
        n = len(self.items)
        c = sum(1 for it in self.items if it.get("check"))
        reading = len(self.queue)
        self.sum_lb.config(text="공문 %d개 · 등록할 것 %d개%s" % (n, c, (" · 읽는 중 %d개" % reading) if reading else ""))

    def by_iid(self, iid):
        return next((it for it in self.items if it["iid"] == iid), None)

    def on_click(self, e):
        if self.tree.identify_column(e.x) != "#1":
            return
        it = self.by_iid(self.tree.identify_row(e.y))
        if it and it.get("picks") and not it.get("done"):
            it["check"] = not it.get("check")
            self.update_row(it)
            self.update_summary()
            return "break"

    def on_double(self, e):
        it = self.by_iid(self.tree.identify_row(e.y))
        if not it or it.get("done"):
            return
        AddDialog(self.app, path=it["path"])            # 하나만 자세히 고치기
        it.update(check=False, done=True, state="개별 창에서 등록", tag="done")
        self.update_row(it)
        self.update_summary()

    def remove_selected(self):
        for iid in self.tree.selection():
            it = self.by_iid(iid)
            if it:
                self.items.remove(it)
            self.tree.delete(iid)
        self.update_summary()

    def clear(self):
        self.items, self.queue = [], []
        self.tree.delete(*self.tree.get_children())
        self.update_summary()

    # ---- 한꺼번에 등록 ----------------------------------------------------
    def register_all(self):
        if self.queue:
            messagebox.showinfo("안내", "아직 읽는 중인 파일이 있어요. 잠시 후 다시 눌러 주세요.", parent=self.win)
            return
        todo = [it for it in self.items if it.get("check") and it.get("picks") and not it.get("done")]
        if not todo:
            messagebox.showinfo("안내", "등록할 공문이 없습니다. [등록] 칸을 눌러 체크해 주세요.", parent=self.win)
            return
        if not messagebox.askyesno("한꺼번에 등록", "공문 %d개를 달력에 등록할까요?" % len(todo), parent=self.win):
            return
        self.app.settings["rename_original"] = self.rename_orig.get()
        core.save_settings(self.app.settings)
        n_ev, warns, first = 0, [], None
        for it in todo:
            res = it["res"]
            common = {"title": it["title"], "doc_no": it["docno"], "org": it.get("org", ""),
                      "attachments": res["attachments"], "emails": res["emails"],
                      "body": it["text"].strip(),
                      "refs": core.find_doc_refs(it["text"], it["docno"])}
            events = [make_event(c["date"].isoformat(), c.get("time", ""), c["kind"], c["snippet"], common) for c in it["picks"]]
            month = doc_month(it.get("info"), res.get("doc_date"))
            _, w = store_document(self.app, events, it["path"], it["text"], it["title"], it["stem"], self.rename_orig.get(), month)
            warns += ["%s: %s" % (os.path.basename(it["path"]), x) for x in w]
            n_ev += len(events)
            first = first or events[0]["date"]
            it.update(check=False, done=True, state="등록 완료" + (" · ⚠" if w else ""), tag="done")
            self.update_row(it)
        self.update_summary()
        if first:
            self.app.go_to(dt.date.fromisoformat(first))
        msg = "공문 %d개 · 일정 %d건을 등록했습니다." % (len(todo), n_ev)
        if warns:
            msg += "\n\n⚠ " + "\n⚠ ".join(warns[:8])
        (messagebox.showwarning if warns else messagebox.showinfo)("등록 완료", msg, parent=self.win)


# ══════════════════════════════════════════════════════════════
#  설정 창 (근무팀 · 알림 · 자동화 · 공유 폴더 · 파일 이름)
# ══════════════════════════════════════════════════════════════
class SettingsDialog:
    TABS = ["team", "alert", "auto", "widget", "share", "name"]

    def __init__(self, app, tab="team"):
        self.app = app
        st = app.settings
        win = self.win = tk.Toplevel(app.root)
        win.title("설정")
        win.configure(bg=BG)
        win.resizable(False, False)
        if app.root.winfo_viewable():
            win.transient(app.root)
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        def page(title):
            f = ttk.Frame(nb, padding=16)
            nb.add(f, text=title)
            return f

        # ---- 근무팀
        p = page(" 👥 근무팀 ")
        ttk.Label(p, text="3교대 근무팀 순서를 알려 주세요", style="Head.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(p, text="기준일 (그날 근무한 팀을 알고 있는 날)").grid(row=1, column=0, sticky="w", pady=(12, 2))
        self.date_var = tk.StringVar(value=st.get("anchor_date") or dt.date.today().isoformat())
        ttk.Entry(p, textvariable=self.date_var, width=14).grid(row=1, column=1, padx=8, sticky="w", pady=(12, 2))
        ttk.Label(p, text="기준일부터 돌아가는 순서").grid(row=2, column=0, sticky="w", pady=2)
        self.pattern_var = tk.StringVar(value=",".join(str(n) for n in st.get("pattern", [1, 2, 3])))
        ttk.Entry(p, textvariable=self.pattern_var, width=14).grid(row=2, column=1, padx=8, sticky="w")
        ttk.Label(p, text="내 팀 (내 근무일을 진하게 표시)").grid(row=3, column=0, sticky="w", pady=2)
        self.my_var = tk.StringVar(value=("%d팀" % st["my_team"]) if st.get("my_team") else "없음")
        ttk.Combobox(p, textvariable=self.my_var, values=["없음", "1팀", "2팀", "3팀"], width=8,
                     state="readonly").grid(row=3, column=1, padx=8, sticky="w")
        ttk.Label(p, justify="left", style="Sub.TLabel", text=(
            "예) 기준일(2026-11-19)에 2팀이 근무했고, 다음날 3팀, 그다음 날 1팀이면\n"
            "    기준일: 2026-11-19 / 순서: 2,3,1\n"
            "하루에 한 팀씩 돌아가는 방식이 아니면 순서를 길게 적으면 됩니다.\n"
            "    예) 2일씩 근무: 1,1,2,2,3,3")).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Label(p, text="🎨 근무팀 색깔", font=(FONT, 10, "bold")).grid(row=5, column=0, columnspan=2, sticky="w", pady=(14, 4))
        self.team_theme = tk.StringVar(value=st.get("team_theme", "기본") if st.get("team_theme") in TEAM_THEMES else "기본")
        for i, (tname, td) in enumerate(TEAM_THEMES.items()):
            rowf = ttk.Frame(p)
            rowf.grid(row=6 + i, column=0, columnspan=2, sticky="w", padx=14, pady=1)
            ttk.Radiobutton(rowf, text="%s  (%s)" % (tname, td["desc"]), value=tname, variable=self.team_theme, width=22).pack(side="left")
            for n_, (lc, _dc) in enumerate(td["colors"][:3], start=1):
                tk.Label(rowf, text="%d팀" % n_, bg=CARD, fg=lc, font=(FONT, 11, "bold"), padx=10, pady=1,
                         highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=2)
        ttk.Label(p, text="칸을 칠하지 않고 '1팀 · 2팀 · 3팀' 글자 색만 바뀝니다. 내 팀은 굵게 보입니다.", style="Sub.TLabel").grid(
            row=9, column=0, columnspan=2, sticky="w", padx=14, pady=(6, 0))

        # ---- 알림
        p = page(" ⏰ 기한 알림 ")
        ttk.Label(p, text="기한이 다가오면 화면 오른쪽 아래에 알림을 띄웁니다", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.alert_on = tk.BooleanVar(value=st.get("alerts_on", True))
        ttk.Checkbutton(p, text="기한 알림 사용", variable=self.alert_on).grid(row=1, column=0, sticky="w", pady=(12, 4))
        levels = st.get("alert_levels", [3, 1, 0])
        self.lv_vars = {}
        row = ttk.Frame(p)
        row.grid(row=2, column=0, columnspan=3, sticky="w", padx=20)
        for lv, name in [(3, "3일 전 (D-3)"), (1, "하루 전 (D-1)"), (0, "당일 (D-day)")]:
            v = tk.BooleanVar(value=lv in levels)
            self.lv_vars[lv] = v
            ttk.Checkbutton(row, text=name, variable=v).pack(side="left", padx=(0, 14))
        self.flash_var = tk.BooleanVar(value=st.get("widget_flash", True))
        ttk.Checkbutton(p, text="위젯이 켜져 있으면 위젯도 깜빡이기", variable=self.flash_var).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(p, style="Sub.TLabel", justify="left", text=(
            "· 기한이 지난 일정은 일주일 동안 '기한 지남' 알림을 한 번 띄웁니다.\n"
            "· 같은 알림은 한 번만 뜹니다. 완료 처리한 일정은 알리지 않습니다.\n"
            "· 위젯만 켜 두어도(--widget) 알림이 뜹니다.")).grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 0))

        # ---- 자동화
        p = page(" ⚡ 자동화 ")
        ttk.Label(p, text="손이 덜 가게 자동으로 해 주는 기능", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.dl_on = tk.BooleanVar(value=st.get("watch_downloads", False))
        ttk.Checkbutton(p, text="📥 다운로드 폴더에 새 공문(PDF/HWPX)이 받아지면 '공문 추가' 창 자동으로 띄우기",
                        variable=self.dl_on).grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 2))
        self.dl_dir = tk.StringVar(value=st.get("download_dir") or gs.default_download_dir())
        ttk.Label(p, text="감시할 폴더").grid(row=2, column=0, sticky="w", padx=(22, 4))
        ttk.Entry(p, textvariable=self.dl_dir, width=46).grid(row=2, column=1, sticky="w")
        ttk.Button(p, text="찾아보기", command=lambda: self.browse(self.dl_dir)).grid(row=2, column=2, padx=6)
        self.auto_on = tk.BooleanVar(value=gs.autostart_enabled())
        cb = ttk.Checkbutton(p, text="🖥 윈도우를 켜면 고른 위젯(위젯 탭) 자동으로 띄우기", variable=self.auto_on)
        cb.grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 2))
        if not gs.autostart_supported():
            cb.state(["disabled"])
            ttk.Label(p, text="(윈도우에서만 쓸 수 있어요)", style="Sub.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", padx=22)

        # ---- 위젯
        p = page(" 🧩 위젯 ")
        ttk.Label(p, text="쓸 위젯을 고르세요 (둘 다 써도 돼요)", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        wsel = st.get("widgets", {"desk": True, "list": False})
        self.w_desk = tk.BooleanVar(value=wsel.get("desk", True))
        self.w_list = tk.BooleanVar(value=wsel.get("list", False))
        ttk.Checkbutton(p, text="📅 달력 위젯 - 바탕화면에 깔리는 큰 월간 달력 (음력 · 절기 · 공휴일 · 일정)",
                        variable=self.w_desk).grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 2))
        ttk.Checkbutton(p, text="📋 목록 위젯 - 오늘 근무팀과 임박한 기한만 보여 주는 작은 창",
                        variable=self.w_list).grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        dc = st.get("desk_cal", {})
        ttk.Label(p, text="달력 위젯 위치", font=(FONT, 10, "bold")).grid(row=3, column=0, sticky="w", pady=(16, 2))
        self.dc_mode = tk.StringVar(value=dc.get("mode", "desktop"))
        row = ttk.Frame(p)
        row.grid(row=4, column=0, columnspan=3, sticky="w", padx=20)
        for key, label in (("desktop", "바탕화면에 깔기 (다른 창 아래, 바탕화면 보기에도 보임)"), ("normal", "일반 창"), ("top", "항상 위")):
            ttk.Radiobutton(row, text=label, value=key, variable=self.dc_mode).pack(side="left", padx=(0, 12))
        ttk.Label(p, text="달력 위젯 모양", font=(FONT, 10, "bold")).grid(row=5, column=0, sticky="w", pady=(12, 2))
        row = ttk.Frame(p)
        row.grid(row=6, column=0, columnspan=3, sticky="w", padx=20)
        self.dc_theme = tk.StringVar(value="밝게" if dc.get("theme") == "light" else "어둡게")
        ttk.Label(row, text="테마").pack(side="left")
        ttk.Combobox(row, textvariable=self.dc_theme, values=["어둡게", "밝게"], width=6, state="readonly").pack(side="left", padx=(4, 14))
        self.dc_alpha = tk.StringVar(value="%d%%" % round(float(dc.get("alpha", 0.9)) * 100))
        ttk.Label(row, text="불투명도").pack(side="left")
        ttk.Combobox(row, textvariable=self.dc_alpha, values=["100%", "90%", "80%", "70%", "60%"], width=6,
                     state="readonly").pack(side="left", padx=(4, 14))
        self.dc_lunar = tk.BooleanVar(value=dc.get("lunar", False))
        self.dc_week = tk.BooleanVar(value=dc.get("weeknum", False))
        ttk.Checkbutton(row, text="음력 표시", variable=self.dc_lunar).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(row, text="주 번호 표시", variable=self.dc_week).pack(side="left")
        ttk.Label(p, style="Sub.TLabel", justify="left", text=(
            "· 위쪽 줄을 끌면 이동, 오른쪽 아래 ◢ 를 끌면 크기 조절, 마우스 휠로 달을 넘깁니다.\n"
            "· 일정 더블클릭 = 공문 열기 / 날짜 더블클릭 = 큰 달력에서 보기 / 우클릭 = 메뉴\n"
            "· 공휴일·대체공휴일·24절기·음력은 프로그램이 직접 계산합니다 (인터넷 필요 없음).")).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(14, 0))

        # ---- 공유 폴더
        p = page(" 📁 공유 폴더 ")
        ttk.Label(p, text="팀원과 같은 달력 쓰기", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(p, style="Sub.TLabel", justify="left", text=(
            "공유 드라이브(예: \\\\서버\\팀공유\\공문달력)를 지정하면, 일정 파일과 공문정리 폴더를 그곳에 둡니다.\n"
            "같은 폴더를 지정한 팀원끼리 일정이 같이 보이고, 15초마다 새로 고칩니다.\n"
            "동시에 고쳐도 더 나중에 고친 내용이 남고, 지운 일정은 모두에게서 지워집니다.\n"
            "(근무팀·알림·위젯 같은 설정은 각자 PC 에 따로 저장됩니다)")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 12))
        self.share_dir = tk.StringVar(value=st.get("shared_dir", ""))
        ttk.Label(p, text="공유 폴더").grid(row=2, column=0, sticky="w")
        ttk.Entry(p, textvariable=self.share_dir, width=46).grid(row=2, column=1, sticky="w", padx=4)
        ttk.Button(p, text="찾아보기", command=lambda: self.browse(self.share_dir)).grid(row=2, column=2, padx=6)
        ttk.Button(p, text="공유 안 함 (내 PC 에만 저장)", command=lambda: self.share_dir.set("")).grid(
            row=3, column=1, sticky="w", padx=4, pady=6)
        ttk.Label(p, text="지금 저장 위치: " + os.path.dirname(app.store.path), style="Sub.TLabel").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # ---- 파일 이름
        p = page(" 📝 파일 이름 ")
        ttk.Label(p, text="공문을 정리할 때 붙일 파일 이름", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.tpl_var = tk.StringVar(value=rn.template_of(st))
        self.datefmt_var = tk.StringVar(value=st.get("rename_date_fmt", rn.DEFAULT_DATE_FORMAT))
        ttk.Label(p, text="이름 형식").grid(row=1, column=0, sticky="w", pady=(12, 2))
        ttk.Entry(p, textvariable=self.tpl_var, width=40).grid(row=1, column=1, sticky="w", padx=6, pady=(12, 2))
        ttk.Label(p, text="날짜 모양").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Combobox(p, textvariable=self.datefmt_var, values=list(rn.DATE_FORMATS), width=14,
                     state="readonly").grid(row=2, column=1, sticky="w", padx=6)
        ttk.Button(p, text="기본값으로", command=lambda: (self.tpl_var.set(rn.DEFAULT_TEMPLATE),
                                                       self.datefmt_var.set(rn.DEFAULT_DATE_FORMAT))).grid(row=1, column=2)
        self.preview = ttk.Label(p, style="Sub.TLabel")
        self.preview.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Label(p, style="Sub.TLabel", justify="left", text=(
            "쓸 수 있는 말: {시행일자} {제목} {시행기관} {문서번호}\n"
            "올린 공문은 연도 · 기안한 달별로 자동 정리됩니다:  공문정리\\2026년\\11월\\제목.pdf")).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        for v in (self.tpl_var, self.datefmt_var):
            v.trace_add("write", lambda *_: self.update_preview())
        self.update_preview()

        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="저장", style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(bar, text="취소", command=win.destroy).pack(side="right", padx=6)
        nb.select(self.TABS.index(tab) if tab in self.TABS else 0)

    def browse(self, var):
        path = filedialog.askdirectory(parent=self.win, initialdir=var.get() or None)
        if path:
            var.set(path)

    def update_preview(self):
        sample = rn.DocInfo(title="2026년 현장지휘관 협조 요청", org="소방행정과", number="소방행정과-11072",
                            year=2026, month=11, day=16)
        self.preview.config(text="예시:  공문정리\\2026년\\11월\\" + rn.build_name(sample, self.tpl_var.get(), self.datefmt_var.get()) + ".pdf")

    def save(self):
        try:
            anchor = parse_date_text(self.date_var.get())
            pattern = core.parse_pattern(self.pattern_var.get())
        except ValueError as e:
            messagebox.showwarning("입력 확인", "[근무팀] 기준일은 YYYY-MM-DD 형식으로, 순서는 1,2,3 처럼 적어 주세요.\n%s" % e, parent=self.win)
            return
        share = self.share_dir.get().strip()
        if share and not os.path.isdir(share):
            messagebox.showwarning("공유 폴더", "공유 폴더를 찾을 수 없습니다.\n%s" % share, parent=self.win)
            return
        dl = self.dl_dir.get().strip()
        if self.dl_on.get() and not os.path.isdir(dl):
            messagebox.showwarning("다운로드 폴더", "감시할 폴더를 찾을 수 없습니다.\n%s" % dl, parent=self.win)
            return
        if self.auto_on.get() != gs.autostart_enabled():
            try:
                gs.set_autostart(self.auto_on.get())
            except OSError as e:
                messagebox.showwarning("자동 실행", "자동 실행을 바꾸지 못했습니다.\n%s" % e, parent=self.win)
        my = self.my_var.get()
        st = self.app.settings                          # 다른 설정(위젯 위치 등)은 그대로 두고 고친 것만 바꾼다
        old_share = st.get("shared_dir", "")
        st.update({
            "anchor_date": anchor.isoformat(), "pattern": pattern, "my_team": int(my[0]) if my[:1].isdigit() else 0,
            "alerts_on": self.alert_on.get(), "alert_levels": [lv for lv, v in self.lv_vars.items() if v.get()],
            "widget_flash": self.flash_var.get(),
            "watch_downloads": self.dl_on.get(), "download_dir": dl,
            "widgets": {"desk": self.w_desk.get(), "list": self.w_list.get()},
            "team_theme": self.team_theme.get(),
            "shared_dir": share, "rename_template": self.tpl_var.get(), "rename_date_fmt": self.datefmt_var.get(),
        })
        st.pop("clip_watch", None)
        st.pop("team_tint", None)
        dc = st.setdefault("desk_cal", {})
        old_dc = dict(dc)
        dc.update({"mode": self.dc_mode.get(), "theme": "light" if self.dc_theme.get() == "밝게" else "dark",
                   "alpha": int(self.dc_alpha.get().rstrip("%")) / 100, "lunar": self.dc_lunar.get(),
                   "weeknum": self.dc_week.get()})
        core.save_settings(st)
        self.win.destroy()
        self.app.apply_settings(share_changed=os.path.normcase(old_share) != os.path.normcase(share),
                                desk_changed=old_dc != dc)


# ══════════════════════════════════════════════════════════════
#  공문 검색 창 (제목 · 문서번호 · 기관 · 메모 · 붙임)
# ══════════════════════════════════════════════════════════════
class SearchWindow:
    def __init__(self, app, query=""):
        self.app = app
        self.found = []
        win = self.win = tk.Toplevel(app.root)
        win.title("공문 검색")
        win.geometry("980x540")
        win.configure(bg=BG)
        if app.root.winfo_viewable():
            win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.close)

        top = ttk.Frame(win, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="🔍", font=(FONT, 13)).pack(side="left")
        self.q = tk.StringVar(value=query)
        ent = ttk.Entry(top, textvariable=self.q, font=(FONT, 11), width=50)
        ent.pack(side="left", padx=8, ipady=2)
        ent.focus_set()
        self.q.trace_add("write", lambda *_: self.refresh())
        self.count = ttk.Label(top, text="", style="Sub.TLabel")
        self.count.pack(side="left", padx=8)
        ttk.Label(top, text="제목 · 문서번호 · 기관 · 메모 · 붙임 · 날짜(2026-11)", style="Sub.TLabel").pack(side="right")

        cols = ("date", "kind", "state", "title", "docno", "org")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col, text, width in zip(cols, ["날짜", "구분", "상태", "공문 제목", "문서번호", "시행기관"], [100, 60, 90, 430, 150, 120]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w", stretch=col == "title")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("done", foreground="#8a8f98")
        self.tree.bind("<Double-1>", lambda e: self.goto())
        ent.bind("<Return>", lambda e: self.goto(first=True))

        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="📅 달력에서 보기", style="Accent.TButton", command=self.goto).pack(side="left")
        ttk.Button(bar, text="📄 공문 열기", command=self.open_doc).pack(side="left", padx=6)
        ttk.Label(bar, text="(더블클릭 = 달력에서 보기 · 띄어 쓰면 모두 들어간 것만)", style="Sub.TLabel").pack(side="left", padx=10)
        self.refresh()

    def close(self):
        self.app.search_win = None
        self.win.destroy()

    def refresh(self):
        self.found = core.search_events(self.app.store.events, self.q.get())
        self.tree.delete(*self.tree.get_children())
        for ev in self.found[:300]:
            n = core.dday(ev["date"], self.app.today)
            state = "완료" if ev.get("done") else core.dday_text(n)
            self.tree.insert("", "end", iid=ev["id"], tags=("done",) if ev.get("done") else (),
                             values=(ev["date"], ev.get("kind", ""), state, ev["title"], ev.get("doc_no", ""), ev.get("org", "")))
        self.count.config(text=("%d건" % len(self.found)) if self.q.get().strip() else "")

    def current(self, first=False):
        sel = self.tree.selection()
        iid = sel[0] if sel else (self.tree.get_children() or [None])[0] if first else None
        return self.app.store.get(iid) if iid else None

    def goto(self, first=False):
        ev = self.current(first)
        if ev:
            self.app.show_event(ev)

    def open_doc(self):
        ev = self.current()
        if ev:
            self.app.open_event_doc(ev)


# ══════════════════════════════════════════════════════════════
#  일정 끌어서 옮기기 / Ctrl 누르고 끌면 복사
#    마우스를 따라다니는 작은 표 (어디로 옮기는지, 옮기기인지 복사인지 보여 준다)
# ══════════════════════════════════════════════════════════════
class DragGhost:
    def __init__(self, root, text):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
            self.win.attributes("-alpha", 0.92)
        except tk.TclError:
            pass
        self.lb = tk.Label(self.win, text="", font=(FONT, 9, "bold"), bg=PRIMARY, fg="#ffffff", padx=8, pady=4)
        self.lb.pack()
        self.title = text

    def show(self, x, y, copy, target=None):
        where = ("  →  %d월 %d일" % (target.month, target.day)) if target else ""
        self.lb.config(text=("⧉ 복사  " if copy else "↔ 옮기기  ") + self.title[:24] + where,
                       bg="#2e9d5b" if copy else PRIMARY)
        self.win.geometry("+%d+%d" % (x + 14, y + 12))

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()


def ctrl_down(e):
    """Ctrl 키가 눌려 있는가 (윈도우·맥·리눅스)"""
    return bool(e.state & 0x0004)


# ══════════════════════════════════════════════════════════════
#  알림 창 (화면 오른쪽 아래에 잠깐 떴다 사라지는 작은 창)
# ══════════════════════════════════════════════════════════════
class Toast:
    shown = []                                          # 지금 떠 있는 알림들 (위로 쌓는다)
    W, H = 340, 104

    def __init__(self, app, title, body, color=PRIMARY, on_open=None, timeout=20000, link_text="자세히 보기 ›"):
        self.app, self.on_open = app, on_open
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        w.configure(bg=BORDER)
        inner = tk.Frame(w, bg=CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(inner, bg=color, width=6).pack(side="left", fill="y")
        box = tk.Frame(inner, bg=CARD, padx=12, pady=8)
        box.pack(side="left", fill="both", expand=True)
        head = tk.Frame(box, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text=title, font=(FONT, 10, "bold"), fg=color, bg=CARD).pack(side="left")
        x = tk.Label(head, text="✕", font=(FONT, 10), fg=SUB, bg=CARD, cursor="hand2")
        x.pack(side="right")
        x.bind("<Button-1>", lambda e: self.close())
        tk.Label(box, text=body, font=(FONT, 9), fg=TEXT, bg=CARD, justify="left", anchor="w",
                 wraplength=self.W - 50).pack(fill="x", pady=(4, 0))
        if on_open:
            link = tk.Label(box, text=link_text, font=(FONT, 9, "bold"), fg=PRIMARY, bg=CARD, cursor="hand2")
            link.pack(anchor="e")
            link.bind("<Button-1>", lambda e: self.open())
        Toast.shown.append(self)
        self.place()
        w.after(timeout, self.close)
        try:
            w.bell()
        except tk.TclError:
            pass

    def place(self):
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        i = Toast.shown.index(self)
        self.win.geometry("%dx%d+%d+%d" % (self.W, self.H, sw - self.W - 16, sh - 70 - (self.H + 10) * (i + 1)))

    def open(self):
        cb = self.on_open
        self.close()
        if cb:
            cb()

    def close(self):
        if self in Toast.shown:
            Toast.shown.remove(self)
            for t in Toast.shown:
                t.place()
        if self.win.winfo_exists():
            self.win.destroy()


# ══════════════════════════════════════════════════════════════
#  일정 설정 / 메모 창 (일정을 더블클릭하거나, 날짜 빈 곳을 더블클릭하면 열린다)
#    달력에 보일 글자 · 날짜 · 시간 · 구분 · 색깔 · 반복(메모) · 메모 · 완료(가운데 줄)
# ══════════════════════════════════════════════════════════════
class DocPicker:
    """메모에 연결할 공문을 달력에 올린 공문 중에서 고르는 창 (여러 개 고를 수 있다)"""

    def __init__(self, app, parent, on_pick, exclude=()):
        self.app, self.on_pick = app, on_pick
        self.docs = [e for e in core.doc_list(app.store.events) if core.link_key(e) not in set(exclude)]
        win = self.win = tk.Toplevel(parent)
        win.title("관련 공문 고르기")
        win.geometry("760x460")
        win.configure(bg=BG)
        win.transient(parent)
        top = ttk.Frame(win, padding=(12, 12, 12, 6))
        top.pack(fill="x")
        ttk.Label(top, text="🔍").pack(side="left")
        self.q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.q, width=44)
        ent.pack(side="left", padx=8)
        ent.focus_set()
        self.q.trace_add("write", lambda *_: self.refresh())
        ttk.Label(top, text="제목 · 문서번호 · 기관  (Ctrl/Shift 로 여러 개)", style="Sub.TLabel").pack(side="left")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        cols = ("date", "title", "docno")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="extended")
        for col, text, width in zip(cols, ["날짜", "공문 제목", "문서번호"], [95, 470, 150]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w", stretch=col == "title")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.ok())
        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        self.cnt = ttk.Label(bar, text="", style="Sub.TLabel")
        self.cnt.pack(side="left")
        ttk.Button(bar, text="연결하기", style="Accent.TButton", command=self.ok).pack(side="right")
        ttk.Button(bar, text="취소", command=win.destroy).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>", lambda e: self.ok())
        self.refresh()

    def refresh(self):
        words = [_w for _w in self.q.get().split() if _w]
        self.shown = [e for e in self.docs if all(w in " ".join([e.get("title", ""), e.get("doc_no", ""), e.get("org", "")])
                                                  for w in words)]
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.shown[:300]):
            self.tree.insert("", "end", iid=str(i), values=(e["date"], e["title"], e.get("doc_no", "")))
        self.cnt.config(text="공문 %d건" % len(self.shown))

    def ok(self):
        picked = [core.make_link(self.shown[int(i)]) for i in self.tree.selection()]
        if picked:
            self.on_pick(picked)
        self.win.destroy()


class EventDialog:
    def __init__(self, app, ev=None, day=None):
        self.app, self.ev = app, ev
        new = ev is None
        # 반복 일정의 한 날짜를 열면 원본(시리즈)을 고친다. 완료만 그날 것.
        self.master = app.store.get(ev["series"]) if ev and ev.get("series") else ev
        src = self.master or {}
        is_memo = new or src.get("kind") == "메모"
        self.is_memo = is_memo
        day = day or (dt.date.fromisoformat(src["date"]) if src else dt.date.today())
        win = self.win = tk.Toplevel(app.root)
        win.title("메모 추가" if new else "일정 설정")
        win.configure(bg=BG)
        win.resizable(False, False)
        if app.root.winfo_viewable():
            win.transient(app.root)
        box = ttk.Frame(win, padding=18)
        box.pack(fill="both", expand=True)

        if new:
            head = "📝 %d월 %d일 (%s) 메모 · 일정 추가" % (day.month, day.day, "월화수목금토일"[day.weekday()])
        else:
            head = ("📝 메모" if is_memo else "📄 공문 일정") + "  ·  " + src["title"]
        ttk.Label(box, text=head, style="Head.TLabel", wraplength=540, justify="left").grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 12))

        self.label_var = tk.StringVar(value="" if new else ev_label(src))
        self.date_var = tk.StringVar(value=day.isoformat())
        self.time_var = tk.StringVar(value=src.get("time", ""))
        self.kind_var = tk.StringVar(value=src.get("kind", "메모"))
        self.color = src.get("color", "초록" if new else "")
        self.done_var = tk.BooleanVar(value=bool((ev or {}).get("done")))

        ttk.Label(box, text="달력에 보일 글자").grid(row=1, column=0, sticky="w")
        ent = ttk.Entry(box, textvariable=self.label_var, width=48, font=(FONT, 11))
        ent.grid(row=1, column=1, columnspan=5, sticky="we", padx=(8, 0), pady=3)
        ttk.Label(box, text="반복 시작일" if src.get("repeat") else "날짜").grid(row=2, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.date_var, width=12).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=3)
        ttk.Label(box, text="시간").grid(row=2, column=2, sticky="e", padx=(10, 4))
        ttk.Entry(box, textvariable=self.time_var, width=7).grid(row=2, column=3, sticky="w")
        ttk.Label(box, text="구분").grid(row=2, column=4, sticky="e", padx=(10, 4))
        ttk.Combobox(box, textvariable=self.kind_var, values=KINDS, width=7, state="readonly").grid(row=2, column=5, sticky="w")

        ttk.Label(box, text="색깔").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        sw = ttk.Frame(box)
        sw.grid(row=3, column=1, columnspan=5, sticky="w", padx=(8, 0), pady=(8, 0))
        self.swatches = {}
        for i, name in enumerate(COLOR_NAMES):
            bg, fg = EVENT_COLORS.get(name, ("#ffffff", SUB))
            lb = tk.Label(sw, text=name, bg=bg, fg=fg, font=(FONT, 9, "bold"), width=5, pady=3, cursor="hand2",
                          highlightthickness=2, highlightbackground=BG)
            lb.grid(row=0, column=i, padx=2, pady=2)
            lb.bind("<Button-1>", lambda e, n=name: self.pick_color(n))
            self.swatches[name] = lb
        ttk.Label(box, text="자동 = 기한이 가까우면 노랑, 지나면 빨강", style="Sub.TLabel").grid(
            row=4, column=1, columnspan=5, sticky="w", padx=(8, 0))
        self.pick_color(self.color or "자동")

        # ---- 반복 (메모만)
        self.rep_frame = None
        if is_memo:
            self.build_repeat(box, src.get("repeat") or {})

        ttk.Label(box, text="메모").grid(row=6, column=0, sticky="nw", pady=(10, 0))
        self.memo = tk.Text(box, width=54, height=4, wrap="word", font=(FONT, 10), relief="flat", bg="#fbfcfe",
                            highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY, padx=6, pady=4)
        self.memo.grid(row=6, column=1, columnspan=5, sticky="we", padx=(8, 0), pady=(10, 0))
        self.memo.insert("1.0", src.get("memo", ""))

        # ---- 관련 공문 (메모만)
        self.links = [dict(x) for x in (src.get("links") or [])]
        self.link_list = None
        if is_memo:
            ttk.Label(box, text="🔗 관련 공문").grid(row=7, column=0, sticky="nw", pady=(10, 0))
            lf = ttk.Frame(box)
            lf.grid(row=7, column=1, columnspan=5, sticky="we", padx=(8, 0), pady=(10, 0))
            self.link_list = listbox(lf, height=3, font=(FONT, 9))
            self.link_list.pack(side="left", fill="x", expand=True)
            lb_ = ttk.Frame(lf)
            lb_.pack(side="left", padx=(6, 0))
            ttk.Button(lb_, text="＋ 달력의 공문", command=self.add_doc_link).pack(fill="x")
            ttk.Button(lb_, text="＋ 파일", command=self.add_file_link).pack(fill="x", pady=2)
            ttk.Button(lb_, text="빼기", command=self.remove_link).pack(fill="x")
            self.link_list.bind("<Double-1>", lambda e: self.open_link())
            self.refresh_links()

        done = tk.Frame(box, bg="#eef7f0" if self.done_var.get() else "#f6f7f9", padx=10, pady=6)
        done.grid(row=8, column=0, columnspan=6, sticky="we", pady=(12, 0))
        done_text = "✔ 완료  (달력에 가운데 줄을 긋고, 기한 알림을 멈춥니다)"
        if ev and ev.get("series"):
            d0 = dt.date.fromisoformat(ev["date"])
            done_text = "✔ %d월 %d일 것만 완료  (반복되는 다른 날은 그대로)" % (d0.month, d0.day)
        self.done_cb = tk.Checkbutton(done, text=done_text, variable=self.done_var, font=(FONT, 10, "bold"), fg=TEXT,
                                      bd=0, bg=done["bg"], activebackground=done["bg"], highlightthickness=0)
        self.done_cb.pack(anchor="w")
        self.done_frame = done

        def recolor(*_):
            c = "#eef7f0" if self.done_var.get() else "#f6f7f9"
            self.done_frame.config(bg=c)
            self.done_cb.config(bg=c, activebackground=c, fg="#1d6b3e" if self.done_var.get() else TEXT)
        self.done_var.trace_add("write", recolor)

        bar = ttk.Frame(box)
        bar.grid(row=9, column=0, columnspan=6, sticky="we", pady=(14, 0))
        ttk.Button(bar, text="저장", style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(bar, text="취소", command=win.destroy).pack(side="right", padx=6)
        if not new:
            ttk.Button(bar, text="🗑 삭제", style="Danger.TButton", command=self.delete).pack(side="left")
            if core.resolve_doc_path(src):
                ttk.Button(bar, text="📄 원본 공문 열기", command=lambda: app.open_event_doc(src)).pack(side="left", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Control-Return>", lambda e: self.save())
        ent.focus_set()
        ent.select_range(0, "end")

    # ---- 관련 공문 연결 -------------------------------------------------------
    def refresh_links(self):
        self.link_list.delete(0, "end")
        for lk in self.links:
            self.link_list.insert("end", ("📄 " if lk.get("key") else "📎 ") + lk.get("title", "") +
                                  (("  (%s)" % lk["doc_no"]) if lk.get("doc_no") else ""))
        if not self.links:
            self.link_list.insert("end", "  (연결한 공문 없음 - 오른쪽 버튼으로 추가)")
            self.link_list.itemconfig("end", fg="#9aa0aa")

    def add_doc_link(self):
        have = [lk["key"] for lk in self.links if lk.get("key")]
        if not core.doc_list(self.app.store.events):
            messagebox.showinfo("안내", "달력에 올린 공문이 아직 없어요.\n[＋ 공문 추가]로 먼저 올리거나 [＋ 파일]로 연결하세요.", parent=self.win)
            return

        def got(items):
            self.links.extend(items)
            self.refresh_links()
        DocPicker(self.app, self.win, got, exclude=have)

    def add_file_link(self):
        path = filedialog.askopenfilename(parent=self.win, title="연결할 공문 파일",
                                          filetypes=[("공문 파일", "*.pdf *.hwpx *.hwp *.txt *.docx"), ("모든 파일", "*.*")])
        if path:
            self.links.append({"file": path, "title": os.path.basename(path)})
            self.refresh_links()

    def remove_link(self):
        sel = self.link_list.curselection()
        if sel and sel[0] < len(self.links):
            del self.links[sel[0]]
            self.refresh_links()

    def open_link(self):
        sel = self.link_list.curselection()
        if sel and sel[0] < len(self.links):
            self.app.open_link(self.links[sel[0]])

    # ---- 반복 설정 칸 ---------------------------------------------------------
    def build_repeat(self, box, r):
        ttk.Label(box, text="🔁 반복").grid(row=5, column=0, sticky="nw", pady=(12, 0))
        f = self.rep_frame = tk.Frame(box, bg="#f6f7f9", padx=10, pady=8)
        f.grid(row=5, column=1, columnspan=5, sticky="we", padx=(8, 0), pady=(12, 0))
        names = [n for _, n in core.REPEAT_TYPES]
        keys = [k for k, _ in core.REPEAT_TYPES]
        self.rep_keys = dict(zip(names, keys))
        start = parse_date_text(self.date_var.get())
        self.rep_type = tk.StringVar(value=names[keys.index(r.get("type", "none"))] if r.get("type", "none") in keys else names[0])
        self.rep_n = tk.StringVar(value=str(r.get("n", 2 if r.get("type") == "ndays" else 1)))
        self.rep_days = [tk.BooleanVar(value=i in (r.get("days") or [start.weekday()])) for i in range(7)]
        self.rep_day = tk.StringVar(value=str(r.get("day", start.day)))
        nth_names = list(core.NTH_NAMES.values())
        self.rep_nth = tk.StringVar(value=core.NTH_NAMES.get(int(r.get("nth", (start.day - 1) // 7 + 1)), "첫째"))
        self.rep_wd = tk.StringVar(value=core.WEEKDAY_NAMES[int(r.get("wd", start.weekday()))] + "요일")
        self.rep_workday = tk.BooleanVar(value=bool(r.get("workday")))
        self.rep_end = tk.StringVar(value="until" if r.get("until") else ("count" if r.get("count") else "none"))
        self.rep_until = tk.StringVar(value=r.get("until") or (start + dt.timedelta(days=90)).isoformat())
        self.rep_count = tk.StringVar(value=str(r.get("count") or 10))

        top = tk.Frame(f, bg=f["bg"])
        top.pack(fill="x")
        ttk.Combobox(top, textvariable=self.rep_type, values=names, width=18, state="readonly").pack(side="left")
        self.rep_opt = tk.Frame(top, bg=f["bg"])                      # 종류마다 바뀌는 칸
        self.rep_opt.pack(side="left", padx=(8, 0))
        self.rep_more = tk.Frame(f, bg=f["bg"])                       # 주말 옮기기 · 끝나는 때 · 미리보기
        self.rep_more.pack(fill="x", pady=(6, 0))
        self.rep_preview = tk.Label(f, text="", bg=f["bg"], fg="#5b3a9c", font=(FONT, 9), anchor="w", justify="left")
        self.rep_preview.pack(fill="x", pady=(4, 0))
        self.nth_names = nth_names
        for v in [self.rep_type, self.rep_n, self.rep_day, self.rep_nth, self.rep_wd, self.rep_workday, self.rep_end,
                  self.rep_until, self.rep_count, self.date_var] + self.rep_days:
            v.trace_add("write", lambda *_: self.update_repeat_preview())
        self.rep_type.trace_add("write", lambda *_: self.layout_repeat())
        self.layout_repeat()

    def _spin(self, parent, var, lo, hi, width=4):
        return tk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=width, font=(FONT, 10), relief="flat",
                          highlightthickness=1, highlightbackground=BORDER, justify="center")

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, bg=parent["bg"], font=(FONT, 10))

    def _chk(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=parent["bg"], activebackground=parent["bg"],
                              font=(FONT, 10), bd=0, highlightthickness=0)

    def layout_repeat(self):
        for w in self.rep_opt.winfo_children() + self.rep_more.winfo_children():
            w.destroy()
        t = self.rep_keys[self.rep_type.get()]
        o, m = self.rep_opt, self.rep_more
        if t == "ndays":
            self._spin(o, self.rep_n, 2, 365).pack(side="left")
            self._lbl(o, "일마다").pack(side="left", padx=4)
        elif t == "weekly":
            self._spin(o, self.rep_n, 1, 8, 3).pack(side="left")
            self._lbl(o, "주마다").pack(side="left", padx=(4, 8))
            for i, name in enumerate(core.WEEKDAY_NAMES):
                self._chk(o, name, self.rep_days[i]).pack(side="left")
        elif t == "monthly":
            self._spin(o, self.rep_day, 1, 31, 3).pack(side="left")
            self._lbl(o, "일  (없는 날이면 그달 말일)").pack(side="left", padx=4)
        elif t == "nth_weekday":
            ttk.Combobox(o, textvariable=self.rep_nth, values=self.nth_names, width=6, state="readonly").pack(side="left")
            ttk.Combobox(o, textvariable=self.rep_wd, values=[d + "요일" for d in core.WEEKDAY_NAMES], width=6,
                         state="readonly").pack(side="left", padx=4)
        if t in ("monthly", "month_start", "month_end", "nth_weekday", "yearly"):
            self._chk(m, "주말·공휴일이면 평일로 옮기기", self.rep_workday).pack(anchor="w")
        if t != "none":
            row = tk.Frame(m, bg=m["bg"])
            row.pack(anchor="w", pady=(2, 0))
            self._lbl(row, "끝:").pack(side="left")
            for val, text in (("none", "계속"), ("until", "날짜까지"), ("count", "횟수")):
                tk.Radiobutton(row, text=text, value=val, variable=self.rep_end, bg=m["bg"], activebackground=m["bg"],
                               font=(FONT, 10), bd=0, highlightthickness=0).pack(side="left", padx=(6, 0))
            ttk.Entry(row, textvariable=self.rep_until, width=11).pack(side="left", padx=(8, 0))
            self._spin(row, self.rep_count, 1, 999).pack(side="left", padx=(6, 0))
            self._lbl(row, "회").pack(side="left")
        self.update_repeat_preview()

    def build_repeat_rule(self):
        """화면 값 -> 반복 규칙 dict (반복 안 함이면 None). 값이 잘못되면 ValueError"""
        if self.rep_frame is None:
            return None
        t = self.rep_keys[self.rep_type.get()]
        if t == "none":
            return None
        r = {"type": t}
        if t in ("ndays", "weekly"):
            r["n"] = int(self.rep_n.get())
        if t == "weekly":
            r["days"] = [i for i, v in enumerate(self.rep_days) if v.get()]
            if not r["days"]:
                raise ValueError("요일을 하나 이상 골라 주세요.")
        if t == "monthly":
            r["day"] = max(1, min(31, int(self.rep_day.get())))
        if t == "nth_weekday":
            r["nth"] = {v: k for k, v in core.NTH_NAMES.items()}[self.rep_nth.get()]
            r["wd"] = core.WEEKDAY_NAMES.index(self.rep_wd.get()[0])
        if t in ("monthly", "month_start", "month_end", "nth_weekday", "yearly") and self.rep_workday.get():
            r["workday"] = True
        if self.rep_end.get() == "until":
            r["until"] = parse_date_text(self.rep_until.get()).isoformat()
        elif self.rep_end.get() == "count":
            r["count"] = max(1, int(self.rep_count.get()))
        return r

    def update_repeat_preview(self):
        if self.rep_frame is None:
            return
        try:
            r = self.build_repeat_rule()
            if not r:
                self.rep_preview.config(text="")
                return
            start = parse_date_text(self.date_var.get())
            ds = core.repeat_dates({"date": start.isoformat(), "repeat": r}, start, start + dt.timedelta(days=800))[:5]
            nxt = ", ".join("%d/%d(%s)" % (d.month, d.day, "월화수목금토일"[d.weekday()]) for d in ds)
            self.rep_preview.config(text="🔁 " + core.describe_repeat(r) + ("\n다음: " + nxt if nxt else "\n(해당하는 날이 없어요)"))
        except (ValueError, KeyError) as e:
            self.rep_preview.config(text="⚠ " + (str(e) if "요일" in str(e) else "숫자·날짜를 확인해 주세요"))

    def pick_color(self, name):
        self.color = "" if name == "자동" else name
        for n, lb in self.swatches.items():
            lb.config(highlightbackground=PRIMARY if n == name else BG)

    def save(self):
        label = self.label_var.get().strip()
        if not label:
            messagebox.showinfo("안내", "달력에 보일 글자를 적어 주세요.", parent=self.win)
            return
        try:
            d = parse_date_text(self.date_var.get())
            tm = parse_time_text(self.time_var.get())
            rule = self.build_repeat_rule()
        except ValueError as e:
            msg = str(e) if "요일" in str(e) else "날짜는 2026-12-03, 시간은 14:00 처럼 적어 주세요."
            messagebox.showwarning("입력 확인", msg, parent=self.win)
            return
        done = self.done_var.get()
        fields = {"date": d.isoformat(), "time": tm, "kind": self.kind_var.get(), "color": self.color,
                  "memo": self.memo.get("1.0", "end").strip()}
        if self.is_memo:
            fields["repeat"] = rule
            fields["links"] = self.links
        store, ev, master = self.app.store, self.ev, self.master
        if ev is None:                                  # 새 메모
            new = dict(fields, title=label, label="", done=done and not rule,
                       done_at=d.isoformat() if done and not rule else "")
            store.add(new)
            sel_id, go = new["id"], d
        else:
            fields["label"] = "" if label == master["title"] else label      # 공문 제목과 같으면 따로 저장 안 함
            if master.get("kind") == "메모":
                fields["title"], fields["label"] = label, ""
            if ev.get("series"):                        # 반복 일정의 한 날: 원본을 고치고, 완료는 그날만
                if done != bool(ev.get("done")):
                    store.toggle_done(ev["id"])
                store.update(master["id"], fields)
                sel_id, go = ev["id"], dt.date.fromisoformat(ev["date"])
            else:
                if rule:
                    fields["done"], fields["done_at"] = False, ""
                else:
                    fields["done"] = done
                    if done != bool(master.get("done")):
                        fields["done_at"] = dt.date.today().isoformat() if done else ""
                store.update(master["id"], fields)
                sel_id, go = master["id"], d
                if rule:
                    sel_id = None
        self.win.destroy()
        self.app.pending_select_id = sel_id
        self.app.go_to(go)

    def delete(self):
        self.win.destroy()
        self.app.delete_given(self.ev)


# ══════════════════════════════════════════════════════════════
#  업무 처리 현황 창 (했는지 / 안 했는지 한눈에)
# ══════════════════════════════════════════════════════════════
class StatusWindow:
    FILTERS = ["미처리", "기한초과", "완료", "전체"]

    def __init__(self, app):
        self.app = app
        win = self.win = tk.Toplevel(app.root)
        win.title("업무 처리 현황")
        win.geometry("1080x560")
        win.configure(bg=BG)
        if app.root.winfo_viewable():
            win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.close)

        top = ttk.Frame(win, padding=12)
        top.pack(fill="x")
        self.filter_var = tk.StringVar(value="미처리")
        for name in self.FILTERS:
            ttk.Radiobutton(top, text=name, value=name, variable=self.filter_var, command=self.refresh).pack(side="left", padx=4)
        self.sum_var = tk.StringVar()
        ttk.Label(top, textvariable=self.sum_var, font=(FONT, 10, "bold")).pack(side="right")

        cols = ("state", "mine", "kind", "date", "time", "title", "docno", "done_at")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
        for col, text, width in zip(cols, ["상태", "실적", "구분", "기한일", "시간", "공문 제목", "문서번호", "완료일"],
                                    [100, 40, 60, 95, 55, 470, 140, 90]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w", stretch=col == "title")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("late", foreground="#a12622")
        self.tree.tag_configure("soon", foreground="#7a5b00")
        self.tree.tag_configure("done", foreground="#8a8f98", font=(FONT, 9, "overstrike"))   # 완료 = 가운데 줄
        self.tree.bind("<Double-1>", lambda e: self.goto())
        for b in ("<Button-3>", "<Button-2>"):
            self.tree.bind(b, self.on_right_click)

        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="✔ 완료 / 되돌리기", style="Accent.TButton", command=self.toggle).pack(side="left")
        ttk.Button(bar, text="📄 공문 열기", command=self.open_doc).pack(side="left", padx=6)
        ttk.Button(bar, text="📅 달력에서 보기", command=self.goto).pack(side="left")
        ttk.Button(bar, text="📊 엑셀로 저장", command=lambda: app.export_xlsx(parent=self.win)).pack(side="right")
        ttk.Label(bar, text="(더블클릭 = 달력에서 공문 내용 보기 · 우클릭 = 메뉴)", style="Sub.TLabel").pack(side="right", padx=10)
        self.refresh()

    def close(self):
        self.app.status_win = None
        self.win.destroy()

    def state_of(self, ev):
        if ev.get("done"):
            return "완료", "done"
        n = core.dday(ev["date"], self.app.today)
        if n < 0:
            return "기한초과 " + core.dday_text(n), "late"
        if n <= 3:
            return core.dday_text(n), "soon"
        return core.dday_text(n), ""

    def refresh(self):
        evs = sorted(self.app.store.events, key=lambda e: (e["date"], e.get("time") or ""))
        total = len(evs)
        done = sum(1 for e in evs if e.get("done"))
        late = sum(1 for e in evs if not e.get("done") and core.dday(e["date"], self.app.today) < 0)
        self.sum_var.set("전체 %d건 · 완료 %d · 미처리 %d · 기한초과 %d" % (total, done, total - done, late))

        mode = self.filter_var.get()
        self.tree.delete(*self.tree.get_children())
        for ev in evs:
            text, tag = self.state_of(ev)
            if mode == "미처리" and ev.get("done"):
                continue
            if mode == "완료" and not ev.get("done"):
                continue
            if mode == "기한초과" and tag != "late":
                continue
            self.tree.insert("", "end", iid=ev["id"], tags=(tag,) if tag else (),
                             values=(text, "★" if ev.get("mine") else "", ev.get("kind", ""), ev["date"], ev.get("time", ""),
                                     ev_label(ev), ev.get("doc_no", ""), ev.get("done_at", "")))

    def current(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("안내", "목록에서 업무를 먼저 선택해 주세요.", parent=self.win)
            return None
        return self.app.store.get(sel[0])

    def toggle(self):
        ev = self.current()
        if ev:
            self.app.store.toggle_done(ev["id"])
            self.app.refresh()                          # 달력과 이 창이 같이 새로고침된다

    def on_right_click(self, e):
        iid = self.tree.identify_row(e.y)               # 마우스 아래 행을 선택하고 우클릭 메뉴
        if not iid:
            return
        self.tree.selection_set(iid)
        ev = self.app.store.get(iid)
        if ev:
            self.app.popup_menu(e.x_root, e.y_root, ev)

    def open_doc(self):
        ev = self.current()
        if ev:
            self.app.open_event_doc(ev)

    def goto(self):
        ev = self.current()
        if ev:
            self.app.show_event(ev)



# ══════════════════════════════════════════════════════════════
#  실적 메모 창 (내가 한 역할·성과를 적어 둔다 → 자기역량기술서에 그대로 쓴다)
# ══════════════════════════════════════════════════════════════
class NoteDialog:
    def __init__(self, app, ev):
        self.app, self.ev = app, ev
        win = self.win = tk.Toplevel(app.root)
        win.title("실적 메모")
        if app.root.winfo_viewable():
            win.transient(app.root)
        box = ttk.Frame(win, padding=12)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text=ev["title"], font=(FONT, 10, "bold"), wraplength=420).pack(anchor="w")
        ttk.Label(box, text="내가 한 일 / 역할 / 성과를 적어 두세요. (자기역량기술서에 그대로 붙여넣을 수 있어요)",
                  style="Sub.TLabel").pack(anchor="w", pady=(4, 6))
        self.text = tk.Text(box, width=56, height=7, wrap="word", font=(FONT, 10))
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", ev.get("note", ""))
        self.mine_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, text="★ 내 실적에 포함", variable=self.mine_var).pack(anchor="w", pady=6)
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Button(row, text="저장", command=self.save).pack(side="right")
        ttk.Button(row, text="취소", command=win.destroy).pack(side="right", padx=6)

    def save(self):
        self.app.store.set_note(self.ev["id"], self.text.get("1.0", "end").strip())
        if self.mine_var.get() != bool(self.ev.get("mine")):
            self.app.store.toggle_mine(self.ev["id"])
        self.win.destroy()
        self.app.refresh()


# ══════════════════════════════════════════════════════════════
#  내 실적 정리 창 (근평·자기역량기술서용: 기간별로 내가 한 업무를 모아 본다)
# ══════════════════════════════════════════════════════════════
class AchievementWindow:
    def __init__(self, app):
        self.app = app
        self.shown = []                                 # 지금 목록에 보이는 일정들
        win = self.win = tk.Toplevel(app.root)
        win.title("내 실적 정리 (자기역량기술서)")
        win.geometry("1000x600")
        win.configure(bg=BG)
        if app.root.winfo_viewable():
            win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.close)

        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        today = dt.date.today()
        ttk.Label(top, text="기간").pack(side="left")
        self.year_var = tk.StringVar(value=str(today.year))
        years = sorted({str(today.year), str(today.year - 1)} | {core.achievement_date(e)[:4] for e in app.store.events}, reverse=True)
        ttk.Combobox(top, textvariable=self.year_var, values=years, width=6, state="readonly").pack(side="left", padx=4)
        self.half_var = tk.StringVar(value="하반기" if today.month >= 7 else "상반기")
        for name in ["상반기", "하반기", "연간", "전체"]:
            ttk.Radiobutton(top, text=name, value=name, variable=self.half_var, command=self.refresh).pack(side="left", padx=3)
        self.only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="★ 내 실적만 보기", variable=self.only_var, command=self.refresh).pack(side="left", padx=14)
        self.sum_var = tk.StringVar()
        ttk.Label(top, textvariable=self.sum_var, font=(FONT, 10, "bold")).pack(side="right")

        cols = ("mine", "date", "kind", "title", "docno", "note")
        self.tree = ttk.Treeview(win, columns=cols, show="headings", height=16)
        for col, text, width in zip(cols, ["실적", "날짜", "구분", "공문 제목", "문서번호", "내 메모"], [45, 95, 60, 380, 130, 250]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8)
        self.tree.tag_configure("mine", foreground="#1f4e9c")
        self.tree.bind("<Double-1>", lambda e: self.open_doc())

        tip = ttk.Label(win, style="Sub.TLabel", padding=(8, 2),
                        text="'★ 내 실적만 보기'를 끄면 그 기간의 모든 업무가 보입니다. 업무를 고르고 [★ 실적 넣기/빼기]를 누르세요.  (날짜는 완료한 날, 완료 전이면 기한일)")
        tip.pack(anchor="w")
        bar = ttk.Frame(win, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="★ 실적 넣기/빼기", command=self.toggle_mine).pack(side="left")
        ttk.Button(bar, text="📝 메모 쓰기", command=self.edit_note).pack(side="left", padx=6)
        ttk.Button(bar, text="📄 공문 열기", command=self.open_doc).pack(side="left")
        ttk.Button(bar, text="글로 복사 (자기역량기술서용)", command=self.copy_text).pack(side="right")
        ttk.Button(bar, text="파일로 저장", command=self.save_file).pack(side="right", padx=6)
        self.refresh()

    def close(self):
        self.app.ach_win = None
        self.win.destroy()

    def refresh(self):
        year = int(self.year_var.get())
        half = self.half_var.get()
        evs = [e for e in self.app.store.events if core.in_period(e, year, half)]
        self.shown = sorted([e for e in evs if e.get("mine")] if self.only_var.get() else evs, key=core.achievement_date)
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for ev in self.shown:
            self.tree.insert("", "end", iid=ev["id"], tags=("mine",) if ev.get("mine") else (),
                             values=("★" if ev.get("mine") else "", core.achievement_date(ev), ev.get("kind", ""),
                                     ev["title"], ev.get("doc_no", ""), (ev.get("note") or "").replace("\n", " ")))
        mine = sum(1 for e in evs if e.get("mine"))
        self.sum_var.set("%s %s: 업무 %d건 중 내 실적 %d건" % (self.year_var.get(), half, len(evs), mine))

    def current(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("안내", "목록에서 업무를 먼저 선택해 주세요.", parent=self.win)
            return None
        return self.app.store.get(sel[0])

    def toggle_mine(self):
        ev = self.current()
        if ev:
            self.app.store.toggle_mine(ev["id"])
            self.app.refresh()

    def edit_note(self):
        ev = self.current()
        if ev:
            NoteDialog(self.app, ev)

    def open_doc(self):
        ev = self.current()
        if ev:
            self.app.open_event_doc(ev)

    def make_text(self):
        mine = [e for e in self.shown if e.get("mine")]
        if not mine:
            messagebox.showinfo("안내", "★ 내 실적으로 표시한 업무가 없습니다.", parent=self.win)
            return ""
        return core.achievement_text(mine, "[%s %s 업무 실적]" % (self.year_var.get(), self.half_var.get()))

    def copy_text(self):
        text = self.make_text()
        if text:
            self.win.clipboard_clear()
            self.win.clipboard_append(text)
            messagebox.showinfo("복사 완료", "복사했습니다.\n자기역량기술서(한글·워드)에 붙여넣기(Ctrl+V) 하세요.", parent=self.win)

    def save_file(self):
        text = self.make_text()
        if not text:
            return
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".txt", initialfile="내실적_정리.txt",
                                            filetypes=[("글자 파일", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(text)
            messagebox.showinfo("완료", "저장했습니다.", parent=self.win)




# ══════════════════════════════════════════════════════════════
#  바탕화면 위젯  (테두리 없는 작은 창: 오늘 근무팀 + 오늘/임박 일정)
#    - 위쪽 날짜 줄을 끌면 이동 / 오른쪽 아래 ◢ 를 끌면 크기 조절
#    - 📌 항상 위 켜기·끄기 / ◐ 투명도 / ▣ 달력 열기 / ✕ 닫기 / 우클릭 메뉴
# ══════════════════════════════════════════════════════════════
class WidgetWindow:
    BG = "#1f2430"
    HEAD = "#2a3040"
    FG = "#f2f4f8"
    SUB = "#9aa3b5"

    def __init__(self, app):
        self.app = app
        self.cfg = app.settings.setdefault("widget", {})
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)                 # 테두리·제목 표시줄 없애기
        self.win.configure(bg=self.BG)
        self.topmost = bool(self.cfg.get("topmost", True))
        self.alpha = float(self.cfg.get("alpha", 0.92))
        screen = gs.virtual_screen() or (0, 0, self.win.winfo_screenwidth(), self.win.winfo_screenheight())
        x, y, w, h = gs.fit_window(int(self.cfg.get("x", 60)), int(self.cfg.get("y", 60)),
                                   int(self.cfg.get("w", 300)), int(self.cfg.get("h", 420)), screen)
        self.win.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self._ready, self._cfg_job = False, None
        self.win.after(800, lambda: setattr(self, "_ready", True))
        self.win.bind("<Configure>", lambda e: self.cfg_changed() if e.widget is self.win else None)
        self.apply_window_attrs()
        self._drag = (0, 0)
        self._job = None
        self.rows = []                                  # 화면에 보이는 일정들 (클릭할 때 쓴다)

        self.head = tk.Frame(self.win, bg=self.HEAD)
        self.head.pack(fill="x")
        self.date_lb = tk.Label(self.head, font=(FONT, 13, "bold"), fg=self.FG, bg=self.HEAD, anchor="w")
        self.date_lb.pack(side="left", padx=(10, 4), pady=6)
        self.team_lb = tk.Label(self.head, font=(FONT, 9, "bold"), fg="#ffffff", bg="#777777", padx=6)
        self.team_lb.pack(side="left")
        for text, cmd in (("✕", self.close), ("▣", self.show_main), ("◐", self.cycle_alpha), ("📌", self.toggle_topmost)):
            b = tk.Label(self.head, text=text, font=(FONT, 10), fg=self.SUB, bg=self.HEAD, cursor="hand2", padx=4)
            b.pack(side="right")
            b.bind("<Button-1>", lambda e, c=cmd: c())
            b.bind("<Enter>", lambda e, w=b: w.config(fg=self.FG))
            b.bind("<Leave>", lambda e, w=b: w.config(fg=self.SUB))
            if text == "📌":
                self.pin_lb = b

        self.drop_ok = gs.enable_file_drop(self.win, app.on_drop)    # 공문 PDF 를 끌어다 놓으면 등록
        tk.Label(self.win, text="📥 PDF 를 끌어다 놓으면 공문 등록", font=(FONT, 8), fg=self.SUB, bg=self.BG).pack(
            side="bottom", anchor="w", padx=10, pady=(0, 6))
        self.body = tk.Frame(self.win, bg=self.BG)
        self.body.pack(fill="both", expand=True, padx=8, pady=(6, 4))

        grip = tk.Label(self.win, text="◢", font=(FONT, 9), fg=self.SUB, bg=self.BG, cursor="sizing")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<Button-1>", self.start_resize)
        grip.bind("<B1-Motion>", self.do_resize)
        grip.bind("<ButtonRelease-1>", lambda e: self.save_cfg())

        for wdg in (self.head, self.date_lb, self.team_lb):   # 날짜 줄을 끌어서 이동
            wdg.bind("<Button-1>", self.start_move)
            wdg.bind("<B1-Motion>", self.do_move)
            wdg.bind("<ButtonRelease-1>", lambda e: self.save_cfg())
        for wdg in (self.win, self.head, self.body):
            for b3 in ("<Button-3>", "<Button-2>"):
                wdg.bind(b3, self.popup)

        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="항상 위 켜기/끄기", command=self.toggle_topmost)
        self.menu.add_command(label="투명도 바꾸기", command=self.cycle_alpha)
        self.menu.add_command(label="달력 열기", command=self.show_main)
        self.menu.add_separator()
        self.menu.add_command(label="위젯 닫기", command=self.close)

        self.refresh()
        self.tick()

    # ---- 창 속성 ---------------------------------------------------------
    def apply_window_attrs(self):
        try:
            self.win.attributes("-topmost", self.topmost)
            self.win.attributes("-alpha", self.alpha)
        except tk.TclError:                             # 일부 환경은 투명도를 지원하지 않는다
            pass

    def toggle_topmost(self):
        self.topmost = not self.topmost
        self.apply_window_attrs()
        self.pin_lb.config(fg=self.FG if self.topmost else self.SUB)
        self.save_cfg()

    def cycle_alpha(self):
        steps = [1.0, 0.92, 0.8, 0.65, 0.5]
        nxt = [a for a in steps if a < self.alpha - 0.01]
        self.alpha = nxt[0] if nxt else steps[0]
        self.apply_window_attrs()
        self.save_cfg()

    def cfg_changed(self):
        """창을 옮기거나 크기를 바꾸면 잠시 뒤에 위치를 저장한다 (끌기가 끝나기를 기다림)"""
        if not self._ready:
            return
        if self._cfg_job:
            self.win.after_cancel(self._cfg_job)
        self._cfg_job = self.win.after(600, self.save_cfg)

    def save_cfg(self):
        self._cfg_job = None
        if not self.win.winfo_exists():
            return
        x, y = self.win.winfo_x(), self.win.winfo_y()
        if x <= -30000 or y <= -30000:                  # 최소화된 창의 가짜 좌표(-32000)는 저장하지 않는다
            return
        self.cfg.update({"x": x, "y": y, "w": self.win.winfo_width(), "h": self.win.winfo_height(),
                         "topmost": self.topmost, "alpha": round(self.alpha, 2)})
        try:
            core.patch_settings({"widget": dict(self.cfg)})         # 다른 설정은 건드리지 않고 이것만 저장
        except OSError:
            pass

    # ---- 이동·크기 조절 --------------------------------------------------
    def start_move(self, e):
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def do_move(self, e):
        self.win.geometry("+%d+%d" % (e.x_root - self._drag[0], e.y_root - self._drag[1]))

    def start_resize(self, e):
        self._drag = (e.x_root, e.y_root, self.win.winfo_width(), self.win.winfo_height())

    def do_resize(self, e):
        w = max(220, self._drag[2] + e.x_root - self._drag[0])
        h = max(200, self._drag[3] + e.y_root - self._drag[1])
        self.win.geometry("%dx%d" % (w, h))

    def popup(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    # ---- 내용 ------------------------------------------------------------
    def refresh(self):
        app = self.app
        today = dt.date.today()
        self.date_lb.config(text="%d월 %d일 (%s)" % (today.month, today.day, "월화수목금토일"[today.weekday()]))
        team = core.team_for(today, app.settings)
        if team:
            self.team_lb.config(text="%d팀 근무" % team, bg=self.HEAD, fg=team_text(team, dark=True))
        else:
            self.team_lb.config(text="팀 미설정", bg="#777777")
        self.pin_lb.config(fg=self.FG if self.topmost else self.SUB)

        for w in self.body.winfo_children():
            w.destroy()
        self.rows = app.store.upcoming(today, 14)       # 처리 안 된 일정 중 14일 이내(지난 것 포함)
        if not self.rows:
            tk.Label(self.body, text="임박한 일정이 없습니다 🙂", font=(FONT, 10), fg=self.SUB, bg=self.BG).pack(pady=20)
            return
        for ev in self.rows[:30]:
            n = core.dday(ev["date"], today)
            b, f = event_colors(ev, today)
            row = tk.Frame(self.body, bg=b, cursor="hand2")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=core.dday_text(n), font=(FONT, 9, "bold"), fg=f, bg=b, width=6).pack(side="left")
            txt = "%s %s%s" % (ev["date"][5:], (ev["time"] + " ") if ev.get("time") else "", ev_label(ev))
            tk.Label(row, text=txt, font=(FONT, 9), fg=f, bg=b, anchor="w", justify="left",
                     wraplength=max(120, self.win.winfo_width() - 110)).pack(side="left", fill="x", expand=True, padx=2, pady=2)
            for part in [row] + list(row.winfo_children()):
                part.bind("<Button-1>", lambda e, ev=ev: self.open_event(ev))
                for b3 in ("<Button-3>", "<Button-2>"):
                    part.bind(b3, self.popup)

    def tick(self):
        """1분마다 새로 그린다 (자정이 지나면 날짜·근무팀이 바뀐다)."""
        self.refresh()
        self._job = self.win.after(60000, self.tick)

    def open_event(self, ev):
        self.app.show_event(ev)

    def show_main(self):
        self.app.root.deiconify()
        self.app.root.lift()

    def close(self, quit_if_alone=True):
        if self._job:
            self.win.after_cancel(self._job)
        self.save_cfg()
        self.win.destroy()
        self.app.widget_closed("list", quit_if_alone)

    def flash(self, times=8):
        """기한 알림이 오면 머리줄을 몇 번 깜빡인다"""
        if not self.win.winfo_exists():
            return
        color = "#d9480f" if times > 0 and times % 2 else self.HEAD
        for w in [self.head] + [c for c in self.head.winfo_children() if c is not self.team_lb]:
            w.config(bg=color)
        if times > 0:
            self.win.after(450, lambda: self.flash(times - 1))


# ══════════════════════════════════════════════════════════════
#  바탕화면 달력 위젯 (바탕화면에 깔린 큰 월간 달력: 음력 · 절기 · 공휴일 · 주 번호 · 일정)
#    - 위쪽 줄을 끌면 이동, 오른쪽 아래 ◢ 를 끌면 크기 조절, 마우스 휠 = 달 넘기기
#    - 일정 더블클릭 = 공문 열기 / 빈 곳 더블클릭 = 그날 큰 달력 / 우클릭 = 메뉴
#    - '바탕화면에 깔기' 모드: 다른 창들 아래에 있고, 바탕화면 보기(Win+D)를 눌러도 남는다
# ══════════════════════════════════════════════════════════════
class DeskCalendar:
    THEMES = {
        # 칸을 색으로 채우지 않고, 가는 줄과 글자색·점으로만 구분하는 깔끔한 모양
        "dark": dict(bg="#141922", bar="#141922", line="#262e3b", fg="#e8ecf2", sub="#8a93a3", dim="#4a5363",
                     accent="#4c8dff", sun="#ff7676", sat="#74a7ff", hol="#ff7676", term="#5fd08f",
                     today_fg="#ffffff", sel="#2a3547", ev="#d9dee7", done="#5c6574",
                     late="#ff7676", soon="#ffc15e", normal="#4c8dff", btn="#7d8696", btn_hover="#ffffff"),
        "light": dict(bg="#ffffff", bar="#ffffff", line="#e8ebf0", fg="#1f2430", sub="#8a909b", dim="#c4c8cf",
                      accent="#2f6fed", sun="#e5484d", sat="#2f6fed", hol="#e5484d", term="#2e9d5b",
                      today_fg="#ffffff", sel="#eef3ff", ev="#2b303a", done="#b0b5bd",
                      late="#e5484d", soon="#e09100", normal="#2f6fed", btn="#9aa0aa", btn_hover="#1f2430"),
    }
    DAYS = ["일", "월", "화", "수", "목", "금", "토"]
    DROP_HINT = "📥 공문 PDF 를 여기에 끌어다 놓으면 등록돼요"

    def __init__(self, app):
        self.app = app
        self.cfg = app.settings.setdefault("desk_cal", {})
        self.th = self.THEMES.get(self.cfg.get("theme", "dark"), self.THEMES["dark"])
        today = dt.date.today()
        self.year, self.month, self.sel = today.year, today.month, None
        self._fonts, self._job, self._drag, self._day = {}, None, (0, 0), today

        win = self.win = tk.Toplevel(app.root)
        win.overrideredirect(True)
        win.configure(bg=self.th["bg"])
        screen = gs.virtual_screen() or (0, 0, win.winfo_screenwidth(), win.winfo_screenheight())   # 모니터 여러 개면 전체 영역
        x, y, w, h = gs.fit_window(int(self.cfg.get("x", 40)), int(self.cfg.get("y", 60)),
                                   int(self.cfg.get("w", 940)), int(self.cfg.get("h", 660)), screen)
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self._ready, self._cfg_job = False, None
        win.after(800, lambda: setattr(self, "_ready", True))
        win.bind("<Configure>", lambda e: self.cfg_changed() if e.widget is win else None)
        self.alpha = float(self.cfg.get("alpha", 0.9))

        th = self.th
        bar = self.bar = tk.Frame(win, bg=th["bar"])
        bar.pack(fill="x", padx=14, pady=(12, 2))
        self.title_lb = tk.Label(bar, font=(FONT, 20, "bold"), fg=th["fg"], bg=th["bar"])
        self.title_lb.pack(side="left")
        self.year_lb = tk.Label(bar, font=(FONT, 11), fg=th["sub"], bg=th["bar"])
        self.year_lb.pack(side="left", padx=(6, 10), pady=(8, 0))
        self._btn(bar, "‹", lambda: self.move(-1), size=16).pack(side="left")
        self._btn(bar, "›", lambda: self.move(1), size=16).pack(side="left")
        self.today_lb = tk.Label(bar, font=(FONT, 10), fg=th["sub"], bg=th["bar"])
        self.today_lb.pack(side="left", padx=14, pady=(6, 0))
        for text, cmd, tip in (("✕", self.close, "닫기"), ("⚙", self.menu_at_button, "메뉴"),
                               ("▣", app.show_main, "큰 달력"), ("＋", lambda: app.open_add_dialog(), "공문 추가"),
                               ("◐", self.cycle_alpha, "투명도")):
            self._btn(bar, text, cmd).pack(side="right", padx=2)
        for wdg in (bar, self.title_lb, self.year_lb, self.today_lb):
            wdg.bind("<Button-1>", self.start_move)
            wdg.bind("<B1-Motion>", self.do_move)
            wdg.bind("<ButtonRelease-1>", self.end_move)
            wdg.bind("<Double-1>", lambda e: self.go_today())

        self.drop_ok = gs.enable_file_drop(win, app.on_drop)     # 공문 PDF 를 끌어다 놓으면 등록
        self.hover = tk.Label(win, text=self.DROP_HINT, font=(FONT, 9), fg=th["sub"], bg=th["bg"], anchor="w", padx=16)
        self.hover.pack(side="bottom", fill="x", pady=(0, 4))
        self.cv = tk.Canvas(win, bg=th["bg"], highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=8)
        grip = tk.Label(win, text="◢", font=(FONT, 9), fg=th["sub"], bg=th["bg"], cursor="sizing")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<Button-1>", self.start_resize)
        grip.bind("<B1-Motion>", self.do_resize)
        grip.bind("<ButtonRelease-1>", self.end_move)

        cv = self.cv
        cv.bind("<Configure>", lambda e: self.schedule_redraw())
        cv.bind("<Motion>", self.on_motion)
        cv.bind("<Leave>", lambda e: self.hover.config(text=self.DROP_HINT))
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", self.on_release)
        cv.bind("<Double-1>", self.on_double)
        for b3 in ("<Button-3>", "<Button-2>"):
            cv.bind(b3, self.on_right)
        cv.bind("<MouseWheel>", lambda e: self.move(-1 if e.delta > 0 else 1))
        cv.bind("<Button-4>", lambda e: self.move(-1))
        cv.bind("<Button-5>", lambda e: self.move(1))

        self.menu = tk.Menu(win, tearoff=0)
        self.apply_mode()
        self.redraw()
        self._job = win.after(60000, self.tick)

    # ---- 작은 글자 버튼 --------------------------------------------------
    def _btn(self, parent, text, cmd, size=11):
        th = self.th
        lb = tk.Label(parent, text=text, font=(FONT, size), fg=th["btn"], bg=th["bar"], cursor="hand2", padx=5)
        lb.bind("<Button-1>", lambda e: cmd())
        lb.bind("<Enter>", lambda e: lb.config(fg=th["btn_hover"]))
        lb.bind("<Leave>", lambda e: lb.config(fg=th["btn"]))
        return lb

    # ---- 창 모드 (바탕화면에 깔기 / 일반 / 항상 위) ------------------------------
    def apply_mode(self):
        mode = self.cfg.get("mode", "desktop")
        try:
            self.win.attributes("-alpha", self.alpha)
            self.win.attributes("-topmost", mode == "top")
        except tk.TclError:
            pass
        if mode == "desktop":
            self.pinned = gs.pin_to_desktop(self.win)
            for ev in ("<FocusIn>", "<ButtonRelease-1>"):
                self.win.bind(ev, lambda e: self.win.after(30, self.to_bottom), add="+")
        else:
            self.pinned = False
            gs.unpin_from_desktop(self.win)

    def to_bottom(self):
        if self.cfg.get("mode", "desktop") == "desktop" and self.win.winfo_exists():
            gs.send_to_bottom(self.win)

    def cycle_alpha(self):
        steps = [1.0, 0.9, 0.8, 0.7, 0.6]
        nxt = [a for a in steps if a < self.alpha - 0.01]
        self.alpha = nxt[0] if nxt else steps[0]
        self.apply_mode()
        self.save_cfg()

    def cfg_changed(self):
        """창을 옮기거나 크기를 바꾸면 잠시 뒤에 위치를 저장한다 (끌기가 끝나기를 기다림)"""
        if not self._ready:
            return
        if self._cfg_job:
            self.win.after_cancel(self._cfg_job)
        self._cfg_job = self.win.after(600, self.save_cfg)

    def save_cfg(self):
        self._cfg_job = None
        if not self.win.winfo_exists():
            return
        x, y = self.win.winfo_x(), self.win.winfo_y()
        if x <= -30000 or y <= -30000:                  # 최소화된 창의 가짜 좌표(-32000)는 저장하지 않는다
            return
        self.cfg.update({"x": x, "y": y, "w": self.win.winfo_width(), "h": self.win.winfo_height(),
                         "alpha": round(self.alpha, 2)})
        try:
            core.patch_settings({"desk_cal": dict(self.cfg)})        # 다른 설정은 건드리지 않고 이것만 저장
        except OSError:
            pass

    # ---- 이동·크기 ------------------------------------------------------------
    def start_move(self, e):
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def do_move(self, e):
        self.win.geometry("+%d+%d" % (e.x_root - self._drag[0], e.y_root - self._drag[1]))

    def start_resize(self, e):
        self._drag = (e.x_root, e.y_root, self.win.winfo_width(), self.win.winfo_height())

    def do_resize(self, e):
        w = max(480, self._drag[2] + e.x_root - self._drag[0])
        h = max(340, self._drag[3] + e.y_root - self._drag[1])
        self.win.geometry("%dx%d" % (w, h))

    def end_move(self, _e=None):
        self.save_cfg()
        self.to_bottom()

    # ---- 달 이동 --------------------------------------------------------------
    def move(self, delta):
        m = self.month + delta
        self.year += (m - 1) // 12
        self.month = (m - 1) % 12 + 1
        self.redraw()

    def go_today(self):
        t = dt.date.today()
        self.year, self.month = t.year, t.month
        self.redraw()

    def tick(self):
        """1분마다: 날짜가 바뀌었으면 다시 그린다"""
        if dt.date.today() != self._day:
            self._day = dt.date.today()
            self.redraw()
        self._job = self.win.after(60000, self.tick)

    def refresh(self):
        self.redraw()

    def schedule_redraw(self):
        if getattr(self, "_redraw_job", None):
            self.win.after_cancel(self._redraw_job)
        self._redraw_job = self.win.after(60, self.redraw)

    # ---- 그리기 ---------------------------------------------------------------
    def font(self, size, bold=False, strike=False):
        key = (size, bold, strike)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(family=FONT, size=size, weight="bold" if bold else "normal",
                                           overstrike=1 if strike else 0)
        return self._fonts[key]

    @staticmethod
    def elide(text, font, maxw):
        """칸 너비에 맞게 글자를 자르고 … 를 붙인다"""
        if font.measure(text) <= maxw:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= maxw:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + "…"

    def redraw(self):
        self._redraw_job = None
        if not self.win.winfo_exists():
            return
        cv, th, cfg = self.cv, self.th, self.cfg
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 100 or H < 100:
            return
        cv.delete("all")
        today = dt.date.today()
        s = self.app.settings
        y, m = self.year, self.month
        self.title_lb.config(text="%d월" % m)
        self.year_lb.config(text=str(y))
        team = core.team_for(today, s)
        bits = ["오늘 %d. %d.(%s)" % (today.month, today.day, "월화수목금토일"[today.weekday()])]
        if cfg.get("lunar", False):
            bits.append("음력 " + kcal.day_info(today)["lunar"])
        if team:
            bits.append("근무 %d팀" % team)
        self.today_lb.config(text="  ·  ".join(bits))

        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(y, m)
        show_wk, show_lunar = cfg.get("weeknum", False), cfg.get("lunar", False)
        left, top = (26 if show_wk else 0), 28
        cw, ch = (W - left) / 7, (H - top) / len(weeks)
        size = 10 if ch >= 90 and cw >= 110 else 9
        f_num, f_num_b = self.font(size + 2), self.font(size + 2, True)
        f_small, f_head = self.font(size - 1), self.font(size - 1, True)
        f_ev, f_ev_done = self.font(size), self.font(size, strike=True)
        line_h = f_ev.metrics("linespace") + 3
        num_h = f_num.metrics("linespace")

        for c, name in enumerate(self.DAYS):            # 요일 (상자 없이 글자만)
            color = th["sun"] if c == 0 else (th["sat"] if c == 6 else th["sub"])
            cv.create_text(left + c * cw + 12, top / 2, text=name, fill=color, font=f_head, anchor="w")
        cv.create_line(0, top - 1, W, top - 1, fill=th["line"])

        by_date = self.app.store.group_by_date()
        for r, week in enumerate(weeks):
            y0 = top + r * ch
            if r:
                cv.create_line(left, y0, W, y0, fill=th["line"])    # 주 사이에 가는 줄 하나
            if show_wk:
                cv.create_text(left / 2, y0 + 8 + num_h / 2, text=str(week[1].isocalendar()[1]), fill=th["dim"],
                               font=f_small)
            for c, d in enumerate(week):
                x0 = left + c * cw
                iso = d.isoformat()
                tag = ("day:" + iso,)
                in_m = d.month == m
                info = kcal.day_info(d, show_lunar)
                hol = info["holiday"]
                # 마우스를 받기 위한 칸 (배경과 같은 색)
                cv.create_rectangle(x0, y0 + 1, x0 + cw, y0 + ch, fill=th["bg"], outline="", tags=tag)
                if d == self.sel and d != today:
                    self.rrect(x0 + 3, y0 + 4, x0 + cw - 3, y0 + ch - 3, 8, fill=th["sel"], outline="", tags=tag)

                nx, ny = x0 + 10, y0 + 8
                if d == today:                          # 오늘: 날짜 뒤에 동그라미
                    rr = num_h / 2 + 3
                    cx = nx + f_num_b.measure(str(d.day)) / 2
                    cv.create_oval(cx - rr, ny + num_h / 2 - rr, cx + rr, ny + num_h / 2 + rr, fill=th["accent"],
                                   outline="", tags=tag)
                    numc, fnt = th["today_fg"], f_num_b
                else:
                    numc = (th["hol"] if c == 0 or hol else th["sat"] if c == 6 else th["fg"]) if in_m else th["dim"]
                    fnt = f_num
                cv.create_text(nx, ny, text=str(d.day), anchor="nw", font=fnt, fill=numc, tags=tag)
                lx = nx + f_num_b.measure(str(d.day)) + 8
                label, lc = ((hol, th["hol"]) if hol else (info["term"], th["term"]) if info["term"]
                             else (info["lunar"], th["sub"]) if info["lunar"] else ("", th["sub"]))
                tm = core.team_for(d, s)
                team_w = f_small.measure("3팀") + 12 if tm else 0
                if label:
                    cv.create_text(lx, ny + 2, text=self.elide(label, f_small, x0 + cw - lx - team_w - 4), anchor="nw",
                                   font=f_small, fill=lc if in_m else th["dim"], tags=tag)
                if tm and in_m:                         # 근무팀: 글자 색만 (내 팀은 굵게)
                    mine = tm == s.get("my_team")
                    cv.create_text(x0 + cw - 10, ny + 2, text="%d팀" % tm, anchor="ne", font=f_head if mine else f_small,
                                   fill=team_text(tm, dark=cfg.get("theme", "dark") == "dark"), tags=tag)

                evs = by_date.get(iso, [])
                ey = ny + num_h + 8
                room = max(0, int((y0 + ch - 4 - ey) // line_h))
                show = evs if len(evs) <= room else evs[:max(0, room - 1)]
                for ev in show:                         # 일정: 색 점 + 글자
                    n = core.dday(ev["date"], today)
                    if ev.get("done"):
                        dot = th["done"]
                    elif ev.get("color") in EVENT_COLORS:
                        dot = DARK_TEXT[ev["color"]] if cfg.get("theme", "dark") == "dark" else EVENT_COLORS[ev["color"]][1]
                    else:
                        dot = th["late"] if n <= 0 else th["soon"] if n <= 3 else th["normal"]
                    etag = tag + ("ev:" + ev["id"],)
                    cy = ey + line_h / 2 - 1
                    cv.create_oval(x0 + 11, cy - 3, x0 + 17, cy + 3, fill=dot if in_m else th["dim"], outline="", tags=etag)
                    text = ((ev["time"] + " ") if ev.get("time") else "") + ev_label(ev)
                    fnt = f_ev_done if ev.get("done") else f_ev
                    color = th["done"] if ev.get("done") else (th["ev"] if in_m else th["dim"])
                    cv.create_text(x0 + 22, ey, text=self.elide(text, fnt, cw - 30), anchor="nw", font=fnt,
                                   fill=color, tags=etag)
                    ey += line_h
                if len(evs) > len(show):
                    cv.create_text(x0 + 22, ey, text="+%d" % (len(evs) - len(show)), anchor="nw",
                                   font=f_small, fill=th["sub"], tags=tag)

    def rrect(self, x0, y0, x1, y1, r, **kw):
        """둥근 모서리 사각형"""
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
               x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    # ---- 마우스 --------------------------------------------------------------
    def _hit(self):
        """마우스 아래: (날짜, 일정 또는 None)"""
        d = ev = None
        for t in self.cv.gettags("current"):
            if t.startswith("day:"):
                d = dt.date.fromisoformat(t[4:])
            elif t.startswith("ev:"):
                ev = self.app.store.get(t[3:])
        return d, ev

    def on_motion(self, _e):
        d, ev = self._hit()
        if ev:
            n = core.dday(ev["date"], dt.date.today())
            state = "완료" if ev.get("done") else core.dday_text(n)
            self.hover.config(text="%s · %s %s · %s   (끌기 = 옮기기, Ctrl+끌기 = 복사, 더블클릭 = 설정·완료)" % (
                state, ev["date"][5:], ev.get("kind", ""), ev_label(ev)))
        elif d:
            info = kcal.day_info(d, self.cfg.get("lunar", False))
            extra = " · ".join(x for x in (info["holiday"], info["term"], ("음력 " + info["lunar"]) if info["lunar"] else "") if x)
            self.hover.config(text="%d월 %d일 %s   (더블클릭 = 메모 추가)" % (d.month, d.day, extra))
        else:
            self.hover.config(text=self.DROP_HINT)

    def day_at(self, x_root, y_root):
        """화면 좌표 아래의 날짜"""
        x, y = x_root - self.cv.winfo_rootx(), y_root - self.cv.winfo_rooty()
        for item in reversed(self.cv.find_overlapping(x, y, x, y)):
            for t in self.cv.gettags(item):
                if t.startswith("day:"):
                    return dt.date.fromisoformat(t[4:])
        return None

    def on_press(self, e):
        d, ev = self._hit()
        self._press = {"d": d, "ev": ev, "x": e.x_root, "y": e.y_root, "ghost": None}

    def on_drag(self, e):
        pr = getattr(self, "_press", None)
        if not pr or not pr["ev"]:
            return
        if pr["ghost"] is None:
            if abs(e.x_root - pr["x"]) + abs(e.y_root - pr["y"]) < 8:
                return
            pr["ghost"] = DragGhost(self.app.root, ev_label(pr["ev"]))
        pr["ghost"].show(e.x_root, e.y_root, ctrl_down(e), self.day_at(e.x_root, e.y_root))

    def on_release(self, e):
        pr, self._press = getattr(self, "_press", None), None
        if not pr:
            return
        if pr["ghost"] is not None:                     # 끌어서 놓음 = 옮기기 (Ctrl = 복사)
            pr["ghost"].close()
            target = self.day_at(e.x_root, e.y_root)
            if target:
                self.app.move_event(pr["ev"], target, copy=ctrl_down(e))
            return
        if pr["d"]:                                     # 그냥 클릭 = 날짜 선택
            self.sel = pr["d"]
            self.redraw()

    def on_double(self, _e):
        d, ev = self._hit()
        if ev:
            EventDialog(self.app, ev)                   # 일정 더블클릭 = 설정 (글자·색·완료)
        elif d:
            EventDialog(self.app, day=d)                # 날짜 더블클릭 = 메모 추가

    def on_right(self, e):
        d, ev = self._hit()
        if ev:
            self.app.popup_menu(e.x_root, e.y_root, ev)
            return
        self.show_menu(e.x_root, e.y_root, d)

    def menu_at_button(self):
        self.show_menu(self.win.winfo_rootx() + self.win.winfo_width() - 180, self.win.winfo_rooty() + 30, None)

    def show_menu(self, x, y, d):
        m = self.menu
        m.delete(0, "end")
        if d:
            m.add_command(label="📅 %d월 %d일 큰 달력에서 보기" % (d.month, d.day),
                          command=lambda: (self.app.show_main(), self.app.go_to(d)))
        m.add_command(label="＋ 공문 추가", command=lambda: self.app.open_add_dialog())
        m.add_command(label="오늘로", command=self.go_today)
        m.add_separator()
        mode = self.cfg.get("mode", "desktop")
        for key, label in (("desktop", "바탕화면에 깔기 (다른 창 아래)"), ("normal", "일반 창"), ("top", "항상 위")):
            m.add_command(label=("● " if mode == key else "○ ") + label, command=lambda k=key: self.set_cfg("mode", k))
        m.add_command(label=("☑ " if self.cfg.get("lunar", False) else "☐ ") + "음력 표시",
                      command=lambda: self.set_cfg("lunar", not self.cfg.get("lunar", False)))
        m.add_command(label=("☑ " if self.cfg.get("weeknum", False) else "☐ ") + "주 번호 표시",
                      command=lambda: self.set_cfg("weeknum", not self.cfg.get("weeknum", False)))
        m.add_command(label="밝은 테마" if self.cfg.get("theme", "dark") == "dark" else "어두운 테마",
                      command=lambda: self.set_cfg("theme", "light" if self.cfg.get("theme", "dark") == "dark" else "dark"))
        m.add_separator()
        m.add_command(label="위젯 설정…", command=lambda: self.app.open_settings("widget"))
        m.add_command(label="✕ 달력 위젯 닫기", command=self.close)
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def set_cfg(self, key, value):
        self.cfg[key] = value
        core.save_settings(self.app.settings)
        if key == "theme":                              # 색이 바뀌면 창을 새로 만든다
            self.app.reopen_widget("desk")
            return
        if key == "mode":
            self.apply_mode()
        self.redraw()

    def flash(self, times=8):
        if not self.win.winfo_exists():
            return
        color = "#d9480f" if times > 0 and times % 2 else self.th["bar"]
        for w in [self.bar] + list(self.bar.winfo_children()):
            w.config(bg=color)
        if times > 0:
            self.win.after(450, lambda: self.flash(times - 1))

    def close(self, quit_if_alone=True):
        if self._job:
            self.win.after_cancel(self._job)
        self.save_cfg()
        self.win.destroy()
        self.app.widget_closed("desk", quit_if_alone)


# ══════════════════════════════════════════════════════════════
#  메인 창 (달력)
# ══════════════════════════════════════════════════════════════
def hbtn(parent, text, cmd, bg, fg="#ffffff", hover=None, font=None, padx=8):
    """머리줄에 쓰는 납작한 글자 버튼"""
    lb = tk.Label(parent, text=text, bg=bg, fg=fg, font=font or (FONT, 11), padx=padx, pady=2, cursor="hand2")
    lb.bind("<Button-1>", lambda e: cmd())
    lb.bind("<Enter>", lambda e: lb.config(bg=hover or bg))
    lb.bind("<Leave>", lambda e: lb.config(bg=bg))
    return lb


class App:
    SEARCH_HINT = "제목 · 문서번호 검색"

    def __init__(self, widget_only=False):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self._icon = None
        try:                                            # 창 아이콘
            self._icon = tk.PhotoImage(file=resource_path("icon.png"))
            self.root.iconphoto(True, self._icon)
            if sys.platform == "win32":
                self.root.iconbitmap(default=resource_path("icon.ico"))
        except (tk.TclError, OSError):
            pass
        self._body_cache = {}
        self.root.geometry("1240x780")
        self.root.minsize(1000, 640)
        setup_style(self.root)
        self.settings = core.load_settings()
        set_team_theme(self.settings.get("team_theme"))
        self.share_ok = core.set_shared_dir(self.settings.get("shared_dir", "")) or not self.settings.get("shared_dir")
        self.store = core.Store(core.shared_path("공문일정.json"))
        self.lex = core.load_lexicon(core.data_path("용어사전.txt"))
        self.today = dt.date.today()
        self.year, self.month = self.today.year, self.today.month
        self.selected = self.today
        self.day_events = []                            # 오른쪽 목록에 보이는 일정들
        self.soon_events = []
        self.rel_items = []
        self.status_win = self.ach_win = self.search_win = self.widget = self.deskcal = None
        self._grid_key = None                           # 달력을 마지막으로 그린 조건 (같으면 다시 안 그린다)
        self._cells = {}
        self._srev = 0                                  # 설정이 바뀔 때마다 1씩 오른다
        self._click_job = None                          # 단일 클릭/더블 클릭을 구분하기 위한 예약
        self.pending_select_id = None                   # 클릭한 일정을 오른쪽 목록에서 선택해 두기 위함
        self.watcher = None
        self.tray, self.tray_ok, self._tray_hint_shown = None, False, False
        self._main_visible = not widget_only
        self._tick = 0
        self.title_var, self.sel_var, self.team_var = tk.StringVar(), tk.StringVar(), tk.StringVar()

        self.menu = tk.Menu(self.root, tearoff=0)       # 우클릭 메뉴
        self.build_header()
        self.build_toolbar()
        self.build_statusbar()
        self.build_body()
        self.refresh()
        author_credit.add_author_credit(self.root, app_name=APP_NAME, bg=STATUS_BG)
        gs.enable_file_drop(self.root, self.on_drop)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_main)
        self.root.bind("<Map>", lambda e: setattr(self, "_main_visible", True) if e.widget is self.root else None)
        self.root.bind("<Unmap>", lambda e: setattr(self, "_main_visible", False) if e.widget is self.root else None)
        self.root.bind("<Control-n>", lambda e: self.open_add_dialog())
        self.root.bind("<Control-f>", lambda e: self.focus_search())
        self.root.bind("<Left>", lambda e: self.move_month(-1) if e.widget is self.root else None)
        self.root.bind("<Right>", lambda e: self.move_month(1) if e.widget is self.root else None)

        self.apply_settings(first=True)
        self.start_tray()
        self.root.after(2500, self.check_alerts)        # 켜자마자 기한 알림 확인
        self.root.after(3000, self.background_tick)
        if widget_only:                                 # 위젯만 띄우기: 큰 달력 창은 숨겨 둔다
            self.root.withdraw()
            self.open_widget()
            if self.widget is None and self.deskcal is None:
                self.open_widget("desk")

    # ---- 화면 만들기 -----------------------------------------------------
    def build_header(self):
        head = tk.Frame(self.root, bg=PRIMARY_DARK)
        head.pack(fill="x")
        if self._icon is not None:
            self._icon_small = self._icon.subsample(8)  # 256 -> 32px
            tk.Label(head, image=self._icon_small, bg=PRIMARY_DARK).pack(side="left", padx=(14, 0), pady=6)
        tk.Label(head, text=APP_NAME, font=(FONT, 15, "bold"), fg="#ffffff", bg=PRIMARY_DARK).pack(side="left", padx=(8, 2), pady=9)
        tk.Label(head, text="공문 · 일정 관리", font=(FONT, 9), fg="#bcd0ff", bg=PRIMARY_DARK).pack(side="left", padx=(0, 22), pady=(14, 9))

        nav = tk.Frame(head, bg=PRIMARY_DARK)
        nav.pack(side="left")
        hbtn(nav, "◀", lambda: self.move_month(-1), PRIMARY_DARK, hover=PRIMARY).pack(side="left")
        tk.Label(nav, textvariable=self.title_var, font=(FONT, 15, "bold"), fg="#ffffff", bg=PRIMARY_DARK,
                 width=10).pack(side="left")
        hbtn(nav, "▶", lambda: self.move_month(1), PRIMARY_DARK, hover=PRIMARY).pack(side="left")
        hbtn(nav, "오늘", lambda: self.go_to(dt.date.today()), "#3b6fe6", hover=PRIMARY, font=(FONT, 10, "bold"),
             padx=12).pack(side="left", padx=(10, 0))
        self.team_label = tk.Label(head, textvariable=self.team_var, font=(FONT, 10, "bold"), fg="#ffffff", bg="#999999",
                                   padx=10, pady=3, cursor="hand2")
        self.team_label.pack(side="left", padx=18)
        self.team_label.bind("<Button-1>", lambda e: self.open_settings("team"))

        box = tk.Frame(head, bg="#ffffff")
        box.pack(side="right", padx=16, pady=8)
        tk.Label(box, text="🔍", bg="#ffffff", fg=SUB, font=(FONT, 10)).pack(side="left", padx=(8, 0))
        self.search_entry = tk.Entry(box, font=(FONT, 10), relief="flat", width=26, fg=SUB, bg="#ffffff")
        self.search_entry.pack(side="left", padx=6, pady=4)
        self.search_entry.insert(0, self.SEARCH_HINT)
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)
        self.search_entry.bind("<Return>", lambda e: self.open_search(self.search_entry.get()))

    def _search_focus_in(self, _e):
        if self.search_entry.get() == self.SEARCH_HINT:
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=TEXT)

    def _search_focus_out(self, _e):
        if not self.search_entry.get().strip():
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, self.SEARCH_HINT)
            self.search_entry.config(fg=SUB)

    def focus_search(self):
        self.search_entry.focus_set()

    def build_toolbar(self):
        bar = tk.Frame(self.root, bg=CARD)
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=CARD)
        inner.pack(fill="x", padx=12, pady=8)

        def sep():
            tk.Frame(inner, bg=BORDER, width=1).pack(side="left", fill="y", padx=10, pady=2)

        ttk.Button(inner, text="＋ 공문 추가", style="Accent.TButton", command=self.open_add_dialog).pack(side="left")
        ttk.Button(inner, text="📂 여러 개 한꺼번에", command=self.open_batch).pack(side="left", padx=(6, 0))
        sep()
        ttk.Button(inner, text="📋 업무 현황", command=self.open_status).pack(side="left")
        ttk.Button(inner, text="★ 내 실적", command=self.open_achievements).pack(side="left", padx=6)

        ttk.Button(inner, text="⚙ 설정", command=lambda: self.open_settings()).pack(side="right")
        mb = ttk.Menubutton(inner, text="📤 내보내기")
        m = tk.Menu(mb, tearoff=0)
        m.add_command(label="📊 엑셀(.xlsx) - 업무 처리 현황", command=self.export_xlsx)
        m.add_command(label="📅 캘린더(.ics) - 구글·아웃룩", command=self.export_ics)
        mb["menu"] = m
        mb.pack(side="right", padx=6)
        wb = ttk.Menubutton(inner, text="🧩 위젯")
        wm = tk.Menu(wb, tearoff=0)
        wm.add_command(label="📅 달력 위젯 (바탕화면 큰 달력)", command=lambda: self.open_widget("desk"))
        wm.add_command(label="📋 목록 위젯 (오늘 근무 · 임박 기한)", command=lambda: self.open_widget("list"))
        wm.add_separator()
        wm.add_command(label="위젯 고르기 · 설정…", command=lambda: self.open_settings("widget"))
        wb["menu"] = wm
        wb.pack(side="right")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    def build_statusbar(self):
        bar = tk.Frame(self.root, bg=STATUS_BG, height=26)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        self.status_items = {}
        for key, tab in (("store", "share"), ("dl", "auto"), ("alert", "alert")):
            lb = tk.Label(bar, text="", bg=STATUS_BG, fg=SUB, font=(FONT, 9), cursor="hand2", padx=8)
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, t=tab: self.open_settings(t))
            lb.bind("<Enter>", lambda e, w=lb: w.config(fg=PRIMARY_DARK))
            lb.bind("<Leave>", lambda e, w=lb: w.config(fg=SUB))
            self.status_items[key] = lb
        self.tip_lb = tk.Label(bar, text="일정 클릭 = 공문 내용 · 끌기 = 옮기기(Ctrl = 복사) · 더블클릭 = 설정·완료 · 날짜 더블클릭 = 메모",
                               bg=STATUS_BG, fg="#9aa0aa", font=(FONT, 9))
        self.tip_lb.pack(side="right", padx=(0, 110))

    def update_statusbar(self):
        s = self.settings
        if s.get("shared_dir") and not self.share_ok:
            store = "⚠ 공유 폴더 연결 안 됨 → 내 PC 에 저장 중"
        elif core._SHARED_DIR:
            store = "👥 공유 폴더: " + os.path.basename(core._SHARED_DIR.rstrip("\\/"))
        else:
            store = "💾 내 PC 에 저장"
        self.status_items["store"].config(text=store)
        self.status_items["dl"].config(text="📥 다운로드 감시 " + ("켜짐" if self.watcher else "꺼짐"))
        self.status_items["alert"].config(text="⏰ 기한 알림 " + ("켜짐" if s.get("alerts_on", True) else "꺼짐"))

    def build_body(self):
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        side = ttk.Frame(body, width=430)               # 오른쪽 패널을 먼저 놓아야 달력이 남은 자리를 채운다
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)
        card = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(side="left", fill="both", expand=True)
        self.cal_frame = tk.Frame(card, bg=CARD)
        self.cal_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.nb = ttk.Notebook(side)
        self.nb.pack(fill="both", expand=True)

        # [선택한 날] 탭: 그날 일정 목록 → 처리/미처리 → 공문 내용(크게) → 관련 공문(작게)
        t1 = ttk.Frame(self.nb, padding=10)
        self.nb.add(t1, text=" 📌 선택한 날 ")
        ttk.Label(t1, textvariable=self.sel_var, style="Head.TLabel").pack(anchor="w")
        self.day_list = listbox(t1, height=4)
        self.day_list.pack(fill="x", pady=(6, 6))
        self.day_list.bind("<<ListboxSelect>>", lambda e: self.show_detail())
        self.day_list.bind("<Double-1>", lambda e: self.edit_current())
        for b in ("<Button-3>", "<Button-2>"):          # 우클릭 (윈도우=Button-3, 맥=Button-2)
            self.day_list.bind(b, self.popup_from_list)

        row = ttk.Frame(t1)
        row.pack(fill="x", pady=(0, 6))
        self.state_var = tk.StringVar(value="")
        self.seg = []
        for val, text in (("미처리", "⏳ 미처리"), ("처리", "✔ 처리완료")):
            b = ttk.Radiobutton(row, text=text, value=val, variable=self.state_var, style="Seg.Toolbutton",
                                command=self.on_state_change)
            b.pack(side="left", padx=(0, 2))
            self.seg.append(b)
        ttk.Button(row, text="🗑", width=3, style="Danger.TButton", command=self.delete_event).pack(side="right")
        ttk.Button(row, text="📄 원본", command=self.open_source).pack(side="right", padx=4)
        ttk.Button(row, text="⚙ 설정", command=self.edit_current).pack(side="right")

        ttk.Label(t1, text="📄 공문 내용", font=(FONT, 9, "bold")).pack(anchor="w")
        box = ttk.Frame(t1)
        box.pack(fill="both", expand=True, pady=(2, 6))
        self.detail = tk.Text(box, wrap="word", font=(FONT, 10), state="disabled", bg="#fbfcfe", relief="flat",
                              highlightthickness=1, highlightbackground=BORDER, padx=10, pady=8, spacing1=1, spacing3=2)
        sb = ttk.Scrollbar(box, orient="vertical", command=self.detail.yview)
        self.detail.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.detail.pack(side="left", fill="both", expand=True)
        self.detail.tag_configure("h", font=(FONT, 12, "bold"), spacing3=6)
        self.detail.tag_configure("meta", foreground="#4b5563", font=(FONT, 9))
        self.detail.tag_configure("memo", foreground="#5b3a9c", font=(FONT, 10), lmargin1=6, lmargin2=6)
        self.detail.tag_configure("sep", foreground="#9aa0aa", font=(FONT, 9), spacing1=8, spacing3=6)
        self.detail.tag_configure("body", font=(FONT, 10))
        self.detail.tag_configure("mark", background="#fff1a8")
        self.detail.tag_configure("hint", foreground="#9aa0aa")

        ttk.Label(t1, text="🔗 관련 공문 (더블클릭 = 이동)", font=(FONT, 8, "bold")).pack(anchor="w")
        self.rel_list = listbox(t1, height=2, font=(FONT, 8))
        self.rel_list.pack(fill="x")
        self.rel_list.bind("<Double-1>", self.on_rel_double)

        # [임박한 기한] 탭
        t2 = ttk.Frame(self.nb, padding=10)
        self.nb.add(t2, text=" ⏰ 임박한 기한 ")
        ttk.Label(t2, text="처리 안 한 일정 · 14일 이내 (지난 것 포함)", style="Sub.TLabel").pack(anchor="w")
        self.soon_list = listbox(t2, font=(FONT, 10))
        self.soon_list.pack(fill="both", expand=True, pady=6)
        self.soon_list.bind("<<ListboxSelect>>", self.jump_to_soon)

    # ---- 달력 그리기 -----------------------------------------------------
    def refresh(self):
        """화면 새로 고침. 달·일정·설정이 그대로면 달력은 다시 그리지 않고 선택 표시만 옮긴다 (빠름)."""
        self.today = dt.date.today()
        key = (self.year, self.month, self.store.version, self.today, self._srev)
        if key == self._grid_key:
            self._mark_selected()
            self.refresh_side()
            return
        self._grid_key = key
        self.title_var.set("%d년 %d월" % (self.year, self.month))
        self.update_team_label()
        for w in self.cal_frame.winfo_children():
            w.destroy()
        self._cells = {}

        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(self.year, self.month)   # 일요일 시작
        self.store.ensure_window(weeks[0][0], weeks[-1][-1])
        by_date = self.store.group_by_date()
        for c in range(7):
            self.cal_frame.columnconfigure(c, weight=1, uniform="day")
        for i, name in enumerate(["일", "월", "화", "수", "목", "금", "토"]):
            color = "#c0392b" if i == 0 else ("#2f6fed" if i == 6 else "#4b5563")
            tk.Label(self.cal_frame, text=name, font=(FONT, 10, "bold"), fg=color, bg=CARD).grid(row=0, column=i, pady=(2, 4))
        self.cal_frame.rowconfigure(0, weight=0)
        for r in range(1, 7):
            self.cal_frame.rowconfigure(r, weight=0, uniform="")
        for r, week in enumerate(weeks, start=1):
            self.cal_frame.rowconfigure(r, weight=1, uniform="week")
            for c, day in enumerate(week):
                self.draw_day(day, r, c, by_date.get(day.isoformat(), []))

        self.refresh_side()
        for w in (self.status_win, self.ach_win, self.search_win, self.widget, self.deskcal):   # 열려 있는 창도 같이 갱신
            if w is not None:
                w.refresh()
        self.update_statusbar()

    def _mark_selected(self):
        for d, cell in self._cells.items():
            sel = d == self.selected
            cell.config(highlightthickness=2 if sel else 1, highlightbackground=PRIMARY if sel else "#e3e7ee")

    def update_team_label(self):
        if self.tray_ok:
            self.tray.set_tooltip(self.tray_tooltip())
        team = core.team_for(self.today, self.settings)
        if team:
            self.team_var.set("오늘 근무 %d팀" % team)
            self.team_label.config(bg=PRIMARY_DARK, fg=team_text(team, dark=True))
        else:
            self.team_var.set("근무팀 설정하기 ›")
            self.team_label.config(bg="#5b7bd6")

    def draw_day(self, day, row, col, events):
        in_month = day.month == self.month
        is_sel = day == self.selected
        is_today = day == self.today
        bg = "#eef4ff" if is_today else (CARD if in_month else "#f6f7f9")

        cell = tk.Frame(self.cal_frame, bg=bg, highlightthickness=2 if is_sel else 1,
                        highlightbackground=PRIMARY if is_sel else "#e3e7ee")
        cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
        self._cells[day] = cell

        head = tk.Frame(cell, bg=bg)                    # 맨 윗줄: 날짜 · 공휴일/절기(왼쪽) + 근무팀(오른쪽)
        head.pack(fill="x", pady=(2, 0))
        info = kcal.day_info(day, lunar=False)
        hol = info["holiday"]
        fg = "#b8bcc4" if not in_month else ("#c0392b" if col == 0 or hol else ("#2f6fed" if col == 6 else "#1f2430"))
        if is_today:
            num = tk.Label(head, text=" %d " % day.day, font=(FONT, 9, "bold"), fg="#ffffff", bg=PRIMARY)
        else:
            num = tk.Label(head, text=str(day.day), font=(FONT, 9, "bold"), fg=fg, bg=bg, anchor="w")
        num.pack(side="left", padx=4)
        widgets = [cell, head, num]
        if hol or info["term"]:
            hl = tk.Label(head, text=hol or info["term"], font=(FONT, 8), bg=bg,
                          fg=("#c0392b" if hol else "#2e9d5b") if in_month else "#b8bcc4")
            hl.pack(side="left")
            widgets.append(hl)

        team = core.team_for(day, self.settings)
        if team:
            mine = team == self.settings.get("my_team")
            tl = tk.Label(head, text="%d팀" % team, font=(FONT, 9 if mine else 8, "bold" if mine else "normal"),
                          fg=team_text(team) if in_month else "#b8bcc4", bg=bg)
            tl.pack(side="right", padx=4)
            widgets.append(tl)

        for ev in events[:3]:                           # 칸에는 최대 3개까지만 보여 준다
            b, f = event_colors(ev, self.today)
            mark = ("✔ " if ev.get("done") else "") + ("★ " if ev.get("mine") else "")
            t = (ev["time"] + " " if ev.get("time") else "") + ev_label(ev)
            font = (FONT, 8, "overstrike") if ev.get("done") else (FONT, 8)      # 완료되면 가운데 줄
            lb = tk.Label(cell, text=mark + t, font=font, bg=b, fg=f, anchor="w", padx=3, cursor="hand2")
            lb.pack(fill="x", padx=3, pady=1)
            lb.bind("<ButtonPress-1>", lambda e, d=day, ev=ev: self.drag_press(e, d, ev))      # 한 번 클릭 = 선택 / 끌면 옮기기
            lb.bind("<B1-Motion>", self.drag_motion)
            lb.bind("<ButtonRelease-1>", self.drag_release)
            lb.bind("<Double-1>", lambda e, ev=ev: self.on_event_double(ev))                  # 더블클릭 = 설정·완료
            for b3 in ("<Button-3>", "<Button-2>"):                                           # 우클릭 = 메뉴
                lb.bind(b3, lambda e, ev=ev: self.popup_menu(e.x_root, e.y_root, ev))
        if len(events) > 3:
            more = tk.Label(cell, text="+%d건 더" % (len(events) - 3), font=(FONT, 8), fg=SUB, bg=bg, anchor="w")
            more.pack(fill="x", padx=4)
            widgets.append(more)
        for w in widgets:                               # 빈 곳: 한 번 = 그날 선택, 두 번 = 메모 추가
            w.bind("<Button-1>", lambda e, d=day: self.select(d))
            w.bind("<Double-1>", lambda e, d=day: EventDialog(self, day=d))

    # ---- 오른쪽 패널 -----------------------------------------------------
    def refresh_side(self):
        d = self.selected
        team = core.team_for(d, self.settings)
        self.sel_var.set("%d월 %d일 (%s)%s" % (d.month, d.day, "월화수목금토일"[d.weekday()],
                                               ("  · 근무 %d팀" % team) if team else ""))
        self.day_events = self.store.group_by_date().get(d.isoformat(), [])
        self.day_list.delete(0, "end")
        for ev in self.day_events:
            mark = ("✔ " if ev.get("done") else "") + ("★ " if ev.get("mine") else "")
            line = "%s [%s] %s" % (ev.get("time") or "종일", ev.get("kind", ""), ev_label(ev))
            self.day_list.insert("end", mark + (strike(line) if ev.get("done") else line))
        if self.day_events:
            idx = 0
            for i, ev in enumerate(self.day_events):    # 방금 클릭한 일정이 있으면 그것을 선택
                if ev["id"] == self.pending_select_id:
                    idx = i
            self.day_list.selection_set(idx)
        self.pending_select_id = None
        self.show_detail()

        self.soon_events = self.store.upcoming(self.today, 14)
        self.soon_list.delete(0, "end")
        for ev in self.soon_events:
            n = core.dday(ev["date"], self.today)
            self.soon_list.insert("end", " %-6s  %s  %s" % (core.dday_text(n), ev["date"][5:], ev_label(ev)))
            if n <= 0:
                self.soon_list.itemconfig("end", fg="#a12622")
            elif n <= 3:
                self.soon_list.itemconfig("end", fg="#7a5b00")
        late = sum(1 for e in self.soon_events if core.dday(e["date"], self.today) <= 3)
        self.nb.tab(1, text=" ⏰ 임박한 기한 %s" % (("(%d) " % late) if late else ""))

    def current_event(self):
        sel = self.day_list.curselection()
        if sel and sel[0] < len(self.day_events):
            return self.day_events[sel[0]]
        return None

    def show_detail(self):
        """오른쪽 '공문 내용' 칸: 요약 몇 줄 + 공문 본문 전체 (기한 날짜는 노랗게 표시)"""
        ev = self.current_event()
        t = self.detail
        t.config(state="normal")
        t.delete("1.0", "end")
        self.state_var.set("처리" if ev and ev.get("done") else ("미처리" if ev else ""))
        for b in self.seg:
            b.state(["!disabled"] if ev else ["disabled"])
        if not ev:
            t.insert("end", "이 날짜에는 일정이 없습니다.\n\n", "hint")
            t.insert("end", "· 날짜 칸을 더블클릭하면 메모를 적을 수 있어요.\n· [＋ 공문 추가]를 누르거나 공문 PDF를 창에 끌어다 놓으세요.", "hint")
        else:
            d = dt.date.fromisoformat(ev["date"])
            n = core.dday(ev["date"], self.today)
            t.insert("end", ev["title"] + "\n", "h")
            state = ("처리 완료" + ((" (%s)" % ev["done_at"]) if ev.get("done_at") else "")) if ev.get("done") else core.dday_text(n)
            t.insert("end", "📅 %d. %d. %d.(%s) %s · %s · %s\n" % (d.year, d.month, d.day, "월화수목금토일"[d.weekday()],
                                                                 ev.get("time") or "종일", ev.get("kind", ""), state), "meta")
            if ev.get("doc_no") or ev.get("org"):
                t.insert("end", "🏢 %s%s\n" % (ev.get("doc_no", ""), ("  · 시행 " + ev["org"]) if ev.get("org") else ""), "meta")
            if ev.get("attachments"):
                t.insert("end", "📎 " + " / ".join(ev["attachments"]) + "\n", "meta")
            if ev.get("mine") or ev.get("note"):
                t.insert("end", "★ 내 실적" + ((" · " + ev["note"]) if ev.get("note") else "") + "\n", "meta")
            if ev.get("repeat"):
                t.insert("end", "🔁 " + core.describe_repeat(ev["repeat"]) + "\n", "meta")
            if ev.get("links"):
                t.insert("end", "🔗 관련 공문: " + " / ".join(lk.get("title", "") for lk in ev["links"]) + "\n", "meta")
            if ev.get("memo"):
                t.insert("end", "\n📝 " + ev["memo"] + "\n", "memo")
            if ev.get("kind") != "메모":
                body = self.doc_body(ev)
                t.insert("end", "──────── 공문 내용 ────────\n", "sep")
                if body:
                    start = t.index("end-1c")
                    t.insert("end", body.strip() + "\n", "body")
                    self._mark_date(start, d)
                else:
                    t.insert("end", "(저장된 공문 내용이 없습니다. [📄 원본]으로 여세요)\n", "hint")
        t.config(state="disabled")
        t.yview_moveto(0)

        self.rel_items = []                             # (보일 글자, 더블클릭하면 할 일)
        if ev:
            for e in core.linked_events(self.store.events, ev):        # 메모에서 직접 연결한 공문 / 나를 연결한 메모
                mark = "📝" if e.get("kind") == "메모" else "🔗"
                self.rel_items.append(("%s %s  %s" % (mark, e["date"][5:], ev_label(e)), lambda e=e: self.show_event(e)))
            for lk in ev.get("links") or []:
                if lk.get("file"):
                    self.rel_items.append(("📎 %s" % lk.get("title", ""), lambda lk=lk: self.open_link(lk)))
            for e in core.related_events(self.store.events, ev):       # 문서번호로 이어진 공문
                self.rel_items.append(("%s  %s  %s" % (e["date"][5:], e.get("doc_no", ""), ev_label(e)),
                                       lambda e=e: self.show_event(e)))
        self.rel_list.delete(0, "end")
        for text, _act in self.rel_items:
            self.rel_list.insert("end", text)
        if ev and not self.rel_items:
            refs = ev.get("refs") or []
            self.rel_list.insert("end", ("  (달력에 없음: " + ", ".join(refs[:3]) + ")") if refs else "  (관련 공문 없음)")
            self.rel_list.itemconfig("end", fg="#9aa0aa")

    def doc_body(self, ev):
        """공문 본문 글자. 예전에 올린 일정은 보관된 공문 파일에서 읽어 온다 (한 번 읽으면 기억)."""
        if ev.get("body"):
            return ev["body"]
        path = core.resolve_doc_path(ev)
        if not path:
            return ""
        if path not in self._body_cache:
            try:
                self._body_cache[path] = core.read_file_text(path)
            except Exception:
                self._body_cache[path] = ""
        return self._body_cache[path]

    def _mark_date(self, start, d):
        """본문에서 그 일정 날짜('12. 3.', '12월 3일', '2026-12-03')를 노랗게 칠한다"""
        pats = [r"%d\s*\.\s*%d\s*\.(?!\d)" % (d.month, d.day), r"%d\s*월\s*%d\s*일" % (d.month, d.day),
                r"%d-%02d-%02d" % (d.year, d.month, d.day), r"(?<![\d/])%d/%d(?![\d/])" % (d.month, d.day)]
        text = self.detail.get(start, "end")
        for pat in pats:
            for m in re.finditer(pat, text):
                self.detail.tag_add("mark", "%s+%dc" % (start, m.start()), "%s+%dc" % (start, m.end()))

    def on_state_change(self):
        ev = self.current_event()
        if ev and (self.state_var.get() == "처리") != bool(ev.get("done")):
            self.set_done_toggle(ev)

    def edit_current(self):
        ev = self.current_event()
        if ev:
            EventDialog(self, ev)
        else:
            EventDialog(self, day=self.selected)

    def on_rel_double(self, e):
        i = self.rel_list.nearest(e.y)
        if 0 <= i < len(self.rel_items):
            self.rel_items[i][1]()

    def open_link(self, lk):
        """메모에 연결한 공문을 연다 (달력의 공문이면 그 공문 일정으로, 파일이면 파일을)"""
        if lk.get("file"):
            if os.path.isfile(lk["file"]):
                try:
                    open_with_default_app(lk["file"])
                except OSError as e:
                    messagebox.showerror("열기 실패", str(e), parent=self.root)
            else:
                messagebox.showinfo("안내", "파일을 찾지 못했습니다.\n%s" % lk["file"], parent=self.root)
            return
        for e in self.store.events:
            if core.link_key(e) == lk.get("key") and e.get("kind") != "메모":
                self.show_event(e)
                return
        messagebox.showinfo("안내", "연결한 공문이 달력에서 지워졌어요.", parent=self.root)

    def jump_to_soon(self, _e):
        sel = self.soon_list.curselection()
        if sel and sel[0] < len(self.soon_events):
            self.show_event(self.soon_events[sel[0]])
            self.nb.select(0)

    # ---- 동작 ------------------------------------------------------------
    def select(self, day):
        self.selected = day
        if (day.year, day.month) != (self.year, self.month):
            self.year, self.month = day.year, day.month
        self.refresh()

    def go_to(self, day):
        self.select(day)

    def show_event(self, ev):
        """그 일정이 있는 날로 가서 선택하고 큰 창을 보여 준다"""
        self.show_main()
        self.pending_select_id = ev["id"]
        self.nb.select(0)
        self.go_to(dt.date.fromisoformat(ev["date"]))

    def show_main(self):
        self.root.deiconify()
        self.root.lift()

    def move_month(self, delta):
        m = self.month + delta
        self.year += (m - 1) // 12
        self.month = (m - 1) % 12 + 1
        self.selected = dt.date(self.year, self.month, 1)
        self.refresh()

    # ---- 일정 끌어서 옮기기 (Ctrl = 복사) ------------------------------------
    def drag_press(self, e, day, ev):
        self._drag = {"ev": ev, "day": day, "x": e.x_root, "y": e.y_root, "ghost": None, "cell": None}
        self.on_event_click(day, ev)

    def cell_at(self, x, y):
        """화면 좌표 아래에 있는 달력 칸의 날짜"""
        w = self.root.winfo_containing(x, y)
        cells = {str(c): d for d, c in self._cells.items()}
        while w is not None:
            if str(w) in cells:
                return cells[str(w)]
            w = w.master
        return None

    def drag_motion(self, e):
        dg = getattr(self, "_drag", None)
        if not dg:
            return
        if dg["ghost"] is None:
            if abs(e.x_root - dg["x"]) + abs(e.y_root - dg["y"]) < 8:
                return                                  # 조금 흔들린 건 클릭으로 본다
            if self._click_job:
                self.root.after_cancel(self._click_job)
                self._click_job = None
            dg["ghost"] = DragGhost(self.root, ev_label(dg["ev"]))
        target = self.cell_at(e.x_root, e.y_root)
        if target != dg["cell"]:                        # 놓을 칸을 초록 테두리로 표시
            for d in (dg["cell"], target):
                c = self._cells.get(d)
                if c is not None and c.winfo_exists():
                    hl = d == target
                    c.config(highlightthickness=2 if hl or d == self.selected else 1,
                             highlightbackground="#2e9d5b" if hl else (PRIMARY if d == self.selected else "#e3e7ee"))
            dg["cell"] = target
        dg["ghost"].show(e.x_root, e.y_root, ctrl_down(e), target)

    def drag_release(self, e):
        dg, self._drag = getattr(self, "_drag", None), None
        if not dg or dg["ghost"] is None:
            return                                      # 끌지 않았으면 그냥 클릭
        dg["ghost"].close()
        self._mark_selected()
        target = self.cell_at(e.x_root, e.y_root)
        if target:
            self.move_event(dg["ev"], target, copy=ctrl_down(e))

    def move_event(self, ev, new_day, copy=False):
        """일정을 다른 날로 옮기거나(copy=False) 복사한다. 반복 일정은 그날 것만 떼어 내서 옮긴다."""
        new_iso, old_iso = new_day.isoformat(), ev["date"]
        if new_iso == old_iso and not copy:
            return
        store = self.store
        if copy or ev.get("series"):
            src = store.get(ev["series"]) if ev.get("series") else ev
            new = {k: v for k, v in src.items()
                   if k not in ("id", "updated", "repeat", "done_dates", "skip_dates", "series", "done", "done_at")}
            new.update(date=new_iso, done=False, done_at="")
            if ev.get("series") and not copy:
                store.delete(ev["id"])                  # 반복에서 그날만 빼고
            store.add(new)
            new_id = new["id"]

            def undo():
                store.delete(new_id)
                if ev.get("series") and not copy:       # 빼 두었던 반복 날짜 되살리기
                    m = store.get(ev["series"])
                    if m:
                        store.update(m["id"], {"skip_dates": [x for x in (m.get("skip_dates") or []) if x != old_iso]})
                self.refresh()
        else:
            store.update(ev["id"], {"date": new_iso})
            self.settings.get("alerted", {}).pop(ev["id"], None)   # 날짜가 바뀌었으니 알림을 다시 받게
            new_id = ev["id"]

            def undo():
                store.update(ev["id"], {"date": old_iso})
                self.refresh()
        self.pending_select_id = new_id
        if new_day in self._cells:                      # 지금 보이는 칸이면 달을 넘기지 않는다
            self.selected = new_day
            self.refresh()
        else:
            self.go_to(new_day)
        o, n = dt.date.fromisoformat(old_iso), new_day
        Toast(self, "⧉ 복사했어요" if copy else "↔ 옮겼어요",
              "%s\n%d월 %d일 → %d월 %d일" % (ev_label(ev), o.month, o.day, n.month, n.day),
              color="#2e9d5b" if copy else PRIMARY, on_open=undo, link_text="↶ 되돌리기", timeout=8000)

    def on_event_click(self, day, ev):
        """일정을 한 번 누르면 그날을 선택한다. (더블클릭과 구분하려고 0.25초 기다린다)
        바로 화면을 새로 그리면 두 번째 클릭이 사라져서 더블클릭이 안 되기 때문이다."""
        if self._click_job:
            self.root.after_cancel(self._click_job)

        def later():
            self._click_job = None
            self.pending_select_id = ev["id"]
            self.select(day)
        self._click_job = self.root.after(250, later)

    def on_event_double(self, ev):
        """일정을 더블클릭하면 설정 창(달력 글자 · 색 · 완료 · 메모)을 연다"""
        if self._click_job:
            self.root.after_cancel(self._click_job)
            self._click_job = None
        self.pending_select_id = ev["id"]
        self.select(dt.date.fromisoformat(ev["date"]))
        EventDialog(self, ev)

    # ---- 우클릭 메뉴 -------------------------------------------------------
    def popup_menu(self, x, y, ev):
        m = self.menu
        m.delete(0, "end")
        m.add_command(label="⚙ 설정 (글자 · 색 · 완료 · 메모)…", command=lambda: EventDialog(self, ev))
        m.add_command(label="📅 공문 내용 보기", command=lambda: self.show_event(ev))
        m.add_command(label="📄 원본 공문 열기", command=lambda: self.open_event_doc(ev))
        m.add_separator()
        m.add_command(label="↩ 완료 취소" if ev.get("done") else "✔ 완료했음 (가운데 줄)", command=lambda: self.set_done_toggle(ev))
        m.add_command(label="☆ 내 실적에서 빼기" if ev.get("mine") else "★ 내 실적에 넣기 (자기역량기술서)", command=lambda: self.set_mine_toggle(ev))
        m.add_command(label="📝 실적 메모 쓰기…", command=lambda: NoteDialog(self, ev))
        m.add_separator()
        m.add_command(label="🗑 삭제", command=lambda: self.delete_given(ev))
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def popup_from_list(self, e):
        """오른쪽 목록에서 우클릭: 마우스 아래 항목을 선택하고 메뉴를 띄운다"""
        i = self.day_list.nearest(e.y)
        if 0 <= i < len(self.day_events):
            self.day_list.selection_clear(0, "end")
            self.day_list.selection_set(i)
            self.show_detail()
            self.popup_menu(e.x_root, e.y_root, self.day_events[i])

    def set_done_toggle(self, ev):
        self.pending_select_id = ev["id"]
        self.store.toggle_done(ev["id"])
        self.refresh()

    def set_mine_toggle(self, ev):
        self.pending_select_id = ev["id"]
        self.store.toggle_mine(ev["id"])
        self.refresh()

    def delete_given(self, ev):
        if ev.get("series"):                            # 반복 일정: 그날만 / 전체
            d = dt.date.fromisoformat(ev["date"])
            ans = messagebox.askyesnocancel("반복 일정 삭제", "'%s' 는 반복 일정입니다.\n\n[예]  %d월 %d일 것만 지우기\n[아니요]  반복 전체 지우기"
                                            % (ev["title"], d.month, d.day), parent=self.root)
            if ans is None:
                return
            self.store.delete(ev["id"] if ans else ev["series"])
            self.refresh()
            return
        if messagebox.askyesno("삭제", "이 일정을 삭제할까요?\n%s\n(보관된 공문 파일은 지워지지 않습니다)" % ev["title"], parent=self.root):
            self.store.delete(ev["id"])
            self.refresh()

    def open_event_doc(self, ev):
        path = core.resolve_doc_path(ev)
        if not path:
            messagebox.showinfo("안내", "저장된 공문 파일을 찾지 못했습니다.\n(공문정리 폴더에서 옮기거나 지운 경우일 수 있어요)", parent=self.root)
            return
        try:
            open_with_default_app(path)
        except OSError as e:
            messagebox.showerror("열기 실패", "공문을 열지 못했습니다.\n%s" % e, parent=self.root)

    def open_source(self):
        ev = self.current_event()
        if ev:
            self.open_event_doc(ev)

    def toggle_done(self):
        ev = self.current_event()
        if ev:
            self.set_done_toggle(ev)

    def toggle_mine_current(self):
        ev = self.current_event()
        if ev:
            self.set_mine_toggle(ev)

    def delete_event(self):
        ev = self.current_event()
        if ev:
            self.delete_given(ev)

    # ---- 내보내기 ----------------------------------------------------------
    def export_ics(self):
        evs = [e for e in self.store.events if not e.get("done")]
        if not evs:
            messagebox.showinfo("안내", "내보낼 일정이 없습니다.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".ics",
                                            initialfile="공문일정.ics", filetypes=[("캘린더 파일", "*.ics")])
        if path:
            core.export_ics(evs, path)
            messagebox.showinfo("완료", "%d건을 내보냈습니다.\n구글캘린더/아웃룩의 '가져오기'로 불러오세요." % len(evs), parent=self.root)

    def export_xlsx(self, parent=None):
        parent = parent or self.root
        path = filedialog.asksaveasfilename(parent=parent, defaultextension=".xlsx", filetypes=[("엑셀 파일", "*.xlsx")],
                                            initialfile="업무처리현황_%s.xlsx" % dt.date.today().strftime("%Y%m%d"))
        if not path:
            return
        try:
            core.export_xlsx(self.store.events, path)
        except OSError as e:
            messagebox.showerror("저장 실패", "엑셀 파일을 저장하지 못했습니다. (엑셀에서 열려 있으면 닫아 주세요)\n%s" % e, parent=parent)
            return
        if messagebox.askyesno("완료", "엑셀 파일로 저장했습니다.\n지금 열어 볼까요?", parent=parent):
            try:
                open_with_default_app(path)
            except OSError:
                pass

    # ---- 창 열기 ------------------------------------------------------------
    def open_add_dialog(self, path=None):
        self.bring_front(AddDialog(self, path=path).win)

    def open_batch(self, paths=()):
        self.bring_front(BatchDialog(self, paths).win)

    def open_settings(self, tab="team"):
        SettingsDialog(self, tab)

    def open_search(self, query=""):
        query = "" if query == self.SEARCH_HINT else query
        if self.search_win is not None:
            self.search_win.q.set(query)
            self.search_win.win.lift()
            return
        self.search_win = SearchWindow(self, query)

    def open_achievements(self):
        if self.ach_win is not None:
            self.ach_win.win.lift()
            return
        self.ach_win = AchievementWindow(self)

    def open_widget(self, kind=None):
        """kind: "desk"(달력 위젯) / "list"(목록 위젯) / None = 설정에서 고른 위젯 모두"""
        kinds = [kind] if kind else [k for k, on in self.settings.get("widgets", {"desk": True}).items() if on]
        for k in kinds:
            cur = self.deskcal if k == "desk" else self.widget
            if cur is not None:
                cur.win.deiconify()
                if k == "list":
                    cur.win.lift()
                continue
            if k == "desk":
                self.deskcal = DeskCalendar(self)
            else:
                self.widget = WidgetWindow(self)

    def reopen_widget(self, kind):
        """모양(테마 등)이 바뀐 위젯을 닫았다가 다시 연다"""
        cur = self.deskcal if kind == "desk" else self.widget
        if cur is not None:
            cur.close(quit_if_alone=False)
            self.open_widget(kind)

    def widget_closed(self, kind, quit_if_alone=True):
        if kind == "desk":
            self.deskcal = None
        else:
            self.widget = None
        if self.tray_ok:
            return                                      # 트레이 아이콘이 있으면 계속 살아 있다 (종료는 트레이 메뉴에서)
        if quit_if_alone and self.widget is None and self.deskcal is None and not self.root.winfo_viewable():
            self.root.destroy()                         # 트레이가 없을 때: 큰 창이 숨겨진 상태에서 마지막 위젯을 닫으면 종료

    def open_status(self):
        if self.status_win is not None:
            self.status_win.win.lift()
            return
        self.status_win = StatusWindow(self)

    def on_drop(self, paths):
        """큰 달력·위젯에 파일을 끌어 놓으면: 하나면 공문 추가, 여러 개면 한꺼번에 등록"""
        files = gs.expand_paths(paths)
        if len(files) == 1:
            self.open_add_dialog(path=files[0])
        elif files:
            self.open_batch(files)
        else:
            Toast(self, "📥 공문 파일이 아니에요", "PDF · HWPX · TXT 파일(또는 그런 파일이 든 폴더)을 놓아 주세요.", timeout=5000)

    def bring_front(self, win):
        """창을 맨 앞으로 (위젯에 끌어 놓았을 때 큰 창이 숨겨져 있어도 공문 추가 창이 보이게)"""
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(400, lambda: win.winfo_exists() and win.attributes("-topmost", False))
            win.focus_force()
        except tk.TclError:
            pass

    def on_close_main(self):
        """트레이 아이콘이 있으면 창만 숨기고 계속 실행한다. 없으면 위젯이 떠 있을 때만 숨긴다."""
        if self.tray_ok:
            self.root.withdraw()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                Toast(self, "🔽 트레이에서 계속 실행 중이에요",
                      "작업표시줄 오른쪽 아래 아이콘을 누르면 다시 열려요.\n완전히 끄려면 아이콘 우클릭 > 종료", timeout=7000)
        elif self.widget is not None or self.deskcal is not None:
            self.root.withdraw()
            Toast(self, "🧩 위젯은 계속 떠 있어요", "큰 달력을 다시 보려면 위젯의 ▣ 를 누르세요.\n위젯을 모두 닫으면 프로그램이 끝납니다.", timeout=6000)
        else:
            self.root.destroy()

    # ---- 트레이 아이콘 (작업표시줄 오른쪽 아래) ----------------------------------
    def start_tray(self):
        self.tray = gs.TrayIcon(resource_path("icon.ico"), self.tray_tooltip(), self.tray_menu_items)
        self.tray_ok = self.tray.start()
        if self.tray_ok:
            self.root.after(150, self.poll_tray)

    def tray_tooltip(self):
        team = core.team_for(dt.date.today(), self.settings)
        return APP_NAME + ((" · 오늘 근무 %d팀" % team) if team else "")

    def tray_menu_items(self):
        """오른쪽 클릭 메뉴 (트레이 쓰레드에서 부르므로 화면을 건드리지 않고 상태만 읽는다)"""
        shown = self._main_visible                      # Tk 를 직접 부르지 않고 미리 적어 둔 값을 쓴다
        return [("toggle", "📅 업무보조 달력 " + ("숨기기" if shown else "열기"), False), None,
                ("desk", "달력 위젯 (바탕화면 큰 달력)", self.deskcal is not None),
                ("list", "목록 위젯 (오늘 근무 · 임박 기한)", self.widget is not None), None,
                ("add", "＋ 공문 추가", False), ("settings", "⚙ 설정", False), None,
                ("quit", "✕ 종료", False)]

    def poll_tray(self):
        try:
            while True:
                self.handle_tray(self.tray.commands.get_nowait())
        except queue.Empty:
            pass
        except Exception:
            pass
        if self.tray_ok:
            self.root.after(150, self.poll_tray)

    def handle_tray(self, cmd):
        if cmd == "toggle":
            if self.root.state() == "withdrawn" or self.root.state() == "iconic":
                self.show_main()
            else:
                self.root.withdraw()
        elif cmd in ("desk", "list"):
            cur = self.deskcal if cmd == "desk" else self.widget
            if cur is not None:
                cur.close(quit_if_alone=False)
            else:
                self.open_widget(cmd)
            self.settings.setdefault("widgets", {})[cmd] = cur is None     # 자동 실행 때도 이 상태로 켜지게
            core.save_settings(self.settings)
        elif cmd == "add":
            self.show_main()
            self.open_add_dialog()
        elif cmd == "settings":
            self.show_main()
            self.open_settings()
        elif cmd == "show":                             # 프로그램을 또 켰을 때: 이미 켜진 쪽을 보여 준다
            self.show_main()
        elif cmd == "widgets":                          # 윈도우 시작 때 또 켜진 경우: 위젯만
            self.open_widget()
        elif cmd == "quit":
            self.quit_app()

    def save_widget_positions(self):
        for w in (self.deskcal, self.widget):
            if w is not None:
                try:
                    w.save_cfg()
                except Exception:
                    pass

    def quit_app(self):
        self.save_widget_positions()
        self.tray_ok = False
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.destroy()

    # ---- 설정 적용 -----------------------------------------------------------
    def apply_settings(self, first=False, share_changed=False, desk_changed=False):
        s = self.settings
        self._srev += 1
        set_team_theme(s.get("team_theme"))
        if share_changed:
            self.switch_store()
        dl = s.get("download_dir") or gs.default_download_dir()
        if s.get("watch_downloads") and os.path.isdir(dl):
            if self.watcher is None or self.watcher.folder != dl:
                self.watcher = gs.FolderWatcher(dl)     # 켤 때 이미 있던 파일은 무시
        else:
            self.watcher = None
        if desk_changed and self.deskcal is not None:   # 달력 위젯 모양이 바뀌었으면 새로 연다
            self.reopen_widget("desk")
        if not first:
            self.refresh()
            self.check_alerts(schedule=False)
        else:
            self.update_statusbar()

    def switch_store(self):
        """저장 위치(공유 폴더)를 바꾼다. 지금 일정을 새 위치에도 넣을지 묻는다."""
        old = list(self.store.events)
        self.share_ok = core.set_shared_dir(self.settings.get("shared_dir", "")) or not self.settings.get("shared_dir")
        self.store = core.Store(core.shared_path("공문일정.json"))
        have = {e["id"] for e in self.store.events}
        missing = [e for e in old if e["id"] not in have]
        if missing and messagebox.askyesno("저장 위치 바꾸기", "지금까지의 일정 %d건을 새 위치에도 넣을까요?\n"
                                           "(넣지 않으면 새 위치의 일정만 보입니다)\n\n※ 보관된 공문 파일은 옮겨지지 않습니다." % len(missing),
                                           parent=self.root):
            self.store.events.extend(missing)
            self.store.save()

    # ---- 계속 도는 일 (3초마다) ------------------------------------------------
    def background_tick(self):
        self._tick += 1
        try:
            if self.watcher is not None:                # 다운로드 폴더에 새 공문
                new = self.watcher.check()
                if new:
                    self.on_new_downloads(new)
            if self._tick % 5 == 0 and self.store.changed_on_disk():   # 15초마다: 다른 사람이 고쳤나
                self.store.reload()
                self.refresh()
            if dt.date.today() != self.today:           # 자정이 지났으면
                self.refresh()
                self.check_alerts(schedule=False)
        finally:
            self.root.after(3000, self.background_tick)

    def on_new_downloads(self, paths):
        names = ", ".join(os.path.basename(p) for p in paths[:2]) + (" 외 %d개" % (len(paths) - 2) if len(paths) > 2 else "")
        Toast(self, "📥 새 공문을 받았어요", names, timeout=8000)
        if len(paths) == 1:
            self.open_add_dialog(path=paths[0])
        else:
            self.open_batch(paths)

    # ---- 기한 알림 ------------------------------------------------------------
    def check_alerts(self, schedule=True):
        try:
            s = self.settings
            if s.get("alerts_on", True):
                alerted = s.setdefault("alerted", {})
                items = core.due_alerts(self.store.alert_events(dt.date.today()), dt.date.today(),
                                        s.get("alert_levels", [3, 1, 0]), alerted)
                if items:
                    for ev, lv in items:
                        alerted.setdefault(ev["id"], []).append(lv)
                    live = {e["id"] for e in self.store.events}
                    for k in [k for k in alerted if k.split("@")[0] not in live]:     # 지워진 일정 기록은 정리
                        del alerted[k]
                    core.save_settings(s)
                    self.show_alerts(items)
        finally:
            if schedule:
                self.root.after(10 * 60 * 1000, self.check_alerts)       # 10분마다

    def show_alerts(self, items):
        colors = {"D-3": "#b45309", "D-1": "#d9480f", "D-day": "#c0392b", "지남": "#7f1d1d"}
        names = {"D-3": "3일 남음", "D-1": "내일까지", "D-day": "오늘까지", "지남": "기한 지남"}
        if len(items) <= 3:
            for ev, lv in items:
                body = "%s\n%s %s · %s" % (ev_label(ev), ev["date"], ev.get("time") or "", ev.get("kind", ""))
                Toast(self, "⏰ %s (%s)" % (names[lv], lv if lv != "지남" else core.dday_text(core.dday(ev["date"], self.today))),
                      body, color=colors[lv], on_open=lambda ev=ev: self.show_event(ev))
        else:
            body = "\n".join("· %s %s" % (lv, ev_label(ev)[:28]) for ev, lv in items[:4])
            if len(items) > 4:
                body += "\n· 외 %d건" % (len(items) - 4)
            Toast(self, "⏰ 기한 알림 %d건" % len(items), body, color="#c0392b",
                  on_open=lambda: (self.show_main(), self.nb.select(1)), timeout=30000)
        if self.settings.get("widget_flash", True):
            for w in (self.widget, self.deskcal):
                if w is not None:
                    w.flash()

    def run(self):
        self.root.mainloop()


def selftest():
    """exe 를 만든 뒤 윈도우에서 실제로 켜 보는 검사 (--selftest). 결과는 selftest.log 에 적는다."""
    import traceback
    out = []
    try:
        for mod in ("gongmun_pdf", "gongmun_xlsx", "gongmun_kcal", "gongmun_rename", "gongmun_system"):
            __import__(mod)
        out.append("modules ok")
        out.append("lunar 2026-11-23 = %s" % (kcal.solar_to_lunar(dt.date(2026, 11, 23)),))
        res = core.analyze("제목 시험 공문\n1. 자료를 2026. 12. 1.(화)까지 제출하여 주시기 바랍니다.")
        out.append("analyze %s" % [(str(c["date"]), c["kind"]) for c in res["candidates"]])
        app = App()
        app.root.update()
        out.append("main window ok")
        app.open_widget("desk")
        app.open_widget("list")
        app.root.update()
        out.append("widgets ok (desktop pinned=%s)" % app.deskcal.pinned)
        out.append("tray ok=%s %s" % (app.tray_ok, app.tray.error if app.tray else ""))
        out.append("widget drop desk=%s list=%s" % (app.deskcal.drop_ok, app.widget.drop_ok))
        first = gs.acquire_single_instance("Local\\GongmunSelfTestMutex", signal=False)
        second = gs.acquire_single_instance("Local\\GongmunSelfTestMutex", signal=False)
        out.append("single instance first=%s second=%s (정상: True/False)" % (first, second))
        out.append("virtual screen=%s" % (gs.virtual_screen(),))
        if app.tray_ok:
            app.handle_tray("desk"); app.root.update()          # 트레이 메뉴 명령도 눌러 본다
            app.handle_tray("desk"); app.root.update()
            app.handle_tray("toggle"); app.handle_tray("toggle"); app.root.update()
            out.append("tray commands ok, menu=%d items" % len(app.tray_menu_items()))
            app.tray.stop()
            app.tray_ok = False
        for make in (lambda: AddDialog(app), lambda: BatchDialog(app), lambda: SettingsDialog(app, "widget"),
                     lambda: StatusWindow(app), lambda: SearchWindow(app, "시험"),
                     lambda: EventDialog(app, day=dt.date.today())):
            w = make()
            app.root.update()
            w.win.destroy()
        out.append("dialogs ok")
        x = core.data_path("selftest.xlsx")
        core.export_xlsx([], x)
        os.remove(x)
        out.append("xlsx ok, autostart supported=%s" % gs.autostart_supported())
        app.deskcal.close(quit_if_alone=False)
        app.widget.close(quit_if_alone=False)
        app.root.destroy()
        out.append("OK")
    except Exception:
        out.append(traceback.format_exc())
    with open(core.data_path("selftest.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif not gs.acquire_single_instance(widgets_only="--widget" in sys.argv):
        sys.exit(0)                                     # 이미 켜져 있다: 그쪽을 보여 주고 이 프로그램은 끝낸다
    else:
        App(widget_only="--widget" in sys.argv).run()   # python gongmun_calendar.py --widget  : 위젯만 실행
