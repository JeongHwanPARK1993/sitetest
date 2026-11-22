# -*- coding: utf-8 -*-
"""
gongmun_core.py  -  공문에서 '기한'을 찾아내는 핵심 부분 (화면 없음)

이 파일은 화면(tkinter)과 상관없이 돌아가는 '두뇌'입니다.
  1) 글자 정리      : 공백/특수문자 때문에 생기는 문제를 없앤다
  2) 날짜 찾기      : 2026. 11. 25.(수) 18:00 같은 날짜·시간을 찾는다
  3) 기한 판단      : 날짜 근처의 용어(제출기한, 까지 ...)로 '기한인지 행사인지' 판단한다
  4) 파일 읽기      : PDF / HWPX / TXT 에서 글자를 꺼낸다
  5) 저장           : 일정을 JSON 파일에 저장한다, .ics 로 내보낸다

용어는 같은 폴더의 '용어사전.txt' 에 있습니다. 코드를 안 고치고 그 파일만 고치면 됩니다.
"""
import datetime as dt
import csv
import json
import os
import re
import shutil
import sys
import unicodedata
import uuid
import zipfile
import xml.etree.ElementTree as ET


# ──────────────────────────────────────────────────────────────
# 0. 파일 위치 (exe 로 만들어도, 그냥 실행해도 '프로그램이 있는 폴더'를 쓴다)
# ──────────────────────────────────────────────────────────────
def data_path(filename):
    if getattr(sys, "frozen", False):          # PyInstaller 로 만든 exe 일 때
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


# ──────────────────────────────────────────────────────────────
# 1. 용어사전 (기본값). 파일이 없으면 이 내용으로 '용어사전.txt'를 만들어 준다
# ──────────────────────────────────────────────────────────────
DEFAULT_LEXICON_TEXT = """\
# ===== 용어사전 =====
# - 한 줄에 용어 하나만 적으세요.
# - 띄어쓰기는 신경 쓰지 마세요. ('제출 기한', '제 출 기 한' 모두 자동 인식)
# - '#'으로 시작하는 줄은 메모입니다.
# - 새 표현을 발견하면 알맞은 [분류] 아래에 한 줄만 추가하면 끝!

[기한용어]
# 날짜 '앞'에 이런 말이 있으면 -> 기한(마감)으로 봅니다
제출기한
회신기한
보고기한
접수기한
신청기한
제출기일
회신기일
마감일
마감
기한
기일
제출일
회신일
신청기간
접수기간
제출기간
회신기간

[행사용어]
# 날짜 '앞'에 이런 말이 있으면 -> 행사/교육 일정으로 봅니다
일시
일정
교육일시
교육일정
행사일시
교육기간
운영기간
행사기간
훈련일시
훈련기간
개최일
개최
실시일
실시
시행일
회의일시

[애매용어]
# 기한일 수도, 행사일 수도 있는 말 -> '확인 필요'로 보여 줍니다
기간
일자
날짜

[문서날짜용어]
# 공문 자체의 날짜(머리말) -> 일정에 올리지 않습니다 (연도 계산에만 사용)
시행
기안
작성
결재
접수
생산
공개
등록

[기한뒤말]
# 날짜 '뒤'에 바로 이런 말이 붙으면 -> 기한으로 봅니다
까지
이내
마감
"""

SECTION_TO_KIND = {"기한용어": "기한", "행사용어": "행사", "애매용어": "애매", "문서날짜용어": "문서"}


def _strip_ws(s):
    """모든 공백(전각 공백, 탭 포함)을 없앤다."""
    return "".join(ch for ch in s if not ch.isspace())


