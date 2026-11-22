# -*- coding: utf-8 -*-
"""
gongmun_calendar.py  -  공문 달력 (화면 부분)

실행:  python gongmun_calendar.py            (전체 화면)
       python gongmun_calendar.py --widget   (바탕화면 위젯만)

화면 구성
  [상단 바]  공문 추가 / 달 이동 / 오늘 근무팀 / 업무 현황 / 근무 설정 / .ics 내보내기
  [왼쪽]     월간 달력 (칸마다 근무팀 표시, 일정을 누르면 저장된 공문이 열린다)
  [오른쪽]   선택한 날짜의 일정 목록 + 상세 + 임박한 기한 목록

공문에서 기한을 찾는 규칙은 gongmun_core.py, 용어는 용어사전.txt 에 있습니다.
"""
import calendar
import datetime as dt
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import author_credit
import gongmun_core as core
import gongmun_rename as rn                        # 공문 PDF 에서 제목·시행기관·시행일자를 읽어 파일 이름을 만든다

FONT = "맑은 고딕"
KINDS = ["기한", "행사", "애매", "기타", "변경전"]
TEAM_COLORS = {1: "#2f6fed", 2: "#2e9d5b", 3: "#d98200"}      # 1팀 파랑 / 2팀 초록 / 3팀 주황


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
    return "".join(ch if ch.isspace() else ch + "\u0336" for ch in text)


def event_colors(ev, today):
    """일정 칸의 색: (배경, 글자). 완료=회색, 지남/당일=빨강, 3일 이내=노랑, 나머지=파랑"""
    if ev.get("done"):
        return "#e6e6e6", "#888888"
    n = core.dday(ev["date"], today)
    if n <= 0:
        return "#fde2e1", "#a12622"
    if n <= 3:
        return "#fff3cd", "#7a5b00"
    return "#e7f1ff", "#1f4e9c"


