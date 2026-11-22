"""공문 PDF 에서 제목 / 시행기관 / 시행일자를 읽어 새 파일명을 만든다 (공문 제목 바꾸기 프로그램에서 가져옴, 화면 없음).

온나라 등에서 '저장' 한 공문 PDF 는 글자가 들어 있는 PDF 라서,
추가 설치 없이 내장 모듈(gongmun_pdf)로 글자와 위치를 읽고 아래 두 곳을 찾는다.

  1쪽   제목 2026년 현장지휘관 ... 협조 요청          -> 제목
  끝쪽  시행 소방행정과-11072 (2026. 11. 16.) 접수 ... -> 시행기관 / 문서번호 / 시행일자

시행일자가 비어 있는 공문(시행 소방행정과-3181 접수)은 바로 위 결재란의
'전결 2026. 3. 11.' 같은 결재일을 대신 쓰고, 화면에 주황색으로 알려 준다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gongmun_pdf import Line, read_pdf_lines

# ---------------------------------------------------------------- 정규식
_DATE = r"\(\s*(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*\)"
# 시행 소방행정과-11072 (2026. 11. 16.)
_RE_SIHAENG = re.compile(r"시\s?행\s*([^\s()]+?)\s*-\s*(\d+)\s*" + _DATE)
# '시행' 글자와 값이 떨어져 추출될 때를 대비한 느슨한 형태
_RE_PAIR = re.compile(r"([^\s()]+?)\s*-\s*(\d+)\s*" + _DATE)
# 시행일자가 비어 있는 경우: 시행 소방행정과-3181 접수
_RE_SIHAENG_NODATE = re.compile(r"시\s?행\s*([^\s()]+?)\s*-\s*(\d+)")
# 결재란 날짜: 전결 2026. 3. 11.
_RE_SIGN_DATE = re.compile(r"(?:(전결|대결|결재|서명)\s*)?(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?")
_RE_TITLE_START = re.compile(r"\s*제\s?목\s*")
_RE_TITLE_STOP = re.compile(r"^\s*(\d+\s*\.\s|붙\s?임|끝\.?\s*$|[가-하]\.\s|수신|\(경유\))")

DATE_FORMATS = {
    "YYYY.MM.DD": "{y}.{m:02d}.{d:02d}",
    "YYYYMMDD": "{y}{m:02d}{d:02d}",
    "YYYY-MM-DD": "{y}-{m:02d}-{d:02d}",
    "YYMMDD": "{y2}{m:02d}{d:02d}",
}
DEFAULT_TEMPLATE = "{시행일자}_{제목}_{시행기관}"
OLD_TEMPLATES = ("{제목}_{시행기관}_{시행일자}",)   # 예전 기본값 - 저장돼 있으면 새 기본값으로 바꿈
DEFAULT_DATE_FORMAT = "YYYY.MM.DD"
MAX_NAME_LEN = 150  # 확장자 제외. 윈도우 경로 길이 제한(260자) 여유


@dataclass
class DocInfo:
    title: str = ""
    org: str = ""          # 시행기관 (예: 소방행정과)
    number: str = ""       # 문서번호 (예: 소방행정과-11072)
    year: int = 0
    month: int = 0
    day: int = 0
    notes: list[str] = field(default_factory=list)  # 확인이 필요한 점 (주황색 표시)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# ---------------------------------------------------------------- 분석
def analyze(path: str | Path) -> DocInfo:
    try:
        pages = read_pdf_lines(path)
    except Exception as e:  # 암호/손상 PDF 등
        return DocInfo(error=f"읽기 실패: {e}")
    return parse_lines(pages)


def parse_lines(pages: list[list[Line]]) -> DocInfo:
    """쪽별 줄 목록에서 제목/시행정보를 뽑는다. (파일을 열지 않는 순수 함수)"""
    info = DocInfo()
    if not any(pages):
        info.error = "글자가 없는 PDF (스캔/이미지)"
        return info

    for page in pages:
        title, n_lines = _find_title(page)
        if title:
            info.title = title
            if n_lines > 1:
                info.notes.append(f"제목 {n_lines}줄 - 띄어쓰기 확인")
            break

    page_texts = ["\n".join(ln.text for ln in page) for page in pages]
    _find_sihaeng(page_texts, info)

    missing = []
    if not info.title:
        missing.append("제목")
    if not info.org:
        missing.append("시행정보")
    if missing:
        info.error = " / ".join(missing) + " 못 찾음 (공문 PDF 가 아닐 수 있음)"
    return info


def _find_title(page: list[Line]) -> tuple[str, int]:
    """'제목' 줄을 찾고, 같은 들여쓰기로 이어지는 다음 줄까지 제목으로 본다.

    제목이 두 줄이면 둘째 줄은 제목 글자 시작 위치에 맞춰 들여쓰기 되고,
    본문은 '제목' 글자 위치(왼쪽 여백)에서 시작하므로 위치로 구분할 수 있다.
    """
    for i, ln in enumerate(page):
        m = _RE_TITLE_START.match(ln.text)
        if not m:
            continue
        rest = ln.text[m.end():].strip()
        label_x = ln.x0
        size = ln.size or 10.0
        parts: list[str] = []
        if rest:
            parts.append(rest)
            title_x = ln.xs[m.end()] if m.end() < len(ln.xs) else label_x + 3 * size
        else:
            title_x = None
            # 제목이 칸 가운데 정렬이라 첫 줄이 '제목' 글자보다 살짝 위에 있는 경우
            if i > 0:
                up = page[i - 1]
                if 0 < up.y - ln.y < 1.6 * size and up.x0 > label_x + size and not _RE_TITLE_STOP.match(up.text):
                    parts.append(up.text)
                    title_x = up.x0
        prev_y = ln.y
        for nxt in page[i + 1:i + 5]:
            if _RE_TITLE_STOP.match(nxt.text):
                break
            if prev_y - nxt.y > 2.4 * max(size, nxt.size):
                break  # 너무 멀리 떨어짐
            if title_x is None:
                if nxt.x0 > label_x + size:
                    title_x = nxt.x0
                else:
                    break
            elif nxt.x0 < title_x - 0.6 * nxt.size:
                break  # 왼쪽 여백에서 시작 -> 본문
            parts.append(nxt.text)
            prev_y = nxt.y
        title = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if title:
            return title, len(parts)
    return "", 0


def _find_sihaeng(page_texts: list[str], info: DocInfo) -> None:
    # 1) 날짜까지 있는 정상 형태 (뒤쪽 쪽부터)
    for txt in reversed(page_texts):
        flat = re.sub(r"\s+", " ", txt)
        m = _RE_SIHAENG.search(flat)
        if not m:
            for sm in re.finditer(r"시\s?행", flat):
                m = _RE_PAIR.search(flat, sm.end(), sm.end() + 80)
                if m:
                    break
        if m:
            org, num, y, mo, d = m.groups()
            _set(info, org, num, int(y), int(mo), int(d))
            return
    # 2) 시행일자가 빈 공문 -> 결재일 대신 사용
    for txt in reversed(page_texts):
        flat = re.sub(r"\s+", " ", txt)
        m = _RE_SIHAENG_NODATE.search(flat)
        if not m:
            continue
        org, num = m.groups()
        dates = list(_RE_SIGN_DATE.finditer(flat, max(0, m.start() - 600), m.start()))
        signed = [d for d in dates if d.group(1)]
        pick = (signed or dates)[-1] if dates else None
        if pick:
            _set(info, org, num, int(pick.group(2)), int(pick.group(3)), int(pick.group(4)))
            label = pick.group(1) or "결재"
            info.notes.append(f"시행일자 없음 - {label}일 사용")
        else:
            info.org, info.number = org, f"{org}-{num}"
            info.error = "시행일자 못 찾음"
        return


def _set(info: DocInfo, org: str, num: str, y: int, mo: int, d: int) -> None:
    info.org, info.number = org, f"{org}-{num}"
    info.year, info.month, info.day = y, mo, d


# ---------------------------------------------------------------- 이름 만들기
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def format_date(info: DocInfo, fmt_key: str) -> str:
    fmt = DATE_FORMATS.get(fmt_key, DATE_FORMATS[DEFAULT_DATE_FORMAT])
    if not (info.year and info.month and info.day):
        return ""
    return fmt.format(y=info.year, y2=info.year % 100, m=info.month, d=info.day)


def safe_name(text: str) -> str:
    text = _BAD.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip().rstrip(". ")
    return text


def build_name(info: DocInfo, template: str, date_fmt: str) -> str:
    """확장자(.pdf)를 뺀 새 이름. 너무 길면 제목 부분을 줄인다."""
    values = {
        "제목": info.title,
        "시행기관": info.org,
        "시행일자": format_date(info, date_fmt),
        "문서번호": info.number,
    }

    def render(title: str) -> str:
        out = template
        for k, val in dict(values, 제목=title).items():
            out = out.replace("{" + k + "}", safe_name(val))
        out = re.sub(r"_{2,}", "_", out).strip("_ ")   # 빈 값 때문에 생긴 __ / 앞뒤 _ 정리
        return safe_name(out)

    name = render(info.title)
    if len(name) > MAX_NAME_LEN and info.title:
        over = len(name) - MAX_NAME_LEN
        name = render(info.title[: max(10, len(info.title) - over - 1)].rstrip() + "…")
    return name


def unique_target(folder: Path, stem: str, source: Path | None = None) -> Path:
    """같은 이름이 이미 있으면 (2), (3) ... 을 붙인다. source 자신이면 그대로 쓴다."""
    cand = folder / f"{stem}.pdf"
    n = 2
    while cand.exists() and not (source and _same(cand, source)):
        cand = folder / f"{stem} ({n}).pdf"
        n += 1
    return cand


def _same(a: Path, b: Path) -> bool:
    try:
        return a.samefile(b)
    except OSError:
        return False


if __name__ == "__main__":  # 명령창에서 바로 확인: py gongmun_core.py 파일.pdf
    import sys

    for arg in sys.argv[1:]:
        inf = analyze(arg)
        print(arg, "->", inf.error or build_name(inf, DEFAULT_TEMPLATE, DEFAULT_DATE_FORMAT), inf.notes)