def load_lexicon(path=None):
    """용어사전.txt 를 읽어서 {'labels': [(용어, 종류)...], 'after': [..]} 로 돌려준다."""
    path = path or data_path("용어사전.txt")
    if not os.path.exists(path):                       # 처음 실행: 기본 사전 파일을 만들어 준다
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_LEXICON_TEXT)
        except OSError:
            pass
        text = DEFAULT_LEXICON_TEXT
    else:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()

    labels, after, section = [], [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        word = _strip_ws(line)                          # 사전의 용어도 공백 제거해서 보관
        if section in SECTION_TO_KIND:
            labels.append((word, SECTION_TO_KIND[section]))
        elif section == "기한뒤말":
            after.append(word)
    return {"labels": labels, "after": after}


# ──────────────────────────────────────────────────────────────
# 2. 글자 정리: '비교용 사본'을 만든다 (공백 제거 + 비슷한 기호 통일)
#    예)  '기    간 :  2026. 11. 25.'  ->  '기간:2026.11.25.'
#    (줄바꿈만은 '\n' 으로 남긴다: 앞 줄 끝 숫자와 다음 줄 날짜가 붙어 버리는 것을 막기 위해)
#    원래 글자 위치를 기억해 두어서, 나중에 화면에는 원본 문장을 보여 줄 수 있다.
# ──────────────────────────────────────────────────────────────
_ZERO_WIDTH = "\u200b\u200c\u200d\ufeff"
_PUNCT_FIX = {"∼": "~", "〜": "~", "～": "~", "–": "-", "—": "-", "‐": "-", "－": "-", "：": ":"}


def compact_with_map(text):
    out, idx_map = [], []
    for i, ch in enumerate(text):
        if ch in "\r\n\v\f":                           # 줄바꿈은 '\n' 으로 남겨 둔다
            if out and out[-1] != "\n":
                out.append("\n")
                idx_map.append(i)
            continue
        if ch.isspace() or ch in _ZERO_WIDTH:
            continue
        for o in unicodedata.normalize("NFKC", ch):     # 전각 숫자/기호를 보통 글자로
            out.append(_PUNCT_FIX.get(o, o))
            idx_map.append(i)
    return "".join(out), idx_map


# ──────────────────────────────────────────────────────────────
# 3. 날짜·시간 찾기 (공백이 이미 없는 '비교용 글자'에서 찾는다)
# ──────────────────────────────────────────────────────────────
FULL_RE = re.compile(r"(?<!\d)(?P<y>(?:19|20)\d{2})[.\-/년]\n?(?P<m>\d{1,2})[.\-/월]\n?(?P<d>\d{1,2})(?:일|\.)?")
SHORT_Y_RE = re.compile(r"['’‘´`](?P<y>\d{2})[.\-/년](?P<m>\d{1,2})[.\-/월](?P<d>\d{1,2})(?:일|\.)?")
MD_KOR_RE = re.compile(r"(?<!\d)(?P<m>\d{1,2})월(?P<d>\d{1,2})일")
MD_DOT_RE = re.compile(r"(?<![\d/])(?P<m>\d{1,2})\.(?P<d>\d{1,2})\.?")
WEEKDAY_RE = re.compile(r"\([월화수목금토일]\)")
TIME_RE = re.compile(r"(?P<ap>오전|오후)?(?P<h>\d{1,2})(?:[:](?P<mi>\d{2})|시(?:(?P<mi2>\d{1,2})분)?)")


def _skip_nl(c, pos):
    """줄바꿈('\n')을 건너뛴 위치. (날짜 다음 줄에 시간/까지가 이어지는 공문이 많다)"""
    while pos < len(c) and c[pos] == "\n":
        pos += 1
    return pos


def _parse_time(c, pos):
    """pos 위치에서 시간을 읽는다. 성공하면 ('18:00', 끝위치), 실패하면 (None, pos)"""
    pos = _skip_nl(c, pos)
    if c.startswith(",", pos):                          # '(수),18:00' 같은 경우
        pos2 = _skip_nl(c, pos + 1)
    else:
        pos2 = pos
    m = TIME_RE.match(c, pos2)
    if not m:
        return None, pos
    h = int(m.group("h"))
    mi = int(m.group("mi") or m.group("mi2") or 0)
    if m.group("ap") == "오후" and h < 12:
        h += 12
    if m.group("ap") == "오전" and h == 12:
        h = 0
    if h > 24 or mi > 59:
        return None, pos
    if h == 24:
        h = 23; mi = 59
    return "%02d:%02d" % (h, mi), m.end()


def _match_one_date(c, pos):
    """pos 위치에서 날짜 하나(+요일+시간)를 읽는다. 없으면 None."""
    for rx in (FULL_RE, SHORT_Y_RE, MD_KOR_RE, MD_DOT_RE):
        m = rx.match(c, pos)
        if not m:
            continue
        gd = m.groupdict()
        end = m.end()
        # '11.25.' 처럼 점으로만 쓴 날짜는 '1.2항' 같은 번호와 헷갈리므로
        # 뒤에 (요일) / 시간 / 까지 / ~ 가 붙을 때만 날짜로 인정한다
        if rx is MD_DOT_RE:
            before = c[max(0, pos - 6):pos]
            if re.search(r"\d\.$", before) and not re.search(r"(^|\n)\d{1,2}\.$", before):
                continue                                # 숫자 나열(1.2.3.)이지만, 줄 맨 앞 번호('2.')는 예외
            tail = c[_skip_nl(c, end):]
            if not (WEEKDAY_RE.match(tail) or TIME_RE.match(tail) or tail.startswith(("까지", "~", "부터"))):
                continue
        month, day = int(gd["m"]), int(gd["d"])
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        year = None
        if gd.get("y"):
            year = int(gd["y"])
            if year < 100:
                year += 2000                            # '26. 11. 25. -> 2026
        wm = WEEKDAY_RE.match(c, _skip_nl(c, end))      # (수) 건너뛰기
        if wm:
            end = wm.end()
        tm, tend = _parse_time(c, end)                  # 18:00 읽기
        if tm:
            end = tend
        return {"y": year, "m": month, "d": day, "time": tm, "end": end}
    return None


def _parse_date_group(c, pos):
    """날짜 하나, 또는 '시작 ~ 끝' 기간을 읽는다."""
    first = _match_one_date(c, pos)
    if not first:
        return None
    group = {"start": pos, "end": first["end"], "first": first, "last": None}
    e = _skip_nl(c, first["end"])
    linked = False                                      # '~' 나 '부터' 로 이어졌을 때만 '기간'으로 본다
    if c.startswith("부터", e):                          # '11.20.부터 11.25.까지'
        e = _skip_nl(c, e + 2)
        linked = True
    if e < len(c) and c[e] in "~-":
        e = _skip_nl(c, e + 1)
        linked = True
    if linked and e < len(c):
        second = _match_one_date(c, e)
        if second:
            group["last"] = second
            group["end"] = second["end"]
    return group


def _make_date(y, m, d):
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


# ──────────────────────────────────────────────────────────────
# 4. 공문 분석 (이 파일의 핵심 함수)
# ──────────────────────────────────────────────────────────────
TITLE_RE = re.compile(r"^\s*제\s*목\s*[:：\-]?\s*(.*)$")
ATTACH_RE = re.compile(r"^\s*붙\s*임\s*[:：]?\s*(.*)$")
EMAIL_RE = re.compile(r"[\w.\-]+@[\w.\-]+\.[A-Za-z]{2,}")
DOCNO_RE = re.compile(r"[가-힣]{2,15}-\d{1,6}")


# 제목 다음 줄이 이런 모양으로 시작하면 '새 항목'이므로 제목의 연속이 아니다
_NEW_ITEM_RE = re.compile(r"^\s*(\d+\s*[.)]|[가-힣]\s*[.)]|[○●※▶■□◦·ㆍ\-]|붙\s*임|관\s*련|수\s*신|참\s*조|\()")


def _find_title(lines):
    for i, line in enumerate(lines):
        m = TITLE_RE.match(line)
        if m:
            t = m.group(1).strip()
            rest = lines[i + 1:]
            if not t:                                   # '제목' 글자만 있는 줄이면 다음 줄이 제목
                while rest and not rest[0].strip():
                    rest = rest[1:]
                if not rest:
                    return ""
                t, rest = rest[0].strip(), rest[1:]
            for nxt in rest[:3]:                        # PDF에서 줄이 꺾인 제목 이어 붙이기 (최대 3줄)
                if not nxt.strip() or _NEW_ITEM_RE.match(nxt):
                    break
                t += " " + nxt.strip()
            return re.sub(r"\s+", " ", t)
    for line in lines:                                  # 못 찾으면 첫 줄
        if line.strip():
            return line.strip()[:80]
    return ""


def _find_attachments(lines):
    res = []
    for i, line in enumerate(lines):
        m = ATTACH_RE.match(line)
        if not m:
            continue
        first = m.group(1).strip()
        if first:
            res.append(first)
        for nxt in lines[i + 1:]:                       # '2. 서식 1부' 처럼 번호로 이어지는 줄
            if re.match(r"^\s*\d+\s*[.)]\s*\S", nxt):
                res.append(nxt.strip())
            else:
                break
    cleaned = []
    for a in res:
        a = re.sub(r"\s*끝\.?\s*$", "", a).strip()      # 맨 뒤 '끝.' 제거
        if a and a not in cleaned:
            cleaned.append(a)
    return cleaned


def _find_requests(lines):
    """'~제출하여 주시기 바랍니다' 같은 요청 문장 (최대 4개)"""
    res = []
    for line in lines:
        c = _strip_ws(line)
        if ("바랍니다" in c or "협조" in c) and any(w in c for w in ("제출", "회신", "보고", "송부", "신청", "접수", "참석")):
            res.append(re.sub(r"\s+", " ", line.strip())[:120])
        if len(res) >= 4:
            break
    return res


def _label_is_close(kind, gap):
    """용어와 날짜 사이 글자(gap)가 충분히 가까운가.
    - 일반 용어: 10글자 이내  (예: '제출기한을', '기간:', '○제출기한\n-')
    - 문서날짜 용어(시행/접수): 머리말은 '시행 소방행정과-1234 (' 처럼 문서번호가 끼므로 번호가 있으면 30글자까지"""
    if kind == "문서":
        return len(gap) <= 4 or (re.search(r"-\d", gap) is not None and len(gap) <= 30)
    return len(gap) <= 10


def _nearest_label(window, labels):
    """window 글자 안에서 '가장 가까운(오른쪽 끝에 붙은)' 용어를 찾는다. 같으면 더 긴 용어."""
    best = None            # (끝위치, 길이, 종류, 용어)
    for word, kind in labels:
        idx = window.rfind(word)
        if idx >= 0:
            cand = (idx + len(word), len(word), kind, word)
            if best is None or cand[:2] > best[:2]:
                best = cand
    return best


def analyze(text, lex=None, today=None):
    """공문 글자 -> 제목/문서번호/붙임/기한 후보 등을 돌려준다."""
    lex = lex or load_lexicon()
    today = today or dt.date.today()
    lines = text.splitlines()
    c, idx_map = compact_with_map(text)
    n = len(c)

    # (1) 날짜 덩어리를 전부 찾는다
    groups, pos = [], 0
    while pos < n:
        if c[pos].isdigit() or c[pos] in "'’‘´`":
            g = _parse_date_group(c, pos)
            if g:
                groups.append(g)
                pos = g["end"]
                continue
        pos += 1

    # (2) 각 날짜 앞의 용어를 보고 종류(기한/행사/애매/문서/기타)를 정한다
    prev_end = 0
    for g in groups:
        window = c[max(prev_end, g["start"] - 25): g["start"]]
        hit = _nearest_label(window, lex["labels"])
        if hit and not _label_is_close(hit[2], window[hit[0]:]):
            hit = None                                  # 너무 멀리 있는 용어는 무시
        g["label_kind"] = hit[2] if hit else None
        g["label_word"] = hit[3] if hit else ""
        nxt = _skip_nl(c, g["end"])
        g["after_deadline"] = any(c.startswith(w, nxt) for w in lex["after"])
        g["after_old"] = c.startswith("에서", nxt)       # '~에서 ~로 변경/연장' 의 앞 날짜
        prev_end = g["end"]

    # (3) 공문 자체 날짜(시행일 등)를 찾아 '연도 계산 기준'으로 쓴다
    doc_date = None
    for g in groups:
        f = g["first"]
        if g["label_kind"] == "문서" and f["y"]:
            doc_date = _make_date(f["y"], f["m"], f["d"])
            if doc_date:
                break
    base = doc_date or today

    # (4) 후보 목록 만들기
    candidates, seen = [], set()
    for g in groups:
        f, l = g["first"], g["last"]
        if g["label_kind"] == "문서":
            continue                                    # 문서 자체 날짜는 일정에 안 올린다
        y1 = f["y"] or base.year
        start = _make_date(y1, f["m"], f["d"])
        if start and not f["y"] and (start - base).days < -180:      # 연도 생략 + 해를 넘긴 경우
            start = _make_date(y1 + 1, f["m"], f["d"])
        if not start:
            continue
        end, tm = start, f["time"]
        if l:
            y2 = l["y"] or start.year
            end = _make_date(y2, l["m"], l["d"])
            if end and not l["y"] and end < start:
                end = _make_date(y2 + 1, l["m"], l["d"])
            if not end:
                end = start
            tm = l["time"] or f["time"]

        kind = g["label_kind"]
        if g["after_deadline"] and kind in (None, "애매", "기한"):
            kind = "기한"                                # '~까지' 가 붙으면 기한
        if g["after_old"]:
            kind = "변경전"                              # 연장·변경 전의 옛 날짜 (체크 안 함)
        if kind is None:
            kind = "기타"
        pick = start if kind == "행사" else end         # 행사는 시작일, 기한은 종료일에 올린다

        key = (pick, kind, tm)
        if key in seen:
            continue
        seen.add(key)
        o_s = idx_map[g["start"]]
        o_e = idx_map[min(g["end"], n) - 1] + 1
        snippet = re.sub(r"\s+", " ", text[max(0, o_s - 25): o_e + 15]).strip()
        candidates.append({
            "kind": kind, "date": pick, "start_date": start, "end_date": end,
            "time": tm or "", "label": g["label_word"], "snippet": snippet, "checked": kind == "기한",
        })

    if candidates and not any(cd["checked"] for cd in candidates):
        for cd in candidates:                           # 기한이 하나도 없으면 '애매'를 미리 체크
            if cd["kind"] == "애매":
                cd["checked"] = True

    # (5) 나머지 항목
    doc_no = ""
    for line in lines[:30]:
        m = DOCNO_RE.search(line)
        if m:
            doc_no = m.group(0)
            break
    return {
        "title": _find_title(lines), "doc_no": doc_no, "doc_date": doc_date,
        "attachments": _find_attachments(lines), "requests": _find_requests(lines),
        "emails": list(dict.fromkeys(EMAIL_RE.findall(text))), "candidates": candidates,
    }


# ──────────────────────────────────────────────────────────────
# 5. 파일에서 글자 꺼내기
# ──────────────────────────────────────────────────────────────
def read_pdf_text(path):
    try:
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        except ImportError:
            raise RuntimeError("PDF를 읽으려면 pypdf 설치가 필요합니다.\n명령창에서:  pip install pypdf")
    if not text.strip():
        raise RuntimeError("PDF에서 글자를 읽지 못했습니다. (스캔한 그림 PDF일 수 있습니다)")
    return text


def read_hwpx_text(path):
    """HWPX 는 zip 파일 속 XML 이라서 별도 프로그램 없이 읽을 수 있다."""
    parts = []
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n))
        if not names:
            raise RuntimeError("HWPX 안에서 본문을 찾지 못했습니다.")
        for name in names:
            root = ET.fromstring(z.read(name))
            for el in root.iter():
                tag = el.tag.split("}")[-1]
                if tag == "p":
                    parts.append("\n")                  # 문단이 시작되면 줄바꿈
                elif tag == "t":
                    parts.append("".join(el.itertext()))
    return re.sub(r"\n{2,}", "\n", "".join(parts)).strip()