# ══════════════════════════════════════════════════════════════
#  공문 추가 창  (붙여넣기 / 파일 불러오기 → 분석 → 확인·수정 → 등록)
# ══════════════════════════════════════════════════════════════
class AddDialog:
    def __init__(self, app, prefill=""):
        self.app = app
        self.source = ""                                # 불러온 원본 파일 경로
        self.rows = []                                  # 기한 후보 한 줄 한 줄
        self.rename_info = None                         # PDF 에서 읽은 제목·시행정보 (rn.DocInfo)

        win = self.win = tk.Toplevel(app.root)
        win.title("공문 추가")
        win.geometry("860x830")
        win.transient(app.root)

        # ① 공문 내용 입력 칸
        top = ttk.LabelFrame(win, text="① 공문 내용을 붙여넣거나(Ctrl+V), 파일을 불러오세요", padding=8)
        top.pack(fill="x", padx=10, pady=(10, 4))
        self.text = tk.Text(top, height=10, wrap="word", font=(FONT, 10))
        self.text.pack(fill="x")
        btns = ttk.Frame(top)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="PDF / HWPX 불러오기", command=self.load_file).pack(side="left")
        ttk.Button(btns, text="분석하기", command=self.run_analyze).pack(side="left", padx=6)
        ttk.Label(btns, text="(파일 이름이 DOSDKML.pdf 처럼 알 수 없어도, 공문 속 '제목'을 자동으로 가져옵니다)",
                  foreground="#777").pack(side="left")

        # ② 분석 결과 (확인하고 고칠 수 있음)
        mid = ttk.LabelFrame(win, text="② 분석 결과 - 틀린 곳은 고치고, 달력에 올릴 것만 체크하세요", padding=8)
        mid.pack(fill="both", expand=True, padx=10, pady=4)

        info = ttk.Frame(mid)
        info.pack(fill="x")
        ttk.Label(info, text="제목").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(info, textvariable=self.title_var, width=80).grid(row=0, column=1, sticky="we", padx=6, pady=2)
        ttk.Label(info, text="문서번호").grid(row=1, column=0, sticky="w")
        self.docno_var = tk.StringVar()
        ttk.Entry(info, textvariable=self.docno_var, width=30).grid(row=1, column=1, sticky="w", padx=6, pady=2)
        info.columnconfigure(1, weight=1)

        head = ttk.Frame(mid)
        head.pack(fill="x", pady=(8, 0))
        for i, t in enumerate(["등록", "날짜(YYYY-MM-DD)", "시간(HH:MM)", "구분", "공문 속 원문"]):
            ttk.Label(head, text=t, font=(FONT, 9, "bold")).grid(row=0, column=i, sticky="w", padx=4)

        self.rows_frame = ttk.Frame(mid)
        self.rows_frame.pack(fill="x")
        ttk.Button(mid, text="+ 날짜 직접 추가", command=self.add_row).pack(anchor="w", pady=4)

        ttk.Label(mid, text="붙임 (한 줄에 하나)").pack(anchor="w")
        self.attach_text = tk.Text(mid, height=3, wrap="word", font=(FONT, 9))
        self.attach_text.pack(fill="x")
        self.extra = {"emails": [], "requests": []}      # 메일·요청 문장은 화면에 안 보이고 같이 저장만

        # 파일 이름 바꾸기 (공문 제목 바꾸기 기능)
        rf = ttk.LabelFrame(win, text="파일 이름 - 공문 PDF 의 제목·시행기관·시행일자로 새 이름을 만듭니다", padding=8)
        rf.pack(fill="x", padx=10, pady=4)
        s = app.settings
        self.name_var = tk.StringVar()
        self.tpl_var = tk.StringVar(value=s.get("rename_template", rn.DEFAULT_TEMPLATE))
        self.datefmt_var = tk.StringVar(value=s.get("rename_date_fmt", rn.DEFAULT_DATE_FORMAT))
        self.rename_orig = tk.BooleanVar(value=False)
        ttk.Label(rf, text="새 이름").grid(row=0, column=0, sticky="w")
        ttk.Entry(rf, textvariable=self.name_var).grid(row=0, column=1, sticky="we", padx=6, pady=2)
        ttk.Label(rf, text=".pdf").grid(row=0, column=2, sticky="w")
        ttk.Button(rf, text="이름 다시 만들기", command=self.make_name).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(rf, text="형식").grid(row=1, column=0, sticky="w")
        ttk.Entry(rf, textvariable=self.tpl_var, width=34).grid(row=1, column=1, sticky="w", padx=6, pady=2)
        ttk.Combobox(rf, textvariable=self.datefmt_var, values=list(rn.DATE_FORMATS), width=12,
                     state="readonly").grid(row=1, column=3, padx=(6, 0))
        self.name_note = ttk.Label(rf, text="", foreground="#b45309")
        self.name_note.grid(row=2, column=1, columnspan=3, sticky="w", padx=6)
        ttk.Checkbutton(rf, text="불러온 원본 파일 이름도 새 이름으로 바꾸기 (같은 폴더에서 이름만 바뀝니다)",
                        variable=self.rename_orig).grid(row=3, column=1, columnspan=3, sticky="w", padx=6, pady=(2, 0))
        ttk.Label(rf, text="형식에 쓸 수 있는 말: {시행일자} {제목} {시행기관} {문서번호}", foreground="#777").grid(
            row=4, column=1, columnspan=3, sticky="w", padx=6)
        rf.columnconfigure(1, weight=1)

        # ③ 등록
        bottom = ttk.Frame(win)
        bottom.pack(fill="x", padx=10, pady=10)
        ttk.Button(bottom, text="달력에 등록", command=self.register).pack(side="right")
        ttk.Button(bottom, text="닫기", command=win.destroy).pack(side="right", padx=6)

        if prefill:
            self.text.insert("1.0", prefill)
            self.run_analyze()

    # ---- 파일 불러오기 -------------------------------------------------
    def load_file(self):
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

    # ---- 파일 이름 만들기 -------------------------------------------------
    def read_rename_info(self, path):
        """PDF 면 제목·시행기관·시행일자를 읽어 새 파일 이름을 미리 채운다."""
        self.rename_info = None
        self.name_var.set("")
        self.name_note.config(text="")
        if os.path.splitext(path)[1].lower() != ".pdf":
            self.name_note.config(text="PDF 가 아니어서 이름은 [날짜_제목] 으로 보관합니다.")
            return
        info = rn.analyze(path)
        if not info.ok:
            self.name_note.config(text=info.error + " - 이름을 직접 적어 주세요.")
            return
        self.rename_info = info
        if info.title and info.title != self.title_var.get().strip():
            self.title_var.set(info.title)              # 제목은 시행정보까지 읽는 이 방식이 더 정확하다
        self.make_name(notes=info.notes)

    def make_name(self, notes=None):
        if self.rename_info is None:
            messagebox.showinfo("안내", "PDF 공문을 불러오면 새 이름을 만들 수 있습니다.\n직접 적으셔도 됩니다.", parent=self.win)
            return
        info = rn.DocInfo(**{**self.rename_info.__dict__, "title": self.title_var.get().strip() or self.rename_info.title})
        self.name_var.set(rn.build_name(info, self.tpl_var.get(), self.datefmt_var.get()))
        self.name_note.config(text=("확인 필요: " + " / ".join(notes)) if notes else "")

    # ---- 분석 ----------------------------------------------------------
    def run_analyze(self):
        body = self.text.get("1.0", "end")
        if not body.strip():
            messagebox.showinfo("안내", "공문 내용을 먼저 붙여넣어 주세요.", parent=self.win)
            return
        result = core.analyze(body, lex=self.app.lex)
        self.title_var.set(result["title"])             # ← 공문 속 '제목'이 자동으로 들어간다
        self.docno_var.set(result["doc_no"])
        self.attach_text.delete("1.0", "end")
        self.attach_text.insert("1.0", "\n".join(result["attachments"]))
        self.extra = {"emails": result["emails"], "requests": result["requests"]}

        for r in self.rows:                             # 이전 결과 지우기
            r["widgets"].destroy()
        self.rows = []
        for cd in result["candidates"]:
            self.add_row(cd)
        if not result["candidates"]:
            messagebox.showinfo("안내", "날짜를 찾지 못했습니다.\n[+ 날짜 직접 추가]로 입력하실 수 있어요.", parent=self.win)

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
        ttk.Checkbutton(frame, variable=r["check"]).grid(row=0, column=0, padx=4)
        ttk.Entry(frame, textvariable=r["date"], width=16).grid(row=0, column=1, padx=4)
        ttk.Entry(frame, textvariable=r["time"], width=10).grid(row=0, column=2, padx=4)
        ttk.Combobox(frame, textvariable=r["kind"], values=KINDS, width=6, state="readonly").grid(row=0, column=3, padx=4)
        ttk.Label(frame, text=r["snippet"], wraplength=420, foreground="#555").grid(row=0, column=4, padx=4, sticky="w")
        self.rows.append(r)

    # ---- 등록 ----------------------------------------------------------
    def register(self):
        title = self.title_var.get().strip() or "(제목 없음)"
        attachments = [a.strip() for a in self.attach_text.get("1.0", "end").splitlines() if a.strip()]
        new_events = []
        for r in self.rows:
            if not r["check"].get():
                continue
            try:                                        # '2026.11.25' 처럼 점으로 써도 받아 준다
                d = dt.date.fromisoformat(r["date"].get().strip().replace(".", "-").replace("/", "-").strip("-"))
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
            new_events.append({
                "date": d.isoformat(), "time": tm, "kind": r["kind"].get(), "title": title,
                "doc_no": self.docno_var.get().strip(), "attachments": attachments,
                "requests": self.extra["requests"], "emails": self.extra["emails"],
                "snippet": r["snippet"], "source": self.source,
            })
        if not new_events:
            messagebox.showinfo("안내", "달력에 올릴 날짜를 체크해 주세요.", parent=self.win)
            return

        stem = rn.safe_name(self.name_var.get().replace(".pdf", "")) or None     # 새 파일 이름 (없으면 [날짜_제목])
        if stem and self.rename_orig.get() and self.source and os.path.isfile(self.source):
            folder = os.path.dirname(self.source)       # 원본 파일도 같은 폴더에서 새 이름으로 바꾼다
            try:
                target = rn.unique_target(Path(folder), stem, source=Path(self.source))
                if str(target) != self.source:
                    os.rename(self.source, target)
                    self.source = str(target)
                    for ev in new_events:
                        ev["source"] = self.source
            except OSError as e:
                messagebox.showwarning("이름 바꾸기 실패", "원본 파일 이름을 바꾸지 못했습니다.\n(열려 있는 파일인지 확인해 주세요)\n%s" % e, parent=self.win)
        self.app.settings["rename_template"] = self.tpl_var.get()
        self.app.settings["rename_date_fmt"] = self.datefmt_var.get()
        core.save_settings(self.app.settings)

        # 공문 사본을 '공문보관' 폴더에 새 파일 이름으로 한 번만 저장하고, 모든 일정이 같은 파일을 가리키게 한다
        try:
            doc_file = core.archive_document(self.source, self.text.get("1.0", "end"), title, new_events[0]["date"], stem=stem)
        except OSError as e:
            doc_file = ""
            messagebox.showwarning("보관 실패", "공문 사본을 보관하지 못했습니다.\n일정만 등록합니다.\n%s" % e, parent=self.win)
        for ev in new_events:
            ev["file"] = doc_file
            self.app.store.add(ev)
        self.app.go_to(dt.date.fromisoformat(new_events[0]["date"]))
        self.win.destroy()
        messagebox.showinfo("등록 완료", "%d건을 달력에 등록했습니다.\n공문 사본: %s" % (len(new_events), doc_file or "없음"),
                            parent=self.app.root)


