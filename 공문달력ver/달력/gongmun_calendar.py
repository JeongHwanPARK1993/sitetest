# -*- coding: utf-8 -*-
"""
gongmun_calendar.py  -  공문 달력 (화면 부분)

실행:  python gongmun_calendar.py            (전체 화면)
       python gongmun_calendar.py --widget   (바탕화면 위젯만)

화면 구성
  [머리줄]    월 이동 · 오늘 근무팀 · 검색칸
  [도구줄]    ＋공문 추가 · 여러 개 한꺼번에 | 업무 현황 · 내 실적 · 검색 | 위젯 · 내보내기 · 설정
  [왼쪽]      월간 달력 (칸마다 근무팀, 일정을 누르면 선택 / 더블클릭하면 공문 열기)
  [오른쪽]    선택한 날: 일정 · 상세 · 회신 할 일 · 관련 공문  /  임박한 기한
  [아래 줄]   저장 위치 · 다운로드 감시 · 복사 분석 · 알림 상태 (누르면 설정이 열린다)

공문에서 기한을 찾는 규칙은 gongmun_core.py, 용어는 용어사전.txt,
파일 이름 만들기는 gongmun_rename.py, 윈도우 기능(끌어놓기·자동 실행)은 gongmun_system.py 에 있습니다.
"""
import calendar
import datetime as dt
import os
import subprocess
import sys
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox, ttk

import author_credit
import gongmun_core as core
import gongmun_rename as rn                        # 공문 PDF 에서 제목·시행기관·시행일자를 읽어 파일 이름을 만든다
import gongmun_system as gs                        # 파일 끌어놓기 · 윈도우 시작 시 실행 · 폴더 감시