def read_file_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return read_pdf_text(path)
    if ext == ".hwpx":
        return read_hwpx_text(path)
    if ext == ".txt":
        for enc in ("utf-8-sig", "cp949"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise RuntimeError("텍스트 파일 인코딩을 읽지 못했습니다.")
    if ext == ".hwp":
        raise RuntimeError("옛날 형식(.hwp)은 아직 지원하지 않습니다.\nHWPX로 저장하거나, 본문을 복사해서 붙여넣어 주세요.")
    raise RuntimeError("지원하지 않는 파일 형식입니다: " + ext)


# ──────────────────────────────────────────────────────────────
# 6. 일정 저장소 (JSON 파일 한 개)
# ──────────────────────────────────────────────────────────────
class Store:
    def __init__(self, path):
        self.path = path
        self.events = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.events = json.load(f)
        except FileNotFoundError:
            self.events = []
        except (json.JSONDecodeError, OSError):         # 파일이 깨졌으면 백업해 두고 새로 시작
            try:
                os.replace(self.path, self.path + ".bak")
            except OSError:
                pass
            self.events = []

    def save(self):
        tmp = self.path + ".tmp"                        # 임시 파일에 쓴 뒤 바꿔치기 (저장 중 꺼져도 안전)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def add(self, ev):
        ev.setdefault("id", uuid.uuid4().hex)
        ev.setdefault("done", False)
        self.events.append(ev)
        self.save()

    def delete(self, ev_id):
        self.events = [e for e in self.events if e["id"] != ev_id]
        self.save()

    def toggle_done(self, ev_id):
        for e in self.events:
            if e["id"] == ev_id:
                e["done"] = not e.get("done", False)
                e["done_at"] = dt.date.today().isoformat() if e["done"] else ""   # 완료한 날짜 기록
        self.save()

    def toggle_mine(self, ev_id):
        """'내 실적'(자기역량기술서에 쓸 업무) 표시를 켜고 끈다"""
        for e in self.events:
            if e["id"] == ev_id:
                e["mine"] = not e.get("mine", False)
        self.save()

    def set_note(self, ev_id, note):
        """내가 한 역할·성과 메모"""
        for e in self.events:
            if e["id"] == ev_id:
                e["note"] = note
        self.save()

    def group_by_date(self):
        res = {}
        for e in sorted(self.events, key=lambda e: (e["date"], e.get("time") or "")):
            res.setdefault(e["date"], []).append(e)
        return res

    def upcoming(self, today, days=14):
        limit = (today + dt.timedelta(days=days)).isoformat()
        evs = [e for e in self.events if not e.get("done") and e["date"] <= limit]
        return sorted(evs, key=lambda e: (e["date"], e.get("time") or ""))


def dday(date_iso, today):
    """오늘이면 0, 내일이면 1, 어제면 -1"""
    return (dt.date.fromisoformat(date_iso) - today).days


def dday_text(n):
    return "D-day" if n == 0 else ("D-%d" % n if n > 0 else "D+%d" % -n)


# ──────────────────────────────────────────────────────────────
# 7. .ics 내보내기 (구글캘린더·아웃룩에서 '가져오기'로 불러올 수 있는 표준 파일)
# ──────────────────────────────────────────────────────────────
def _ics_escape(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def export_ics(events, path):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//gongmun-calendar//KO", "CALSCALE:GREGORIAN"]
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    for e in events:
        d = dt.date.fromisoformat(e["date"])
        summary = "[%s] %s" % (e.get("kind", ""), e.get("title", ""))
        desc = "\n".join(x for x in (
            ("문서번호: " + e["doc_no"]) if e.get("doc_no") else "",
            ("붙임: " + " / ".join(e["attachments"])) if e.get("attachments") else "",
        ) if x)
        lines += ["BEGIN:VEVENT", "UID:%s@gongmun" % e["id"], "DTSTAMP:" + stamp, "SUMMARY:" + _ics_escape(summary)]
        if e.get("time"):
            h, m = map(int, e["time"].split(":"))
            start = dt.datetime(d.year, d.month, d.day, h, m)
            lines += ["DTSTART:" + start.strftime("%Y%m%dT%H%M%S"),
                      "DTEND:" + (start + dt.timedelta(minutes=30)).strftime("%Y%m%dT%H%M%S")]
        else:                                           # 시간이 없으면 '종일' 일정
            lines += ["DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
                      "DTEND;VALUE=DATE:" + (d + dt.timedelta(days=1)).strftime("%Y%m%d")]
        if desc:
            lines.append("DESCRIPTION:" + _ics_escape(desc))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")


# ──────────────────────────────────────────────────────────────
# 8. 3교대 근무팀 계산 + 설정 (설정.json)
#    '패턴'은 기준일부터 하루에 한 칸씩 돌아가는 근무팀 목록입니다.
#    예) 패턴 [1,2,3] , 기준일에 1팀 근무 -> 기준일 1팀, 다음날 2팀, 그다음 3팀, 다시 1팀 ...
# ──────────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {"anchor_date": "", "pattern": [1, 2, 3], "my_team": 0}


def load_settings():
    st = dict(DEFAULT_SETTINGS)
    try:
        with open(data_path("설정.json"), "r", encoding="utf-8") as f:
            st.update(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return st


def save_settings(st):
    with open(data_path("설정.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def parse_pattern(text):
    """'1,2,3' 또는 '1 2 3' -> [1,2,3]  (잘못되면 ValueError)"""
    nums = [int(x) for x in re.split(r"[\s,]+", text.strip()) if x]
    if not nums or any(n < 1 or n > 9 for n in nums):
        raise ValueError("패턴은 1~9 사이 숫자를 쉼표로 적어 주세요. 예: 1,2,3")
    return nums


def team_for(day, st):
    """그날 근무하는 팀 번호. 기준일이 설정되지 않았으면 None"""
    try:
        anchor = dt.date.fromisoformat(st.get("anchor_date", ""))
    except ValueError:
        return None
    pattern = st.get("pattern") or []
    if not pattern:
        return None
    return pattern[(day - anchor).days % len(pattern)]


# ──────────────────────────────────────────────────────────────
# 9. 공문 보관: 불러온 공문(PDF 등)을 '공문보관' 폴더에 [날짜_제목] 이름으로 복사
#    (온나라에서 받은 DOSDKML.pdf 같은 이름이 공문 제목으로 바뀐다)
# ──────────────────────────────────────────────────────────────
def safe_filename(name, maxlen=60):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:maxlen].strip(" .") or "공문"


def archive_document(source, text, title, date_iso, stem=None):
    """공문 사본을 보관하고 '프로그램 폴더 기준 상대경로'를 돌려준다.
    stem 이 있으면 그 이름(확장자 제외)으로 저장하고, 없으면 [날짜_제목] 으로 저장한다."""
    folder = data_path("공문보관")
    os.makedirs(folder, exist_ok=True)
    has_file = bool(source) and os.path.isfile(source)
    ext = (os.path.splitext(source)[1] if has_file else "") or ".txt"
    base = safe_filename(stem, 150) if stem else "%s_%s" % (date_iso, safe_filename(title))
    dest, n = os.path.join(folder, base + ext), 2
    while os.path.exists(dest):                         # 같은 이름이 있으면 _2, _3 ...
        dest = os.path.join(folder, "%s_%d%s" % (base, n, ext))
        n += 1
    if has_file:
        shutil.copy2(source, dest)
    else:                                               # 붙여넣기로 넣은 공문은 글자 파일로 보관
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
    return os.path.join("공문보관", os.path.basename(dest))


def resolve_doc_path(ev):
    """일정에 연결된 공문 파일의 실제 경로 (없으면 None)"""
    for key in ("file", "source"):
        v = ev.get(key)
        if v:
            p = v if os.path.isabs(v) else data_path(v)
            if os.path.isfile(p):
                return p
    return None


def export_csv(events, path):
    """업무 처리 현황을 엑셀에서 열 수 있는 CSV 로 저장"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["상태", "구분", "날짜", "시간", "제목", "문서번호", "완료일", "붙임"])
        for e in sorted(events, key=lambda e: (e["date"], e.get("time") or "")):
            w.writerow(["완료" if e.get("done") else "미처리", e.get("kind", ""), e["date"], e.get("time", ""),
                        e.get("title", ""), e.get("doc_no", ""), e.get("done_at", ""),
                        " / ".join(e.get("attachments", []))])


# ──────────────────────────────────────────────────────────────
# 10. 내 실적 정리 (근무성적평정·자기역량기술서용)
#     기준 날짜 = 완료한 날(done_at), 없으면 공문 기한일
# ──────────────────────────────────────────────────────────────
def achievement_date(ev):
    return ev.get("done_at") or ev["date"]


def in_period(ev, year, half):
    """half: '상반기'(1~6월) / '하반기'(7~12월) / '연간' / '전체'"""
    if half == "전체":
        return True
    d = dt.date.fromisoformat(achievement_date(ev))
    if d.year != year:
        return False
    if half == "상반기":
        return d.month <= 6
    if half == "하반기":
        return d.month >= 7
    return True


def achievement_text(events, title=""):
    """선택한 실적들을 자기역량기술서에 붙여넣기 좋은 글로 만든다"""
    evs = sorted(events, key=achievement_date)
    out = [title] if title else []
    for i, e in enumerate(evs, 1):
        d = dt.date.fromisoformat(achievement_date(e))
        line = "%d. %d. %d. %d. %s" % (i, d.year, d.month, d.day, e.get("title", ""))
        if e.get("doc_no"):
            line += " (%s)" % e["doc_no"]
        out.append(line)
        if e.get("note"):
            out.append("   - " + e["note"].replace("\n", "\n     "))
    return "\n".join(out)
