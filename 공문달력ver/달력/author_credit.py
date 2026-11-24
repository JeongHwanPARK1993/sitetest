# -*- coding: utf-8 -*-
"""
author_credit.py  -  만든이(제작자) 안내 (오른쪽 아래 '만든이: 박정환')

사용법 (메인 창을 만든 뒤 한 줄):
    import author_credit
    author_credit.add_author_credit(root, app_name="프로그램 이름")
    author_credit.add_author_credit(root, app_name="프로그램 이름", label="제작자")   # '제작자: 박정환'
"""
import tkinter as tk
from tkinter import ttk

AUTHOR = "박정환"
EMAIL = "hwan9876@korea.kr"
GREETING = "좋은 하루 되세요 ^^"
FONT = "맑은 고딕"


def add_author_credit(parent, app_name="", bg=None, label="만든이"):
    """창의 오른쪽 아래 구석에 작은 '만든이' 글자를 얹고, 누르면 안내 창을 띄운다.
    label: 구석에 보일 말 ("만든이" 또는 "제작자")"""
    if bg is None:
        try:
            bg = parent.cget("bg")                      # ttk 창이면 실패할 수 있어서 대비
        except tk.TclError:
            bg = "#f0f0f0"
    title = "%s: %s" % (label, AUTHOR)

    corner = tk.Label(parent, text=title, font=(FONT, 8), fg="#9a9a9a", bg=bg, cursor="hand2")
    corner.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-4)   # place 라서 다른 배치(pack/grid)를 건드리지 않음
    corner.lift()

    state = {"win": None}                               # 안내 창이 이미 열려 있는지 기억

    def on_enter(_e):
        corner.config(fg="#333333", font=(FONT, 8, "underline"))

    def on_leave(_e):
        corner.config(fg="#9a9a9a", font=(FONT, 8))

    def open_dialog(_e=None):
        win = state["win"]
        if win is not None and win.winfo_exists():     # 중복으로 열지 않기
            win.lift()
            return
        win = tk.Toplevel(parent)
        state["win"] = win
        win.title("%s 안내" % label)
        win.resizable(False, False)
        win.transient(parent)

        box = ttk.Frame(win, padding=18)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text=title, font=(FONT, 12, "bold")).pack(anchor="w")
        # tk.Label 을 쓰면 배경색이 창과 달라 보이므로 ttk.Label 에 글자색만 준다
        ttk.Label(box, text=GREETING, font=(FONT, 10), foreground="#2f6fed").pack(anchor="w", pady=(4, 10))

        row = ttk.Frame(box)
        row.pack(fill="x")
        mail_var = tk.StringVar(win, value=EMAIL)
        win.mail_var = mail_var                         # 꼭 붙잡아 둔다: 안 하면 변수가 사라져서 메일 칸이 빈칸으로 보인다
        entry = ttk.Entry(row, textvariable=mail_var, state="readonly", width=28)   # 읽기 전용, 드래그 선택 가능
        entry.pack(side="left")
        copy_btn = ttk.Button(row, text="복사하기")
        copy_btn.pack(side="left", padx=(6, 0))

        def copy_mail():
            win.clipboard_clear()
            win.clipboard_append(EMAIL)
            copy_btn.config(text="✔ 복사됨")             # 복사됐는지 눈으로 확인
            win.after(1500, lambda: copy_btn.winfo_exists() and copy_btn.config(text="복사하기"))

        copy_btn.config(command=copy_mail)

        name = app_name or "프로그램 이름"
        info = ("궁금한 점, 오류, 바라는 기능이 있으면 위 메일로 보내 주세요.\n"
                "메일 제목 앞에 [%s]를 적어 주시면 확인이 빠릅니다.\n"
                "오류는 어떤 파일로 무엇을 했는지 함께 알려 주세요." % name)
        ttk.Label(box, text=info, wraplength=340, justify="left").pack(anchor="w", pady=(12, 12))
        ttk.Button(box, text="닫기", command=win.destroy).pack(anchor="e")

        win.bind("<Escape>", lambda e: win.destroy())  # Esc 로 닫기
        win.update_idletasks()                          # 부모 창 가운데에 놓기
        x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
        win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        win.focus_set()

    corner.bind("<Enter>", on_enter)
    corner.bind("<Leave>", on_leave)
    corner.bind("<Button-1>", open_dialog)
    return corner