FONT = "맑은 고딕"
KINDS = ["기한", "행사", "애매", "기타", "변경전"]
TEAM_COLORS = {1: "#2f6fed", 2: "#2e9d5b", 3: "#d98200"}      # 1팀 파랑 / 2팀 초록 / 3팀 주황

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
    """공문 한 건 저장: (원본 이름 바꾸기) → 공문보관에 사본 → 일정 저장.
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


def make_event(date_iso, time_text, kind, snippet, common):
    ev = {"date": date_iso, "time": time_text, "kind": kind, "snippet": snippet}
    for k, v in common.items():                         # 할 일 목록은 일정마다 따로 복사
        ev[k] = [dict(t) for t in v] if k == "todos" else v
    return ev


# ══════════════════════════════════════════════════════════════
#  공문 추가 창
#   ① 공문 내용(붙여넣기/불러오기/끌어놓기) → ② 공문 정보·파일 이름 → ③ 날짜 → ④ 붙임·할 일 → 등록
# ══════════════════════════════════════════════════════════════
class AddDialog:
    def __init__(self, app, prefill="", path=None):
        self.app = app
        self.source = ""                                # 불러온 원본 파일 경로
        self.rows = []                                  # 날짜 후보 한 줄 한 줄
        self.rename_info = None                         # PDF 에서 읽은 제목·시행정보 (rn.DocInfo)
        self.emails = []

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
        self.tpl_var = tk.StringVar(value=s.get("rename_template", rn.DEFAULT_TEMPLATE))
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

        # ④ 붙임 · 회신 할 일
        extra = ttk.LabelFrame(right, text=" ④ 붙임 · 회신 할 일 (한 줄에 하나) ", padding=8)
        extra.pack(fill="both", expand=True, padx=(8, 0))
        for col, (label, attr) in enumerate([("📎 붙임", "attach_text"), ("☑ 회신 할 일 (달력에서 체크할 수 있어요)", "todo_text")]):
            ttk.Label(extra, text=label, font=(FONT, 9, "bold")).grid(row=0, column=col, sticky="w", padx=4)
            t = tk.Text(extra, height=4, wrap="word", font=(FONT, 9), relief="flat", bg="#fbfcfe",
                        highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY, padx=4, pady=3)
            t.grid(row=1, column=col, sticky="nsew", padx=4)
            setattr(self, attr, t)
            extra.columnconfigure(col, weight=1)
        extra.rowconfigure(1, weight=1)

        if not gs.enable_file_drop(win, self.on_drop):
            self.hint.config(text="📂 [파일 불러오기]로 공문 PDF/HWPX 를 여세요.  공문 내용을 복사해서 붙여넣어도 됩니다.")
        if prefill:
            self.text.insert("1.0", prefill)
            self.run_analyze()
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
        self.todo_text.delete("1.0", "end")
        self.todo_text.insert("1.0", "\n".join(result.get("todos") or result["requests"]))
        self.emails = result["emails"]

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
            self.name_note.config(text="PDF 가 아니어서 이름은 [날짜_제목] 으로 보관합니다. (직접 적어도 돼요)")
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
        self.name_note.config(text=("⚠ 확인 필요: " + " / ".join(notes)) if notes else "✔ 공문에서 이름을 만들었어요. 고쳐도 됩니다.")

    # ---- 등록 ----------------------------------------------------------
    def register(self):
        title = self.title_var.get().strip() or "(제목 없음)"
        lines = lambda t: [a.strip() for a in t.get("1.0", "end").splitlines() if a.strip()]
        text = self.text.get("1.0", "end")
        docno = self.docno_var.get().strip()
        common = {"title": title, "doc_no": docno, "org": self.org_var.get().strip(),
                  "attachments": lines(self.attach_text), "emails": self.emails,
                  "todos": [{"text": t, "done": False} for t in lines(self.todo_text)],
                  "refs": core.find_doc_refs(text, docno)}
        new_events = []
        for r in self.rows:
            if not r["check"].get():
                continue
            try:                                        # '2026.11.25' 처럼 점으로 써도 받아 준다
                d = parse_date_text(r["date"].get())
            except ValueError:
                messagebox.showwarning("날짜 확인", "날짜를 YYYY-MM-DD 형식으로 적어 주세요.\n(예: 2026-11-25)", parent=self.win)
                return
            tm = r["time"].get().strip()
            if tm:
                try:
                    h, m = tm.split(":")
                    tm = "%02d:%02d" % (int(h), int(m))
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
        month = "%04d-%02d" % (info.year, info.month) if info and info.year else None   # 시행한 달 폴더에 보관
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
        stem = rn.build_name(rn.DocInfo(**{**info.__dict__, "title": title}), s.get("rename_template", rn.DEFAULT_TEMPLATE),
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
                                          (it["stem"] + os.path.splitext(it["path"])[1]) if it.get("stem") else "[날짜_제목] 으로 보관",
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
                      "todos": [{"text": t, "done": False} for t in (res.get("todos") or res["requests"])],
                      "refs": core.find_doc_refs(it["text"], it["docno"])}
            events = [make_event(c["date"].isoformat(), c.get("time", ""), c["kind"], c["snippet"], common) for c in it["picks"]]
            info = it.get("info")
            month = "%04d-%02d" % (info.year, info.month) if info and info.year else None
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
    TABS = ["team", "alert", "auto", "share", "name"]

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
        self.clip_on = tk.BooleanVar(value=st.get("clip_watch", False))
        ttk.Checkbutton(p, text="📋 공문 내용을 복사(Ctrl+C)하면 자동으로 분석해서 '공문 추가' 창 띄우기",
                        variable=self.clip_on).grid(row=3, column=0, columnspan=3, sticky="w", pady=(14, 2))
        self.auto_on = tk.BooleanVar(value=gs.autostart_enabled())
        cb = ttk.Checkbutton(p, text="🖥 윈도우를 켜면 바탕화면 위젯 자동으로 띄우기", variable=self.auto_on)
        cb.grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 2))
        if not gs.autostart_supported():
            cb.state(["disabled"])
            ttk.Label(p, text="(윈도우에서만 쓸 수 있어요)", style="Sub.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", padx=22)

        # ---- 공유 폴더
        p = page(" 📁 공유 폴더 ")
        ttk.Label(p, text="팀원과 같은 달력 쓰기", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(p, style="Sub.TLabel", justify="left", text=(
            "공유 드라이브(예: \\\\서버\\팀공유\\공문달력)를 지정하면, 일정 파일과 공문보관 폴더를 그곳에 둡니다.\n"
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
        ttk.Label(p, text="공문 PDF 를 보관할 때 붙일 이름", style="Head.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.tpl_var = tk.StringVar(value=st.get("rename_template", rn.DEFAULT_TEMPLATE))
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
            "공문 보관 폴더는 달마다 나뉩니다:  공문보관\\2026-11\\…")).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
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
        self.preview.config(text="예시:  " + rn.build_name(sample, self.tpl_var.get(), self.datefmt_var.get()) + ".pdf")

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
            "watch_downloads": self.dl_on.get(), "download_dir": dl, "clip_watch": self.clip_on.get(),
            "shared_dir": share, "rename_template": self.tpl_var.get(), "rename_date_fmt": self.datefmt_var.get(),
        })
        core.save_settings(st)
        self.win.destroy()
        self.app.apply_settings(share_changed=os.path.normcase(old_share) != os.path.normcase(share))


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
#  알림 창 (화면 오른쪽 아래에 잠깐 떴다 사라지는 작은 창)
# ══════════════════════════════════════════════════════════════
class Toast:
    shown = []                                          # 지금 떠 있는 알림들 (위로 쌓는다)
    W, H = 340, 104

    def __init__(self, app, title, body, color=PRIMARY, on_open=None, timeout=20000):
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
            link = tk.Label(box, text="자세히 보기 ›", font=(FONT, 9, "bold"), fg=PRIMARY, bg=CARD, cursor="hand2")
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

        cols = ("state", "mine", "kind", "date", "time", "title", "todo", "docno", "done_at")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
        for col, text, width in zip(cols, ["상태", "실적", "구분", "기한일", "시간", "공문 제목", "할 일", "문서번호", "완료일"],
                                    [100, 40, 60, 95, 55, 420, 55, 140, 90]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w", stretch=col == "title")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("late", foreground="#a12622")
        self.tree.tag_configure("soon", foreground="#7a5b00")
        self.tree.tag_configure("done", foreground="#8a8f98", font=(FONT, 9, "overstrike"))   # 완료 = 가운데 줄
        self.tree.bind("<Double-1>", lambda e: self.open_doc())
        for b in ("<Button-3>", "<Button-2>"):
            self.tree.bind(b, self.on_right_click)

        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="✔ 완료 / 되돌리기", style="Accent.TButton", command=self.toggle).pack(side="left")
        ttk.Button(bar, text="📄 공문 열기", command=self.open_doc).pack(side="left", padx=6)
        ttk.Button(bar, text="📅 달력에서 보기", command=self.goto).pack(side="left")
        ttk.Button(bar, text="📊 엑셀로 저장", command=lambda: app.export_xlsx(parent=self.win)).pack(side="right")
        ttk.Button(bar, text="CSV", command=self.export).pack(side="right", padx=6)
        ttk.Label(bar, text="(더블클릭 = 공문 열기 · 우클릭 = 메뉴)", style="Sub.TLabel").pack(side="right", padx=10)
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
            todos = ev.get("todos") or []
            todo = ("%d/%d" % (sum(1 for t in todos if t.get("done")), len(todos))) if todos else ""
            self.tree.insert("", "end", iid=ev["id"], tags=(tag,) if tag else (),
                             values=(text, "★" if ev.get("mine") else "", ev.get("kind", ""), ev["date"], ev.get("time", ""),
                                     ev["title"], todo, ev.get("doc_no", ""), ev.get("done_at", "")))

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

    def export(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".csv", initialfile="업무처리현황.csv",
                                            filetypes=[("CSV 파일", "*.csv")])
        if path:
            core.export_csv(self.app.store.events, path)
            messagebox.showinfo("완료", "저장했습니다.\n엑셀에서 열 수 있습니다.", parent=self.win)


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
        w, h = int(self.cfg.get("w", 300)), int(self.cfg.get("h", 420))
        x, y = int(self.cfg.get("x", 60)), int(self.cfg.get("y", 60))
        self.win.geometry("%dx%d+%d+%d" % (w, h, x, y))
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

        self.body = tk.Frame(self.win, bg=self.BG)
        self.body.pack(fill="both", expand=True, padx=8, pady=(6, 14))

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

    def save_cfg(self):
        self.cfg.update({"x": self.win.winfo_x(), "y": self.win.winfo_y(),
                         "w": self.win.winfo_width(), "h": self.win.winfo_height(),
                         "topmost": self.topmost, "alpha": round(self.alpha, 2)})
        core.save_settings(self.app.settings)

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
            self.team_lb.config(text="%d팀 근무" % team, bg=TEAM_COLORS.get(team, "#7a4fd6"))
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
            txt = "%s %s%s" % (ev["date"][5:], (ev["time"] + " ") if ev.get("time") else "", ev["title"])
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

    def close(self):
        if self._job:
            self.win.after_cancel(self._job)
        self.save_cfg()
        self.win.destroy()
        self.app.widget = None
        if not self.app.root.winfo_viewable():
            self.app.root.destroy()                     # 큰 창이 숨겨진 상태에서 위젯을 닫으면 프로그램 종료

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
        self.root.title("공문 달력")
        self.root.geometry("1240x780")
        self.root.minsize(1000, 640)
        setup_style(self.root)
        self.settings = core.load_settings()
        self.share_ok = core.set_shared_dir(self.settings.get("shared_dir", "")) or not self.settings.get("shared_dir")
        self.store = core.Store(core.shared_path("공문일정.json"))
        self.lex = core.load_lexicon(core.data_path("용어사전.txt"))
        self.today = dt.date.today()
        self.year, self.month = self.today.year, self.today.month
        self.selected = self.today
        self.day_events = []                            # 오른쪽 목록에 보이는 일정들
        self.soon_events = []
        self.rel_events = []
        self.status_win = self.ach_win = self.search_win = self.widget = None
        self.widget_only = widget_only
        self._click_job = None                          # 단일 클릭/더블 클릭을 구분하기 위한 예약
        self.pending_select_id = None                   # 클릭한 일정을 오른쪽 목록에서 선택해 두기 위함
        self.last_clip = ""
        self.watcher = None
        self._tick = 0
        self.title_var, self.sel_var, self.team_var = tk.StringVar(), tk.StringVar(), tk.StringVar()

        self.menu = tk.Menu(self.root, tearoff=0)       # 우클릭 메뉴
        self.build_header()
        self.build_toolbar()
        self.build_statusbar()
        self.build_body()
        self.refresh()
        author_credit.add_author_credit(self.root, app_name="공문 달력", bg=STATUS_BG)
        gs.enable_file_drop(self.root, self.on_drop)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_main)
        self.root.bind("<Control-n>", lambda e: self.open_add_dialog())
        self.root.bind("<Control-f>", lambda e: self.focus_search())
        self.root.bind("<Left>", lambda e: self.move_month(-1) if e.widget is self.root else None)
        self.root.bind("<Right>", lambda e: self.move_month(1) if e.widget is self.root else None)

        self.apply_settings(first=True)
        self.root.after(2500, self.check_alerts)        # 켜자마자 기한 알림 확인
        self.root.after(3000, self.background_tick)
        if widget_only:                                 # 위젯만 띄우기: 큰 달력 창은 숨겨 둔다
            self.root.withdraw()
            self.open_widget()

    # ---- 화면 만들기 -----------------------------------------------------
    def build_header(self):
        head = tk.Frame(self.root, bg=PRIMARY_DARK)
        head.pack(fill="x")
        tk.Label(head, text="📅 공문 달력", font=(FONT, 14, "bold"), fg="#ffffff", bg=PRIMARY_DARK).pack(side="left", padx=(16, 24), pady=9)

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
        ttk.Button(inner, text="🔍 검색", command=lambda: self.open_search("")).pack(side="left")

        ttk.Button(inner, text="⚙ 설정", command=lambda: self.open_settings()).pack(side="right")
        mb = ttk.Menubutton(inner, text="📤 내보내기")
        m = tk.Menu(mb, tearoff=0)
        m.add_command(label="📊 엑셀(.xlsx) - 업무 처리 현황", command=self.export_xlsx)
        m.add_command(label="CSV - 업무 처리 현황", command=self.export_csv)
        m.add_command(label="📅 캘린더(.ics) - 구글·아웃룩", command=self.export_ics)
        mb["menu"] = m
        mb.pack(side="right", padx=6)
        ttk.Button(inner, text="🧩 위젯", command=self.open_widget).pack(side="right")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    def build_statusbar(self):
        bar = tk.Frame(self.root, bg=STATUS_BG, height=26)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        self.status_items = {}
        for key, tab in (("store", "share"), ("dl", "auto"), ("clip", "auto"), ("alert", "alert")):
            lb = tk.Label(bar, text="", bg=STATUS_BG, fg=SUB, font=(FONT, 9), cursor="hand2", padx=8)
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, t=tab: self.open_settings(t))
            lb.bind("<Enter>", lambda e, w=lb: w.config(fg=PRIMARY_DARK))
            lb.bind("<Leave>", lambda e, w=lb: w.config(fg=SUB))
            self.status_items[key] = lb
        self.tip_lb = tk.Label(bar, text="일정 한 번 클릭 = 선택 · 더블클릭 = 공문 열기 · 우클릭 = 메뉴 · Ctrl+N 공문 추가",
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
        self.status_items["clip"].config(text="📋 복사 분석 " + ("켜짐" if s.get("clip_watch") else "꺼짐"))
        self.status_items["alert"].config(text="⏰ 기한 알림 " + ("켜짐" if s.get("alerts_on", True) else "꺼짐"))

    def build_body(self):
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        side = ttk.Frame(body, width=380)               # 오른쪽 패널을 먼저 놓아야 달력이 남은 자리를 채운다
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)
        card = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(side="left", fill="both", expand=True)
        self.cal_frame = tk.Frame(card, bg=CARD)
        self.cal_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.nb = ttk.Notebook(side)
        self.nb.pack(fill="both", expand=True)

        # [선택한 날] 탭
        t1 = ttk.Frame(self.nb, padding=10)
        self.nb.add(t1, text=" 📌 선택한 날 ")
        ttk.Label(t1, textvariable=self.sel_var, style="Head.TLabel").pack(anchor="w")
        self.day_list = listbox(t1, height=5)
        self.day_list.pack(fill="x", pady=(6, 4))
        self.day_list.bind("<<ListboxSelect>>", lambda e: self.show_detail())
        self.day_list.bind("<Double-1>", lambda e: self.open_source())
        for b in ("<Button-3>", "<Button-2>"):          # 우클릭 (윈도우=Button-3, 맥=Button-2)
            self.day_list.bind(b, self.popup_from_list)
        btns = ttk.Frame(t1)
        btns.pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="✔ 완료", command=self.toggle_done).pack(side="left")
        ttk.Button(btns, text="📄 공문 열기", command=self.open_source).pack(side="left", padx=4)
        ttk.Button(btns, text="★ 실적", command=self.toggle_mine_current).pack(side="left")
        ttk.Button(btns, text="🗑", width=3, style="Danger.TButton", command=self.delete_event).pack(side="right")

        self.detail = tk.Text(t1, height=8, wrap="word", font=(FONT, 9), state="disabled", bg="#fafbfd", relief="flat",
                              highlightthickness=1, highlightbackground=BORDER, padx=6, pady=4)
        self.detail.pack(fill="x")
        ttk.Label(t1, text="☑ 회신 할 일  (누르면 체크)", font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 2))
        self.todo_list = listbox(t1, height=4, font=(FONT, 9))
        self.todo_list.pack(fill="x")
        self.todo_list.bind("<ButtonRelease-1>", self.on_todo_click)
        ttk.Label(t1, text="🔗 관련 공문  (더블클릭 = 이동)", font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 2))
        self.rel_list = listbox(t1, height=3, font=(FONT, 9))
        self.rel_list.pack(fill="both", expand=True)
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
        self.today = dt.date.today()
        self.title_var.set("%d년 %d월" % (self.year, self.month))
        self.update_team_label()
        for w in self.cal_frame.winfo_children():
            w.destroy()

        by_date = self.store.group_by_date()
        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(self.year, self.month)   # 일요일 시작
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
        for w in (self.status_win, self.ach_win, self.search_win, self.widget):   # 열려 있는 창도 같이 갱신
            if w is not None:
                w.refresh()
        self.update_statusbar()

    def update_team_label(self):
        team = core.team_for(self.today, self.settings)
        if team:
            self.team_var.set("오늘 근무 %d팀" % team)
            self.team_label.config(bg=TEAM_COLORS.get(team, "#7a4fd6"))
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

        head = tk.Frame(cell, bg=bg)                    # 맨 윗줄: 날짜(왼쪽) + 근무팀(오른쪽)
        head.pack(fill="x", pady=(2, 0))
        fg = "#b8bcc4" if not in_month else ("#c0392b" if col == 0 else ("#2f6fed" if col == 6 else "#1f2430"))
        if is_today:
            num = tk.Label(head, text=" %d " % day.day, font=(FONT, 9, "bold"), fg="#ffffff", bg=PRIMARY)
        else:
            num = tk.Label(head, text=str(day.day), font=(FONT, 9, "bold"), fg=fg, bg=bg, anchor="w")
        num.pack(side="left", padx=4)
        widgets = [cell, head, num]

        team = core.team_for(day, self.settings)
        if team:
            color = TEAM_COLORS.get(team, "#7a4fd6")
            mine = team == self.settings.get("my_team")
            tl = tk.Label(head, text="%d팀" % team, font=(FONT, 8, "bold"),
                          fg="#ffffff" if mine else color, bg=color if mine else bg, padx=3)
            tl.pack(side="right", padx=3)
            widgets.append(tl)

        for ev in events[:3]:                           # 칸에는 최대 3개까지만 보여 준다
            b, f = event_colors(ev, self.today)
            mark = ("✔ " if ev.get("done") else "") + ("★ " if ev.get("mine") else "")
            t = (ev["time"] + " " if ev.get("time") else "") + ev["title"]
            font = (FONT, 8, "overstrike") if ev.get("done") else (FONT, 8)      # 완료되면 가운데 줄
            lb = tk.Label(cell, text=mark + t, font=font, bg=b, fg=f, anchor="w", padx=3, cursor="hand2")
            lb.pack(fill="x", padx=3, pady=1)
            lb.bind("<Button-1>", lambda e, d=day, ev=ev: self.on_event_click(d, ev))          # 한 번 클릭 = 선택
            lb.bind("<Double-1>", lambda e, ev=ev: self.on_event_double(ev))                  # 더블클릭 = 공문 열기
            for b3 in ("<Button-3>", "<Button-2>"):                                           # 우클릭 = 메뉴
                lb.bind(b3, lambda e, ev=ev: self.popup_menu(e.x_root, e.y_root, ev))
        if len(events) > 3:
            more = tk.Label(cell, text="+%d건 더" % (len(events) - 3), font=(FONT, 8), fg=SUB, bg=bg, anchor="w")
            more.pack(fill="x", padx=4)
            widgets.append(more)
        for w in widgets:                               # 빈 곳을 누르면 그날만 선택, 더블클릭 = 그날로 공문 추가
            w.bind("<Button-1>", lambda e, d=day: self.select(d))

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
            line = "%s [%s] %s" % (ev.get("time") or "종일", ev.get("kind", ""), ev["title"])
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
            self.soon_list.insert("end", " %-6s  %s  %s" % (core.dday_text(n), ev["date"][5:], ev["title"]))
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
        ev = self.current_event()
        lines = []
        if ev:
            lines.append("제목: " + ev["title"])
            lines.append("일시: %s %s  (%s)" % (ev["date"], ev.get("time") or "종일", ev.get("kind", "")))
            n = core.dday(ev["date"], self.today)
            state = "처리 완료" + ((" (%s)" % ev["done_at"]) if ev.get("done_at") else "") if ev.get("done") else core.dday_text(n) + " · 미처리"
            lines.append("처리 상태: " + state)
            lines.append("내 실적: " + ("★ 포함" if ev.get("mine") else "아니오") + (("  · 메모: " + ev["note"]) if ev.get("note") else ""))
            if ev.get("doc_no") or ev.get("org"):
                lines.append("문서번호: %s%s" % (ev.get("doc_no", ""), ("  · 시행: " + ev["org"]) if ev.get("org") else ""))
            lines.append("저장된 공문: " + (os.path.basename(core.resolve_doc_path(ev) or "") or "없음"))
            if ev.get("attachments"):
                lines.append("붙임: " + " / ".join(ev["attachments"]))
            if ev.get("emails"):
                lines.append("메일: " + ", ".join(ev["emails"]))
            if ev.get("snippet"):
                lines.append("공문 속 문구: " + ev["snippet"])
        else:
            lines.append("이 날짜에는 일정이 없습니다.\n\n[＋ 공문 추가]를 누르거나, 공문 PDF를 이 창에 끌어다 놓으세요.")
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", "\n".join(lines))
        self.detail.config(state="disabled")

        self.todo_list.delete(0, "end")
        todos = (ev or {}).get("todos") or []
        for t in todos:
            self.todo_list.insert("end", ("☑ " + strike(t["text"])) if t.get("done") else ("☐ " + t["text"]))
            if t.get("done"):
                self.todo_list.itemconfig("end", fg="#8a8f98")
        if ev and not todos:
            self.todo_list.insert("end", "  (할 일 없음)")
            self.todo_list.itemconfig("end", fg="#9aa0aa")

        self.rel_events = core.related_events(self.store.events, ev) if ev else []
        self.rel_list.delete(0, "end")
        for e in self.rel_events:
            self.rel_list.insert("end", "%s  %s  %s" % (e["date"][5:], e.get("doc_no", ""), e["title"]))
        if ev and not self.rel_events:
            refs = ev.get("refs") or []
            self.rel_list.insert("end", ("  (달력에 없음: " + ", ".join(refs[:3]) + ")") if refs else "  (관련 공문 없음)")
            self.rel_list.itemconfig("end", fg="#9aa0aa")

    def on_todo_click(self, e):
        ev = self.current_event()
        if not ev or not ev.get("todos"):
            return
        i = self.todo_list.nearest(e.y)
        if 0 <= i < len(ev["todos"]):
            self.pending_select_id = ev["id"]
            self.store.toggle_todo(ev["id"], i)
            self.refresh()

    def on_rel_double(self, e):
        i = self.rel_list.nearest(e.y)
        if 0 <= i < len(self.rel_events):
            self.show_event(self.rel_events[i])

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
        """일정을 더블클릭하면 저장된 공문을 연다"""
        if self._click_job:
            self.root.after_cancel(self._click_job)
            self._click_job = None
        self.open_event_doc(ev)

    # ---- 우클릭 메뉴 -------------------------------------------------------
    def popup_menu(self, x, y, ev):
        m = self.menu
        m.delete(0, "end")
        m.add_command(label="📄 공문 열기", command=lambda: self.open_event_doc(ev))
        m.add_command(label="📅 달력에서 보기", command=lambda: self.show_event(ev))
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
        if messagebox.askyesno("삭제", "이 일정을 삭제할까요?\n%s\n(보관된 공문 파일은 지워지지 않습니다)" % ev["title"], parent=self.root):
            self.store.delete(ev["id"])
            self.refresh()

    def open_event_doc(self, ev):
        path = core.resolve_doc_path(ev)
        if not path:
            messagebox.showinfo("안내", "저장된 공문 파일을 찾지 못했습니다.\n(공문보관 폴더에서 옮기거나 지운 경우일 수 있어요)", parent=self.root)
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

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv", initialfile="업무처리현황.csv",
                                            filetypes=[("CSV 파일", "*.csv")])
        if path:
            core.export_csv(self.store.events, path)
            messagebox.showinfo("완료", "저장했습니다.\n엑셀에서 열 수 있습니다.", parent=self.root)

    # ---- 창 열기 ------------------------------------------------------------
    def open_add_dialog(self, prefill="", path=None):
        AddDialog(self, prefill, path=path)

    def open_batch(self, paths=()):
        BatchDialog(self, paths)

    def open_settings(self, tab="team"):
        SettingsDialog(self, tab)

    def open_team_settings(self):
        self.open_settings("team")

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

    def open_widget(self):
        if self.widget is not None:
            self.widget.win.lift()
            return
        self.widget = WidgetWindow(self)

    def open_status(self):
        if self.status_win is not None:
            self.status_win.win.lift()
            return
        self.status_win = StatusWindow(self)

    def on_drop(self, paths):
        """큰 달력 창에 파일을 끌어 놓으면: 하나면 공문 추가, 여러 개면 한꺼번에 등록"""
        files = gs.expand_paths(paths)
        if len(files) == 1:
            self.open_add_dialog(path=files[0])
        elif files:
            self.open_batch(files)

    def on_close_main(self):
        """위젯이 떠 있으면 큰 창만 숨기고 위젯은 계속 둔다"""
        if self.widget is not None:
            self.root.withdraw()
            Toast(self, "🧩 위젯은 계속 떠 있어요", "달력을 다시 보려면 위젯의 ▣ 를 누르세요.\n위젯을 닫으면 프로그램이 끝납니다.", timeout=6000)
        else:
            self.root.destroy()

    # ---- 설정 적용 -----------------------------------------------------------
    def apply_settings(self, first=False, share_changed=False):
        s = self.settings
        if share_changed:
            self.switch_store()
        dl = s.get("download_dir") or gs.default_download_dir()
        if s.get("watch_downloads") and os.path.isdir(dl):
            if self.watcher is None or self.watcher.folder != dl:
                self.watcher = gs.FolderWatcher(dl)     # 켤 때 이미 있던 파일은 무시
        else:
            self.watcher = None
        if s.get("clip_watch") and not getattr(self, "_clip_running", False):
            self.last_clip = self.read_clip()           # 지금 복사돼 있는 내용은 무시하고 '새로 복사'만 감시
            self._clip_running = True
            self.root.after(1000, self.poll_clipboard)
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
                items = core.due_alerts(self.store.events, dt.date.today(), s.get("alert_levels", [3, 1, 0]), alerted)
                if items:
                    for ev, lv in items:
                        alerted.setdefault(ev["id"], []).append(lv)
                    live = {e["id"] for e in self.store.events}
                    for k in [k for k in alerted if k not in live]:     # 지워진 일정 기록은 정리
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
                body = "%s\n%s %s · %s" % (ev["title"], ev["date"], ev.get("time") or "", ev.get("kind", ""))
                Toast(self, "⏰ %s (%s)" % (names[lv], lv if lv != "지남" else core.dday_text(core.dday(ev["date"], self.today))),
                      body, color=colors[lv], on_open=lambda ev=ev: self.show_event(ev))
        else:
            body = "\n".join("· %s %s" % (lv, ev["title"][:28]) for ev, lv in items[:4])
            if len(items) > 4:
                body += "\n· 외 %d건" % (len(items) - 4)
            Toast(self, "⏰ 기한 알림 %d건" % len(items), body, color="#c0392b",
                  on_open=lambda: (self.show_main(), self.nb.select(1)), timeout=30000)
        if self.widget is not None and self.settings.get("widget_flash", True):
            self.widget.flash()

    # ---- 복사하면 자동 분석 (클립보드 감시) ----------------------------------
    def read_clip(self):
        try:
            return self.root.clipboard_get()
        except tk.TclError:                             # 클립보드가 비었거나 글자가 아닐 때
            return ""

    def poll_clipboard(self):
        if not self.settings.get("clip_watch"):
            self._clip_running = False
            return
        text = self.read_clip()
        if text and text != self.last_clip:
            self.last_clip = text
            if len(text) > 100:                         # 너무 짧은 복사는 공문이 아니므로 무시
                res = core.analyze(text, lex=self.lex)
                if any(c["kind"] in ("기한", "애매") for c in res["candidates"]):
                    self.open_add_dialog(prefill=text)
        self.root.after(1000, self.poll_clipboard)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App(widget_only="--widget" in sys.argv).run()       # python gongmun_calendar.py --widget  : 위젯만 실행