# ══════════════════════════════════════════════════════════════
#  근무 설정 창 (3교대 팀 순서)
# ══════════════════════════════════════════════════════════════
class TeamSettingsDialog:
    def __init__(self, app):
        self.app = app
        st = app.settings
        win = self.win = tk.Toplevel(app.root)
        win.title("근무 설정")
        win.transient(app.root)
        win.resizable(False, False)
        box = ttk.Frame(win, padding=16)
        box.pack()

        ttk.Label(box, text="3교대 근무팀 순서를 알려 주세요", font=(FONT, 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="기준일 (그날 근무한 팀을 알고 있는 날)").grid(row=1, column=0, sticky="w", pady=(10, 2))
        self.date_var = tk.StringVar(value=st.get("anchor_date") or dt.date.today().isoformat())
        ttk.Entry(box, textvariable=self.date_var, width=14).grid(row=1, column=1, padx=8)
        ttk.Label(box, text="기준일부터 돌아가는 순서").grid(row=2, column=0, sticky="w", pady=2)
        self.pattern_var = tk.StringVar(value=",".join(str(n) for n in st.get("pattern", [1, 2, 3])))
        ttk.Entry(box, textvariable=self.pattern_var, width=14).grid(row=2, column=1, padx=8)
        ttk.Label(box, text="내 팀 (내 근무일을 진하게 표시)").grid(row=3, column=0, sticky="w", pady=2)
        self.my_var = tk.StringVar(value=("%d팀" % st["my_team"]) if st.get("my_team") else "없음")
        ttk.Combobox(box, textvariable=self.my_var, values=["없음", "1팀", "2팀", "3팀"], width=8, state="readonly").grid(row=3, column=1, padx=8, sticky="w")
        ttk.Label(box, justify="left", foreground="#666", text=(
            "예) 기준일(2026-11-19)에 2팀이 근무했고, 다음날 3팀, 그다음 날 1팀이면\n"
            "    기준일: 2026-11-19 / 순서: 2,3,1\n"
            "하루에 한 팀씩 돌아가는 방식이 아니면 순서를 길게 적으면 됩니다.\n"
            "    예) 2일씩 근무: 1,1,2,2,3,3")).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 6))
        row = ttk.Frame(box)
        row.grid(row=5, column=0, columnspan=2, sticky="e")
        ttk.Button(row, text="저장", command=self.save).pack(side="right")
        ttk.Button(row, text="취소", command=win.destroy).pack(side="right", padx=6)

    def save(self):
        try:
            anchor = dt.date.fromisoformat(self.date_var.get().strip().replace(".", "-").replace("/", "-"))
            pattern = core.parse_pattern(self.pattern_var.get())
        except ValueError as e:
            messagebox.showwarning("입력 확인", "기준일은 YYYY-MM-DD 형식으로, 순서는 1,2,3 처럼 적어 주세요.\n%s" % e, parent=self.win)
            return
        my = self.my_var.get()
        self.app.settings = {"anchor_date": anchor.isoformat(), "pattern": pattern,
                             "my_team": int(my[0]) if my[:1].isdigit() else 0}
        core.save_settings(self.app.settings)
        self.win.destroy()
        self.app.refresh()


# ══════════════════════════════════════════════════════════════
#  업무 처리 현황 창 (했는지 / 안 했는지 한눈에)
# ══════════════════════════════════════════════════════════════
class StatusWindow:
    FILTERS = ["미처리", "기한초과", "완료", "전체"]

    def __init__(self, app):
        self.app = app
        win = self.win = tk.Toplevel(app.root)
        win.title("업무 처리 현황")
        win.geometry("1000x540")
        win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self.close)

        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        self.filter_var = tk.StringVar(value="미처리")
        for name in self.FILTERS:
            ttk.Radiobutton(top, text=name, value=name, variable=self.filter_var, command=self.refresh).pack(side="left", padx=4)
        self.sum_var = tk.StringVar()
        ttk.Label(top, textvariable=self.sum_var, font=(FONT, 10, "bold")).pack(side="right")

        cols = ("state", "mine", "kind", "date", "time", "title", "docno", "done_at")
        self.tree = ttk.Treeview(win, columns=cols, show="headings", height=16)
        for col, text, width in zip(cols, ["상태", "실적", "구분", "기한일", "시간", "공문 제목", "문서번호", "완료일"],
                                    [90, 40, 60, 95, 55, 420, 130, 90]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8)
        self.tree.tag_configure("late", foreground="#a12622")
        self.tree.tag_configure("soon", foreground="#7a5b00")
        self.tree.tag_configure("done", foreground="#888888", font=(FONT, 9, "overstrike"))   # 완료 = 가운데 줄
        self.tree.bind("<Double-1>", lambda e: self.open_doc())
        for b in ("<Button-3>", "<Button-2>"):
            self.tree.bind(b, self.on_right_click)

        bar = ttk.Frame(win, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="완료 처리 / 되돌리기", command=self.toggle).pack(side="left")
        ttk.Button(bar, text="공문 열기", command=self.open_doc).pack(side="left", padx=6)
        ttk.Button(bar, text="달력에서 보기", command=self.goto).pack(side="left")
        ttk.Button(bar, text="CSV(엑셀)로 저장", command=self.export).pack(side="right")
        ttk.Label(bar, text="(더블클릭 = 공문 열기)", foreground="#777").pack(side="right", padx=10)
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
        for iid in self.tree.get_children():
            self.tree.delete(iid)
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
                                     ev["title"], ev.get("doc_no", ""), ev.get("done_at", "")))

    def current(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("안내", "목록에서 업무를 먼저 선택해 주세요.", parent=self.win)
            return None
        for ev in self.app.store.events:
            if ev["id"] == sel[0]:
                return ev
        return None

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
        for ev in self.app.store.events:
            if ev["id"] == iid:
                self.app.popup_menu(e.x_root, e.y_root, ev)

    def open_doc(self):
        ev = self.current()
        if ev:
            self.app.open_event_doc(ev)

    def goto(self):
        ev = self.current()
        if ev:
            self.app.go_to(dt.date.fromisoformat(ev["date"]))
            self.app.root.lift()

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
        win.transient(app.root)
        box = ttk.Frame(win, padding=12)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text=ev["title"], font=(FONT, 10, "bold"), wraplength=420).pack(anchor="w")
        ttk.Label(box, text="내가 한 일 / 역할 / 성과를 적어 두세요. (자기역량기술서에 그대로 붙여넣을 수 있어요)",
                  foreground="#666").pack(anchor="w", pady=(4, 6))
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

        tip = ttk.Label(win, foreground="#777", padding=(8, 2),
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
        for ev in self.app.store.events:
            if ev["id"] == sel[0]:
                return ev
        return None

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
#  메인 창 (달력)
# ══════════════════════════════════════════════════════════════
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
        self.show_main()
        self.app.pending_select_id = ev["id"]
        self.app.go_to(dt.date.fromisoformat(ev["date"]))

    def show_main(self):
        self.app.root.deiconify()
        self.app.root.lift()

    def close(self):
        if self._job:
            self.win.after_cancel(self._job)
        self.save_cfg()
        self.win.destroy()
        self.app.widget = None
        if self.app.widget_only and not self.app.root.winfo_viewable():
            self.app.root.destroy()                     # 위젯만 켠 상태에서 닫으면 프로그램 종료


class App:
    def __init__(self, widget_only=False):
        self.root = tk.Tk()
        self.root.title("공문 달력")
        self.root.geometry("1180x740")
        self.store = core.Store(core.data_path("공문일정.json"))
        self.lex = core.load_lexicon(core.data_path("용어사전.txt"))
        self.settings = core.load_settings()
        self.today = dt.date.today()
        self.year, self.month = self.today.year, self.today.month
        self.selected = self.today
        self.day_events = []                            # 오른쪽 목록에 보이는 일정들
        self.soon_events = []
        self.status_win = None
        self.ach_win = None
        self.widget = None
        self.widget_only = widget_only
        self._click_job = None                          # 단일 클릭/더블 클릭을 구분하기 위한 예약
        self.pending_select_id = None                   # 클릭한 일정을 오른쪽 목록에서 선택해 두기 위함
        self.last_clip = ""
        self.watch_var = tk.BooleanVar(value=False)
        self.title_var = tk.StringVar()
        self.sel_var = tk.StringVar()
        self.team_var = tk.StringVar()

        self.menu = tk.Menu(self.root, tearoff=0)       # 우클릭 메뉴
        self.build_top()
        self.build_body()
        self.refresh()
        author_credit.add_author_credit(self.root, app_name="공문 달력")
        if widget_only:                                 # 위젯만 띄우기: 큰 달력 창은 숨겨 둔다
            self.root.withdraw()
            self.open_widget()

    # ---- 화면 만들기 -----------------------------------------------------
    def build_top(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=8)
        ttk.Button(bar, text="＋ 공문 추가", command=self.open_add_dialog).pack(side="left")
        ttk.Button(bar, text="◀", width=3, command=lambda: self.move_month(-1)).pack(side="left", padx=(20, 2))
        ttk.Label(bar, textvariable=self.title_var, font=(FONT, 15, "bold"), width=11, anchor="center").pack(side="left")
        ttk.Button(bar, text="▶", width=3, command=lambda: self.move_month(1)).pack(side="left", padx=2)
        ttk.Button(bar, text="오늘", command=lambda: self.go_to(dt.date.today())).pack(side="left", padx=10)
        self.team_label = tk.Label(bar, textvariable=self.team_var, font=(FONT, 12, "bold"), fg="#ffffff", bg="#999999", padx=10, pady=2)
        self.team_label.pack(side="left", padx=10)

        ttk.Button(bar, text=".ics 내보내기", command=self.export_ics).pack(side="right")
        ttk.Button(bar, text="🧩 위젯", command=self.open_widget).pack(side="right", padx=6)
        ttk.Button(bar, text="⚙ 근무 설정", command=self.open_team_settings).pack(side="right", padx=6)
        ttk.Button(bar, text="📋 업무 현황", command=self.open_status).pack(side="right")
        ttk.Button(bar, text="★ 내 실적 정리", command=self.open_achievements).pack(side="right", padx=6)
        ttk.Checkbutton(bar, text="복사하면 자동 분석", variable=self.watch_var,
                        command=self.toggle_watch).pack(side="right", padx=14)

    def build_body(self):
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 22))   # 아래쪽 여백 = 만든이 글자 자리

        self.cal_frame = ttk.Frame(body)
        self.cal_frame.pack(side="left", fill="both", expand=True)

        side = ttk.Frame(body, width=350)
        side.pack(side="right", fill="y", padx=(10, 0))
        side.pack_propagate(False)

        ttk.Label(side, textvariable=self.sel_var, font=(FONT, 11, "bold")).pack(anchor="w")
        self.day_list = tk.Listbox(side, height=6, font=(FONT, 10), exportselection=False)
        self.day_list.pack(fill="x", pady=4)
        self.day_list.bind("<<ListboxSelect>>", lambda e: self.show_detail())
        self.day_list.bind("<Double-1>", lambda e: self.open_source())
        for b in ("<Button-3>", "<Button-2>"):          # 우클릭 (윈도우=Button-3, 맥=Button-2)
            self.day_list.bind(b, self.popup_from_list)

        self.detail = tk.Text(side, height=12, wrap="word", font=(FONT, 9), state="disabled", bg="#fafafa")
        self.detail.pack(fill="x")

        btns = ttk.Frame(side)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="처리 완료/되돌리기", command=self.toggle_done).pack(side="left")
        ttk.Button(btns, text="공문 열기", command=self.open_source).pack(side="left", padx=4)
        ttk.Button(btns, text="삭제", command=self.delete_event).pack(side="left")

        ttk.Label(side, text="임박한 기한 (14일 이내, 지난 것 포함)", font=(FONT, 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.soon_list = tk.Listbox(side, height=8, font=(FONT, 9), exportselection=False)
        self.soon_list.pack(fill="both", expand=True, pady=4)
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
            color = "#c0392b" if i == 0 else ("#2f6fed" if i == 6 else "#333333")
            tk.Label(self.cal_frame, text=name, font=(FONT, 10, "bold"), fg=color).grid(row=0, column=i, pady=2)

        for r, week in enumerate(weeks, start=1):
            self.cal_frame.rowconfigure(r, weight=1, uniform="week")
            for c, day in enumerate(week):
                self.draw_day(day, r, c, by_date.get(day.isoformat(), []))

        self.refresh_side()
        if self.status_win is not None:                 # 업무 현황 창이 열려 있으면 같이 갱신
            self.status_win.refresh()
        if self.ach_win is not None:
            self.ach_win.refresh()
        if self.widget is not None:                     # 위젯도 같이 갱신
            self.widget.refresh()

    def update_team_label(self):
        team = core.team_for(self.today, self.settings)
        if team:
            self.team_var.set("오늘 근무: %d팀" % team)
            self.team_label.config(bg=TEAM_COLORS.get(team, "#7a4fd6"))
        else:
            self.team_var.set("근무팀 미설정 (⚙ 근무 설정)")
            self.team_label.config(bg="#999999")

    def draw_day(self, day, row, col, events):
        in_month = day.month == self.month
        is_sel = day == self.selected
        bg = "#fffbe6" if day == self.today else ("#ffffff" if in_month else "#f4f4f4")
        cell = tk.Frame(self.cal_frame, bg=bg, highlightthickness=2 if is_sel else 1,
                        highlightbackground="#2f6fed" if is_sel else "#cccccc")
        cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

        head = tk.Frame(cell, bg=bg)                    # 맨 윗줄: 날짜(왼쪽) + 근무팀(오른쪽)
        head.pack(fill="x")
        fg = "#aaaaaa" if not in_month else ("#c0392b" if col == 0 else ("#2f6fed" if col == 6 else "#222222"))
        num = tk.Label(head, text=str(day.day), font=(FONT, 9, "bold"), fg=fg, bg=bg, anchor="w")
        num.pack(side="left", padx=3)
        widgets = [cell, head, num]

        team = core.team_for(day, self.settings)
        if team:
            color = TEAM_COLORS.get(team, "#7a4fd6")
            mine = team == self.settings.get("my_team")
            tl = tk.Label(head, text="%d팀" % team, font=(FONT, 8, "bold"),
                          fg="#ffffff" if mine else color, bg=color if mine else bg, padx=3)
            tl.pack(side="right", padx=2)
            widgets.append(tl)

        for ev in events[:3]:                           # 칸에는 최대 3개까지만 보여 준다
            b, f = event_colors(ev, self.today)
            mark = ("✔ " if ev.get("done") else "") + ("★ " if ev.get("mine") else "")
            t = (ev["time"] + " " if ev.get("time") else "") + ev["title"]
            font = (FONT, 8, "overstrike") if ev.get("done") else (FONT, 8)      # 완료되면 가운데 줄
            lb = tk.Label(cell, text=mark + t, font=font, bg=b, fg=f, anchor="w", padx=2, cursor="hand2")
            lb.pack(fill="x", padx=2, pady=1)
            lb.bind("<Button-1>", lambda e, d=day, ev=ev: self.on_event_click(d, ev))          # 한 번 클릭 = 선택
            lb.bind("<Double-1>", lambda e, ev=ev: self.on_event_double(ev))                  # 더블클릭 = 공문 열기
            for b3 in ("<Button-3>", "<Button-2>"):                                           # 우클릭 = 메뉴
                lb.bind(b3, lambda e, ev=ev: self.popup_menu(e.x_root, e.y_root, ev))
        if len(events) > 3:
            more = tk.Label(cell, text="+%d건 더" % (len(events) - 3), font=(FONT, 8), fg="#666666", bg=bg, anchor="w")
            more.pack(fill="x", padx=3)
            widgets.append(more)
        for w in widgets:                               # 빈 곳을 누르면 그날만 선택
            w.bind("<Button-1>", lambda e, d=day: self.select(d))

    # ---- 오른쪽 패널 -----------------------------------------------------
    def refresh_side(self):
        d = self.selected
        team = core.team_for(d, self.settings)
        self.sel_var.set("%d월 %d일 (%s)%s" % (d.month, d.day, "월화수목금토일"[d.weekday()],
                                               ("  근무 %d팀" % team) if team else ""))
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
            self.soon_list.insert("end", "%s  %s  %s" % (core.dday_text(n), ev["date"][5:], ev["title"]))

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
            if ev.get("doc_no"):
                lines.append("문서번호: " + ev["doc_no"])
            lines.append("저장된 공문: " + (os.path.basename(core.resolve_doc_path(ev) or "") or "없음"))
            if ev.get("attachments"):
                lines.append("붙임: " + " / ".join(ev["attachments"]))
            if ev.get("requests"):
                lines.append("요청: " + " ".join(ev["requests"]))
            if ev.get("emails"):
                lines.append("메일: " + ", ".join(ev["emails"]))
            if ev.get("snippet"):
                lines.append("공문 속 문구: " + ev["snippet"])
        else:
            lines.append("이 날짜에는 일정이 없습니다.")
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", "\n".join(lines))
        self.detail.config(state="disabled")

    def jump_to_soon(self, _e):
        sel = self.soon_list.curselection()
        if sel and sel[0] < len(self.soon_events):
            self.go_to(dt.date.fromisoformat(self.soon_events[sel[0]]["date"]))

    # ---- 동작 ------------------------------------------------------------
    def select(self, day):
        self.selected = day
        if (day.year, day.month) != (self.year, self.month):
            self.year, self.month = day.year, day.month
        self.refresh()

    def go_to(self, day):
        self.select(day)

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
        self.store.toggle_done(ev["id"])
        self.refresh()

    def set_mine_toggle(self, ev):
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

    def delete_event(self):
        ev = self.current_event()
        if ev:
            self.delete_given(ev)

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

    def open_add_dialog(self, prefill=""):
        AddDialog(self, prefill)

    def open_team_settings(self):
        TeamSettingsDialog(self)

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

    # ---- 복사하면 자동 분석 (클립보드 감시) ----------------------------------
    def toggle_watch(self):
        if self.watch_var.get():
            self.last_clip = self.read_clip()           # 지금 복사돼 있는 내용은 무시하고 '새로 복사'만 감시
            self.root.after(1000, self.poll_clipboard)

    def read_clip(self):
        try:
            return self.root.clipboard_get()
        except tk.TclError:                             # 클립보드가 비었거나 글자가 아닐 때
            return ""

    def poll_clipboard(self):
        if not self.watch_var.get():
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
