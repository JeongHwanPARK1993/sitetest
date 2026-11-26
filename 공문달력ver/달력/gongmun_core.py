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
import filecmp
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


_SHARED_DIR = ""                                        # 팀 공유 폴더 (비어 있으면 프로그램 폴더)


def set_shared_dir(path):
    """일정 파일(공문일정.json)과 공문정리 폴더를 둘 곳을 정한다. 빈 값이면 프로그램 폴더."""
    global _SHARED_DIR
    _SHARED_DIR = path if path and os.path.isdir(path) else ""
    return _SHARED_DIR


def shared_path(filename):
    return os.path.join(_SHARED_DIR, filename) if _SHARED_DIR else data_path(filename)


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
시한
제출시한
회신시한
보고시한
납부기한
납기
납부일
완료기한
완료일
조치기한
이행기한
통보기한
송부기한
추천기한
응모기한
등록기한
제출마감
접수마감
신청마감
회신마감
마감일시
조사기한
검토기한
의견제출기한
회신요청일
제출요청일
보고일
까지제출

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
회의일
개최일시
행사일정
행사일
교육일
교육시간
시험일
시험일시
면접일
면접일시
심사일
심사일시
발표일
발표일시
평가일
평가일시
점검일
점검일시
시상식
개강일
개강
입교일
입교
수료일
연수일정
연수기간
연수일시
워크숍
설명회
간담회
회의
행사
교육
훈련
대회
참석일시
참석일
방문일
방문일시
출장일
출장기간
근무일
당직일
휴무일
소집일
총회
세미나
토론회
공청회
예행연습
리허설
전달식
임명식
감사패

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
이전
전까지
한하여
기한
한제출
한회신
제출
회신
보고
신청
송부
통보
납부
완료
도래
시까지

[행사뒤말]
# 날짜 '뒤'에 바로 이런 말이 붙으면 -> 행사로 봅니다  (예: '12. 12.(토) 10:00 입교')
개최
입교
개강
실시
개막
시작
진행
열립니다
개최예정
예정
참석
방문
"""

SECTION_TO_KIND = {"기한용어": "기한", "행사용어": "행사", "애매용어": "애매", "문서날짜용어": "문서"}

# 용어사전.txt 에 [행사뒤말] 이 없는 예전 사전도 쓸 수 있게 기본값을 둔다
_DEFAULT_AFTER_EVENT = ["개최", "입교", "개강", "실시", "개막", "시작", "진행", "열립니다", "개최예정", "예정", "참석", "방문"]

# 날짜 앞에 이런 말이 붙어 있으면 '12. 9.' 처럼 뒤에 아무것도 없어도 날짜로 본다
_BARE_DATE_HINT = re.compile(r"(기한|시한|기일|마감일?|일시|일정|기간|일자|날짜|제출일|회신일|시험일|발표일|납기|납부일|완료일|보고일|까지|~|부터|:|및|,|·|와|과|또는|\()$")


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

    labels, after, after_ev, section = [], [], [], None
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
        elif section == "행사뒤말":
            after_ev.append(word)
    return {"labels": labels, "after": after, "after_event": after_ev or _DEFAULT_AFTER_EVENT}


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
MD_SLASH_RE = re.compile(r"(?<![\d/])(?P<m>\d{1,2})/(?P<d>\d{1,2})(?![\d/])")
YY_DOT_RE = re.compile(r"(?<![\d])(?P<y>2\d)\.(?P<m>\d{1,2})\.(?P<d>\d{1,2})\.?(?![\d])")
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


_AFTER_OK = ("까지", "~", "부터", "이내", "이전", "전까지", "한하여", "로연장", "로변경", "로조정", "으로연장", "으로변경", "으로조정",
             "로수정", "로단축", "로앞당", "로연기", "로미룹", "에서", "마감", "제출", "회신", "접수", "신청")


def _match_one_date(c, pos, allow_bare=False):
    """pos 위치에서 날짜 하나(+요일+시간)를 읽는다. 없으면 None."""
    for rx in (FULL_RE, SHORT_Y_RE, YY_DOT_RE, MD_KOR_RE, MD_SLASH_RE, MD_DOT_RE):
        m = rx.match(c, pos)
        if not m:
            continue
        gd = m.groupdict()
        end = m.end()
        if rx is YY_DOT_RE or rx is MD_SLASH_RE:        # '26.12.5.' / '12/10' 은 뒤에 요일·시간·까지가 붙을 때만 날짜로 본다
            tail = c[_skip_nl(c, end):]
            if not (WEEKDAY_RE.match(tail) or TIME_RE.match(tail) or tail.startswith(_AFTER_OK)
                    or _BARE_DATE_HINT.search(c[max(0, pos - 6):pos])):
                continue
        # '11.25.' 처럼 점으로만 쓴 날짜는 '1.2항' 같은 번호와 헷갈리므로
        # 뒤에 (요일) / 시간 / 까지 / ~ 가 붙을 때만 날짜로 인정한다
        if rx is MD_DOT_RE:
            before = c[max(0, pos - 6):pos]
            if re.search(r"\d\.$", before) and not re.search(r"(^|\n)\d{1,2}\.$", before):
                continue                                # 숫자 나열(1.2.3.)이지만, 줄 맨 앞 번호('2.')는 예외
            tail = c[_skip_nl(c, end):]
            if tail.startswith(")") and c[max(0, pos - 1):pos] == "(":
                tail = tail[1:]                         # '(12. 2.)까지'
            if not (WEEKDAY_RE.match(tail) or TIME_RE.match(tail) or tail.startswith(_AFTER_OK)
                    or _BARE_DATE_HINT.search(c[max(0, pos - 6):pos]) or allow_bare):
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
        second = _match_one_date(c, e, allow_bare=True)      # '12. 1. ~ 12. 7.' 처럼 기간의 끝 날짜는 뒤에 아무것도 없어도 인정
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
ATTACH_RE = re.compile(r"^\s*붙\s*임(?!\s*(?:과|와|의|을|에|으로|같이|\d*\s*서식에))\s*[:：]?\s*(.*)$")   # "붙임과 같이 …" 는 붙임 목록이 아님
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
        if re.match(r"^(하여|하고|하여서|해서|한|하는|하신|하며|하기)", gap):
            return False                                # '작성하여 11.23.까지' 는 문서 날짜가 아니라 할 일의 기한
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


_WD = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
_REL_WEEK = re.compile(r"(?P<w>금주|이번주|금번주|차주|다음주|차차주|다다음주)(?:중)?(?P<d>[월화수목금토일])(?:요일)?")
_REL_DAY = re.compile(r"(?P<w>금일|오늘|내일|익일|명일|모레|명후일)(?:중|내)?")
_REL_WITHIN = re.compile(r"(?P<n>\d{1,3})(?P<u>일|주)(?:이내|내에|이내에|안에)")
_REL_DAYS = {"금일": 0, "오늘": 0, "내일": 1, "익일": 1, "명일": 1, "모레": 2, "명후일": 2}
_REL_WEEKS = {"금주": 0, "이번주": 0, "금번주": 0, "차주": 1, "다음주": 1, "차차주": 2, "다다음주": 2}
_DEADLINE_WORDS = ("까지", "이내", "마감", "정오", "이전", "전까지", "중", "내")
_REQUEST_WORDS = ("접수", "수령", "통보", "공문", "시행", "회신", "제출", "보고", "신청", "송부", "조치", "완료")


def _snippet_at(text, idx_map, c_start, c_end):
    n = len(idx_map)
    o_s = idx_map[min(c_start, n - 1)]
    o_e = idx_map[min(c_end, n) - 1] + 1
    return re.sub(r"\s+", " ", text[max(0, o_s - 25): o_e + 15]).strip()


def _relative_candidates(c, idx_map, text, base):
    """말로 쓴 기한을 날짜로 바꾼다. base = 공문 날짜(없으면 오늘)"""
    out = []
    monday = base - dt.timedelta(days=base.weekday())
    for m in _REL_WEEK.finditer(c):
        after = c[m.end():m.end() + 6]
        tm, tend = _parse_time(c, m.end()) if not after.startswith(_DEADLINE_WORDS) else (None, m.end())
        if not (after.startswith(_DEADLINE_WORDS) or tm):
            continue                                    # '금주 금요일' 뒤에 까지·시간이 없으면 기한이 아니다
        d = monday + dt.timedelta(weeks=_REL_WEEKS[m.group("w")], days=_WD[m.group("d")])
        out.append({"kind": "기한", "date": d, "start_date": d, "end_date": d, "time": "", "label": m.group("w"),
                    "snippet": _snippet_at(text, idx_map, m.start(), m.end() + 3), "checked": True, "pos": m.start()})
    for m in _REL_DAY.finditer(c):
        after = c[m.end():m.end() + 6]
        if not after.startswith(_DEADLINE_WORDS + ("12", "13", "14", "15", "16", "17", "18")) and m.group(0)[-1] not in "중내":
            continue
        d = base + dt.timedelta(days=_REL_DAYS[m.group("w")])
        out.append({"kind": "기한", "date": d, "start_date": d, "end_date": d, "time": "", "label": m.group("w"),
                    "snippet": _snippet_at(text, idx_map, m.start(), m.end() + 3), "checked": True, "pos": m.start()})
    for m in _REL_WITHIN.finditer(c):
        before = c[max(0, m.start() - 30):m.start()].split("\n")[-1]       # 같은 줄에 요청 말이 있을 때만
        if not any(w in before for w in _REQUEST_WORDS) and not any(w in c[m.end():m.end() + 8] for w in _REQUEST_WORDS):
            continue                                    # '3일 이내' 가 기한 설명일 때만
        n = int(m.group("n")) * (7 if m.group("u") == "주" else 1)
        if not 1 <= n <= 120:
            continue
        d = base + dt.timedelta(days=n)
        out.append({"kind": "애매", "date": d, "start_date": d, "end_date": d, "time": "", "label": "이내",
                    "snippet": _snippet_at(text, idx_map, m.start(), m.end()) + "  (공문 날짜 기준으로 계산)",
                    "checked": False, "pos": m.start()})
    return out


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
        if c.startswith(")", nxt) and "(" in c[max(0, g["start"] - 2):g["start"]]:
            nxt += 1                                    # '차주 수요일(12. 2.)까지' 처럼 괄호 안 날짜
        nxt2 = nxt + 1 if c.startswith(("에", "은", "는", "을", "를", "도"), nxt) else nxt     # '10:00에 개최' 처럼 조사가 끼어도
        g["after_deadline"] = any(c.startswith(w, nxt) for w in lex["after"])
        g["after_event"] = any(c.startswith(w, nxt2) for w in lex.get("after_event", ()))
        g["after_old"] = c.startswith("에서", nxt)       # '~에서 ~로 변경/연장' 의 앞 날짜
        prev_end = g["end"]

    # 날짜 목록('12. 3., 12. 4. 및 12. 5.')이나 'A에서 B로 변경' 은 앞 날짜의 용어를 이어받는다
    for i in range(1, len(groups)):
        g, pg = groups[i], groups[i - 1]
        between = c[pg["end"]:g["start"]]
        if pg.get("after_old") and between.startswith("에서") and len(between) <= 4:
            g["label_kind"] = pg["label_kind"] or "기한"          # 새 기한/새 일정
            g["after_deadline"] = g["after_deadline"] or g["label_kind"] == "기한"
            g["inherited_new"] = True
        elif g["label_kind"] is None and between in (",", "·", "및", "와", "과", "/", "또는", ",및", "과/", "∼", "") and len(between) <= 3 \
                and pg["label_kind"] in ("기한", "행사"):
            g["label_kind"], g["label_word"] = pg["label_kind"], pg["label_word"]

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
        if kind in (None, "애매") and g.get("after_event"):
            kind = "행사"                                # '12. 12.(토) 10:00 입교' 처럼 뒤에 행사 동사가 붙으면 행사
        if kind is None and l and f is not l:
            kind = "애매"                                # 용어 없이 '12. 1. ~ 12. 7.' 처럼 기간만 있으면 확인 필요
        if g["after_old"] and not g.get("inherited_new"):
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
            "pos": g["start"],
        })

    # (4-2) '금주 금요일까지', '익일까지', '7일 이내' 처럼 날짜가 아니라 말로 쓴 기한
    have = {cd["date"] for cd in candidates}
    for cd in _relative_candidates(c, idx_map, text, base):
        if cd["date"] not in have:
            candidates.append(cd)
            have.add(cd["date"])
    candidates.sort(key=lambda cd: cd["pos"])

    if candidates and not any(cd["checked"] for cd in candidates):
        for cd in candidates:                           # 기한이 하나도 없으면 '애매'를 미리 체크
            if cd["kind"] == "애매":
                cd["checked"] = True
    if candidates and not any(cd["checked"] for cd in candidates):
        for cd in candidates:                           # 기한·애매도 없으면 '행사'(참석 일시 등)를 미리 체크
            if cd["kind"] == "행사":
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
        except ImportError:                             # 설치된 게 없으면 내장 PDF 리더(gongmun_pdf)로 읽는다
            try:
                import gongmun_pdf
                text = "\n".join(gongmun_pdf.read_pdf_text(path))
            except Exception as e:
                raise RuntimeError("PDF를 읽지 못했습니다: %s\n(pypdf 를 설치하면 더 잘 읽힙니다:  pip install pypdf)" % e)
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
    """일정 저장소. 여러 사람이 공유 폴더의 같은 파일을 써도 서로 덮어쓰지 않도록
    저장할 때마다 파일을 다시 읽어 '더 나중에 고친 쪽'을 남기고 합친다.
    지운 일정은 {"id", "deleted": True} 표시만 남겨서 다른 사람 PC 에서도 지워지게 한다."""

    def __init__(self, path):
        self.path = path
        self.events = []
        self._tomb = {}                                 # 지운 일정 id -> 지운 시각
        self.mtime = 0
        self.version = 0                                # 내용이 바뀔 때마다 1씩 오른다 (화면 다시 그릴지 판단)
        t = dt.date.today()
        self.window = (t - dt.timedelta(days=400), t + dt.timedelta(days=800))   # 반복 일정을 펼쳐 둘 기간
        self._group = (None, {})
        self.load()

    @staticmethod
    def _now():
        return dt.datetime.now().isoformat(timespec="seconds")

    def _read_file(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, OSError):         # 파일이 깨졌으면 백업해 두고 새로 시작
            try:
                shutil.copy2(self.path, self.path + ".bak")
            except OSError:
                pass
            return []

    def _split(self, records):
        live, tomb = {}, {}
        for r in records:
            if not isinstance(r, dict) or "id" not in r:
                continue
            if r.get("deleted"):
                tomb[r["id"]] = r.get("updated", "")
            else:
                live[r["id"]] = r
        return live, tomb

    def load(self):
        live, self._tomb = self._split(self._read_file())
        self.events = [e for i, e in live.items() if i not in self._tomb]
        self.mtime = self._file_mtime()
        self.version += 1

    def _file_mtime(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0

    def changed_on_disk(self):
        """다른 사람(또는 다른 창)이 파일을 고쳤으면 True"""
        return self._file_mtime() != self.mtime

    def reload(self):
        """디스크 내용과 합쳐서 다시 읽는다 (내 쪽에서 고친 것도 유지)."""
        self._merge_with_disk()

    def _merge_with_disk(self):
        disk_live, disk_tomb = self._split(self._read_file())
        mine = {e["id"]: e for e in self.events}
        tomb = dict(disk_tomb)
        for i, t in self._tomb.items():
            if t >= tomb.get(i, ""):
                tomb[i] = t
        merged = dict(disk_live)
        for i, e in mine.items():                       # 같은 일정이면 더 나중에 고친 쪽을 남긴다
            if i not in merged or e.get("updated", "") >= merged[i].get("updated", ""):
                merged[i] = e
        for i, t in tomb.items():                       # 지운 뒤에 다시 고친 게 아니면 지운다
            if i in merged and merged[i].get("updated", "") <= t:
                del merged[i]
        self._tomb = tomb
        self.events = sorted(merged.values(), key=lambda e: (e.get("date", ""), e.get("time") or ""))
        self.version += 1

    def save(self):
        self._merge_with_disk()
        records = list(self.events) + [{"id": i, "deleted": True, "updated": t} for i, t in self._tomb.items()]
        tmp = self.path + ".tmp"                        # 임시 파일에 쓴 뒤 바꿔치기 (저장 중 꺼져도 안전)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
        self.mtime = self._file_mtime()

    # ---- 반복 일정 ----------------------------------------------------------
    # 반복 메모는 원본 하나만 저장하고, 달력에는 날짜마다 '가짜 일정'(id = 원본id@날짜)을 만들어 보여 준다.
    # 그날만 완료 = 원본의 done_dates 에 날짜 추가 / 그날만 삭제 = skip_dates 에 날짜 추가
    def _master(self, ev_id):
        for e in self.events:
            if e["id"] == ev_id:
                return e
        return None

    def get(self, ev_id):
        if ev_id and "@" in ev_id:
            base, day = ev_id.split("@", 1)
            m = self._master(base)
            return occurrence(m, day) if m else None
        return self._master(ev_id)

    def _edit(self, ev_id, fn):
        e = self._master(ev_id.split("@", 1)[0] if ev_id else ev_id)
        if e is not None:
            fn(e)
            e["updated"] = self._now()
        self.save()

    def add(self, ev):
        ev.setdefault("id", uuid.uuid4().hex)
        ev.setdefault("done", False)
        ev["updated"] = self._now()
        self.events.append(ev)
        self.save()

    def delete(self, ev_id):
        """일정 삭제. 반복 일정의 한 날짜(id@날짜)면 그날만 뺀다."""
        if "@" in ev_id:
            base, day = ev_id.split("@", 1)
            self._edit(base, lambda e: e.setdefault("skip_dates", []).append(day))
            return
        self.events = [e for e in self.events if e["id"] != ev_id]
        self._tomb[ev_id] = self._now()
        self.save()

    def toggle_done(self, ev_id):
        if "@" in ev_id:                               # 반복 일정은 그날만 완료/취소
            base, day = ev_id.split("@", 1)

            def fn(e):
                dd = e.setdefault("done_dates", [])
                if day in dd:
                    dd.remove(day)
                else:
                    dd.append(day)
            self._edit(base, fn)
            return

        def fn(e):
            e["done"] = not e.get("done", False)
            e["done_at"] = dt.date.today().isoformat() if e["done"] else ""   # 완료한 날짜 기록
        self._edit(ev_id, fn)

    def toggle_mine(self, ev_id):
        """'내 실적'(자기역량기술서에 쓸 업무) 표시를 켜고 끈다"""
        self._edit(ev_id, lambda e: e.__setitem__("mine", not e.get("mine", False)))

    def set_note(self, ev_id, note):
        """내가 한 역할·성과 메모"""
        self._edit(ev_id, lambda e: e.__setitem__("note", note))

    def update(self, ev_id, fields):
        """설정 창에서 고친 값(글자 · 색 · 날짜 · 완료 · 메모 · 반복 ...)을 한꺼번에 저장"""
        self._edit(ev_id, lambda e: e.update(fields))

    def ensure_window(self, lo, hi):
        """반복 일정을 펼쳐 둘 기간이 lo~hi 를 덮게 넓힌다 (달을 넘길 때 부른다)"""
        wlo, whi = self.window
        if lo < wlo or hi > whi:
            self.window = (min(lo, wlo) - dt.timedelta(days=60), max(hi, whi) + dt.timedelta(days=60))
            self._group = (None, {})

    def expanded(self, lo=None, hi=None):
        """보통 일정 + 반복 일정을 lo~hi 기간의 날짜별로 펼친 목록"""
        lo, hi = lo or self.window[0], hi or self.window[1]
        out = []
        for e in self.events:
            if e.get("repeat"):
                out.extend(occurrence(e, d.isoformat()) for d in repeat_dates(e, lo, hi))
            else:
                out.append(e)
        return out

    def group_by_date(self):
        """{날짜: [일정...]}  (내용이 바뀌지 않았으면 지난번 결과를 그대로 쓴다)"""
        if self._group[0] == self.version:
            return self._group[1]
        res = {}
        for e in sorted(self.expanded(), key=lambda e: (e["date"], e.get("time") or "")):
            res.setdefault(e["date"], []).append(e)
        self._group = (self.version, res)
        return res

    def next_occurrences(self, today, days):
        """반복 일정마다 오늘부터 days 일 안의 '다음 한 번' (임박 목록·알림용)"""
        out = []
        for e in self.events:
            if e.get("repeat"):
                for d in repeat_dates(e, today, today + dt.timedelta(days=days)):
                    o = occurrence(e, d.isoformat())
                    if not o.get("done"):
                        out.append(o)
                        break
        return out

    def upcoming(self, today, days=14):
        limit = (today + dt.timedelta(days=days)).isoformat()
        evs = [e for e in self.events if not e.get("repeat") and not e.get("done") and e["date"] <= limit]
        evs += self.next_occurrences(today, days)
        return sorted(evs, key=lambda e: (e["date"], e.get("time") or ""))

    def alert_events(self, today):
        """기한 알림 대상: 보통 일정 + 반복 일정의 가까운 날"""
        return [e for e in self.events if not e.get("repeat")] + self.next_occurrences(today, 3)


# ──────────────────────────────────────────────────────────────
# 6-2. 반복 규칙
#   {"type": "daily"}                         매일
#   {"type": "ndays", "n": 3}                 3일마다
#   {"type": "weekly", "n": 1, "days": [0,2]} 매주(또는 n주마다) 월·수   (0=월 ... 6=일)
#   {"type": "monthly", "day": 15}            매달 15일 (없는 날이면 그달 말일)
#   {"type": "month_start"}                   매월 초 (1일)
#   {"type": "month_end"}                     매월 말 (말일)
#   {"type": "nth_weekday", "nth": 2, "wd": 1} 매월 둘째 화요일 (nth=-1 이면 마지막)
#   {"type": "yearly"}                        매년 같은 날
#   공통: "workday": True  -> 주말·공휴일이면 평일로 옮김 (매월 초는 뒤로, 매월 말은 앞으로)
#         "until": "2026-12-31" 또는 "count": 10  -> 끝나는 때
# ──────────────────────────────────────────────────────────────
REPEAT_TYPES = [("none", "반복 안 함"), ("daily", "매일"), ("ndays", "N일마다"), ("weekly", "매주 (요일 고르기)"),
                ("monthly", "매달 N일"), ("month_start", "매월 초 (1일)"), ("month_end", "매월 말 (말일)"),
                ("nth_weekday", "매월 N번째 ○요일"), ("yearly", "매년")]
WEEKDAY_NAMES = "월화수목금토일"
NTH_NAMES = {1: "첫째", 2: "둘째", 3: "셋째", 4: "넷째", 5: "다섯째", -1: "마지막"}


def _last_day(y, m):
    return (dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)).day


def _is_off(d):
    try:
        import gongmun_kcal
        return d.weekday() >= 5 or d in gongmun_kcal.holidays(d.year)
    except Exception:
        return d.weekday() >= 5


def _to_workday(d, backward=False):
    step = dt.timedelta(days=-1 if backward else 1)
    for _ in range(10):
        if not _is_off(d):
            break
        d += step
    return d


def _raw_dates(r, start, hi):
    """규칙대로 start 부터 hi 까지 날짜를 차례로 낸다 (주말 옮기기 전)"""
    t = r.get("type")
    if t in ("daily", "ndays"):
        step = dt.timedelta(days=1 if t == "daily" else max(1, int(r.get("n", 1))))
        d = start
        while d <= hi:
            yield d
            d += step
    elif t == "weekly":
        days = sorted(set(r.get("days") or [start.weekday()]))
        n = max(1, int(r.get("n", 1)))
        week0 = start - dt.timedelta(days=start.weekday())
        w = 0
        while week0 + dt.timedelta(weeks=w) <= hi:
            if w % n == 0:
                for wd in days:
                    d = week0 + dt.timedelta(weeks=w, days=wd)
                    if start <= d <= hi:
                        yield d
            w += 1
    elif t in ("monthly", "month_start", "month_end", "nth_weekday", "yearly"):
        y, m = start.year, start.month
        while dt.date(y, m, 1) <= hi:
            if t == "monthly":
                d = dt.date(y, m, min(int(r.get("day", start.day)), _last_day(y, m)))
            elif t == "month_start":
                d = dt.date(y, m, 1)
            elif t == "month_end":
                d = dt.date(y, m, _last_day(y, m))
            elif t == "yearly":
                d = dt.date(y, m, min(start.day, _last_day(y, m))) if m == start.month else None
            else:                                       # N번째 요일
                nth, wd = int(r.get("nth", 1)), int(r.get("wd", start.weekday()))
                if nth > 0:
                    first = dt.date(y, m, 1)
                    d = first + dt.timedelta(days=(wd - first.weekday()) % 7 + 7 * (nth - 1))
                    d = d if d.month == m else None
                else:
                    last = dt.date(y, m, _last_day(y, m))
                    d = last - dt.timedelta(days=(last.weekday() - wd) % 7)
            if d is not None and start <= d:
                yield d
            m += 1
            if m > 12:
                y, m = y + 1, 1


def repeat_dates(ev, lo, hi):
    """반복 일정이 lo~hi 사이에 걸리는 날짜들"""
    r = ev.get("repeat") or {}
    if not r or r.get("type") in (None, "none"):
        return []
    try:
        start = dt.date.fromisoformat(ev["date"])
    except (KeyError, ValueError):
        return []
    until = dt.date.fromisoformat(r["until"]) if r.get("until") else None
    count = int(r["count"]) if r.get("count") else None
    end = min(hi, until) if until else hi
    if count is None and lo - start > dt.timedelta(days=400) and r.get("type") in ("daily", "ndays"):
        n = 1 if r["type"] == "daily" else max(1, int(r.get("n", 1)))   # 오래된 매일 반복은 앞부분 건너뛰기
        start = start + dt.timedelta(days=((lo - start).days // n) * n)
    skip = set(ev.get("skip_dates") or [])
    out, k = [], 0
    for d in _raw_dates(r, start, end + dt.timedelta(days=7)):
        k += 1
        if count is not None and k > count:
            break
        if r.get("workday") and r.get("type") in ("monthly", "month_start", "month_end", "nth_weekday", "yearly"):
            d = _to_workday(d, backward=r.get("type") == "month_end")
        if d > end:
            if d > end + dt.timedelta(days=7):
                break
            continue
        if d >= lo and d.isoformat() not in skip:
            out.append(d)
        if k > 20000:
            break
    return out


def occurrence(ev, day):
    """반복 일정의 한 날짜를 일정처럼 쓸 수 있는 사본"""
    o = dict(ev)
    o.update({"id": ev["id"] + "@" + day, "date": day, "series": ev["id"],
              "done": day in (ev.get("done_dates") or []), "done_at": day if day in (ev.get("done_dates") or []) else ""})
    return o


def describe_repeat(r):
    """{"type": "weekly", "days": [0, 2]} -> '매주 월·수'"""
    if not r or r.get("type") in (None, "none"):
        return ""
    t = r["type"]
    if t == "daily":
        s = "매일"
    elif t == "ndays":
        s = "%d일마다" % int(r.get("n", 1))
    elif t == "weekly":
        n = int(r.get("n", 1))
        s = ("매주" if n == 1 else "%d주마다" % n) + " " + "·".join(WEEKDAY_NAMES[d] for d in sorted(r.get("days") or []))
    elif t == "monthly":
        s = "매달 %d일" % int(r.get("day", 1))
    elif t == "month_start":
        s = "매월 초(1일)"
    elif t == "month_end":
        s = "매월 말(말일)"
    elif t == "nth_weekday":
        s = "매월 %s %s요일" % (NTH_NAMES.get(int(r.get("nth", 1)), ""), WEEKDAY_NAMES[int(r.get("wd", 0))])
    elif t == "yearly":
        s = "매년"
    else:
        s = "반복"
    if r.get("workday"):
        s += " (주말·공휴일이면 평일로)"
    if r.get("until"):
        s += " · %s까지" % r["until"]
    elif r.get("count"):
        s += " · %d회" % int(r["count"])
    return s


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
DEFAULT_SETTINGS = {"anchor_date": "", "pattern": [1, 2, 3], "my_team": 0, "team_theme": "기본"}


def load_settings():
    st = dict(DEFAULT_SETTINGS)
    try:
        with open(data_path("설정.json"), "r", encoding="utf-8") as f:
            st.update(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return st


def save_settings(st):
    path = data_path("설정.json")
    tmp = path + ".tmp"                                 # 임시 파일에 쓴 뒤 바꿔치기 (저장 중 꺼져도 설정이 깨지지 않는다)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def patch_settings(patch):
    """설정 파일을 다시 읽어서 patch 에 적은 것만 바꿔 저장한다.
    (위젯 위치처럼 자주 바뀌는 값을 저장할 때 쓴다. 다른 값을 낡은 내용으로 덮어쓰지 않는다.)"""
    st = load_settings()
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(st.get(k), dict):
            st[k].update(v)
        else:
            st[k] = v
    save_settings(st)
    return st


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


def work_type(st):
    """근무 형태: 'shift' = 3교대(내 팀 근무일), 'day' = 일근(평일). 내 팀을 안 정했으면 일근."""
    wt = st.get("work_type")
    if wt == "shift" and st.get("my_team") and team_for(dt.date.today(), st) is not None:
        return "shift"
    if wt in ("day", "shift"):
        return "day"
    return "shift" if st.get("my_team") and team_for(dt.date.today(), st) is not None else "day"


def is_work_day(day, st):
    """내가 근무하는 날인가 (아침 브리핑 · 병아리 '했어요?' 를 이날만)"""
    if work_type(st) == "shift":
        return team_for(day, st) == st.get("my_team")
    return not _is_off(day)


# ──────────────────────────────────────────────────────────────
# 9. 공문 정리: 올린 공문(PDF 등)을 '공문정리\2026년\11월\' 폴더에 제목 이름으로 복사
#    (온나라에서 받은 DOSDKML.pdf 같은 이름이 공문 제목으로 바뀌고, 연도·기안한 달별로 정리된다)
# ──────────────────────────────────────────────────────────────
ARCHIVE_DIR = "공문정리"


def safe_filename(name, maxlen=60):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:maxlen].strip(" .") or "공문"


def archive_subdir(month):
    """'2026-11' -> 공문정리\2026년\11월"""
    y, m = month.split("-")[:2]
    return os.path.join(ARCHIVE_DIR, "%s년" % y, "%02d월" % int(m))


def archive_document(source, text, title, date_iso, stem=None, month=None):
    """공문 사본을 공문정리\연도\월 폴더에 보관하고 '프로그램 폴더 기준 상대경로'를 돌려준다.
    month = 기안(시행)한 달 'YYYY-MM' (모르면 일정 날짜의 달).  stem 이 없으면 제목을 파일 이름으로 쓴다."""
    month = month or (date_iso or dt.date.today().isoformat())[:7]
    sub = archive_subdir(month)
    folder = shared_path(sub)
    os.makedirs(folder, exist_ok=True)
    has_file = bool(source) and os.path.isfile(source)
    ext = (os.path.splitext(source)[1] if has_file else "") or ".txt"
    base = safe_filename(stem or title, 150)
    dest, n = os.path.join(folder, base + ext), 2
    while os.path.exists(dest):
        if has_file and filecmp.cmp(source, dest, shallow=False):
            return os.path.join(sub, os.path.basename(dest))    # 똑같은 공문을 또 올리면 사본을 또 만들지 않는다
        dest = os.path.join(folder, "%s (%d)%s" % (base, n, ext))   # 이름만 같은 다른 공문이면 (2), (3) ...
        n += 1
    if has_file:
        shutil.copy2(source, dest)
    else:                                               # 붙여넣기로 넣은 공문은 글자 파일로 보관
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
    return os.path.join(sub, os.path.basename(dest))


def resolve_doc_path(ev):
    """일정에 연결된 공문 파일의 실제 경로 (없으면 None)"""
    for key in ("file", "source"):
        v = ev.get(key)
        if v:
            cands = [v] if os.path.isabs(v) else [shared_path(v), data_path(v)]
            for p in cands:
                if os.path.isfile(p):
                    return p
    return None


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


# ──────────────────────────────────────────────────────────────
# 11. 관련 공문 묶기 ("○○과-1234호와 관련입니다" -> 같은 건끼리 연결)
# ──────────────────────────────────────────────────────────────
_REF_RE = re.compile(r"[가-힣][가-힣0-9]{1,14}-\d{1,6}")    # 감사2담당관-1407 처럼 숫자가 낀 부서명도


def find_doc_refs(text, own_no=""):
    """본문에 나오는 다른 공문의 문서번호들. 이 공문 자신의 번호(시행 ...)와 접수번호는 뺀다."""
    flat = re.sub(r"\s+", " ", text or "")
    res = []
    for m in _REF_RE.finditer(flat):
        no = m.group(0)
        before = flat[max(0, m.start() - 4):m.start()]
        if no == own_no or "시행" in before or "접수" in before or no in res:
            continue
        res.append(no)
    return res[:10]



def related_events(events, ev):
    """ev 와 문서번호로 이어진 다른 공문 일정들 (같은 공문의 다른 날짜는 뺀다)"""
    my_no = ev.get("doc_no", "")
    my_refs = set(ev.get("refs") or [])
    out, seen = [], set()
    for e in events:
        if e["id"] == ev["id"] or (my_no and e.get("doc_no") == my_no) or (e.get("group") and e.get("group") == ev.get("group")):
            continue
        linked = (e.get("doc_no") and e["doc_no"] in my_refs) or (my_no and my_no in (e.get("refs") or [])) \
            or bool(my_refs & set(e.get("refs") or []))
        key = e.get("group") or e["id"]
        if linked and key not in seen:
            seen.add(key)
            out.append(e)
    return out


# ──────────────────────────────────────────────────────────────
# 11-2. 메모에 '관련 공문' 연결
#   메모의 "links" = [{"key": 공문묶음 id, "title": ..., "doc_no": ...}  (달력에 올린 공문)
#                      {"file": 파일 경로, "title": 파일 이름}]            (파일만 연결)
# ──────────────────────────────────────────────────────────────
def link_key(ev):
    """일정이 속한 '공문 한 건'을 가리키는 값 (같은 공문의 여러 날짜는 같은 값)"""
    return ev.get("group") or ev.get("series") or ev["id"]


def doc_list(events):
    """연결할 수 있는 공문들 (메모·반복 제외, 공문 한 건당 가장 이른 일정 하나), 최근 순"""
    seen = {}
    for e in events:
        if e.get("kind") == "메모" or e.get("repeat") or e.get("series"):
            continue
        k = link_key(e)
        if k not in seen or e["date"] < seen[k]["date"]:
            seen[k] = e
    return sorted(seen.values(), key=lambda e: e["date"], reverse=True)


def make_link(ev):
    return {"key": link_key(ev), "title": ev.get("title", ""), "doc_no": ev.get("doc_no", "")}


def linked_events(events, ev):
    """ev 와 '관련 공문 연결'로 이어진 일정들: 내가 연결한 공문 + 나를 연결한 메모"""
    out, seen = [], {link_key(ev)}
    keys = [lk["key"] for lk in (ev.get("links") or []) if lk.get("key")]
    for k in keys:
        cand = [e for e in events if link_key(e) == k and e.get("kind") != "메모"]
        if cand and k not in seen:
            seen.add(k)
            out.append(min(cand, key=lambda e: e["date"]))
    me = link_key(ev)
    for e in events:
        if e.get("repeat") or e.get("series"):
            if not e.get("repeat"):
                continue
        if any(lk.get("key") == me for lk in (e.get("links") or [])) and link_key(e) not in seen:
            seen.add(link_key(e))
            out.append(e)
    return out


# ──────────────────────────────────────────────────────────────
# 12. 기한 알림 (D-3, D-1, 당일, 지남 - 단계마다 한 번씩)
# ──────────────────────────────────────────────────────────────
ALERT_LEVELS = [(3, "D-3"), (1, "D-1"), (0, "D-day")]


def due_alerts(events, today, levels=(3, 1, 0), alerted=None):
    """지금 띄워야 할 알림 [(일정, 단계이름)].  alerted = {일정id: [이미 띄운 단계]} (내 PC 설정에 저장)"""
    alerted = alerted or {}
    out = []
    for e in events:
        if e.get("done") or e.get("kind") == "변경전":
            continue
        n = dday(e["date"], today)
        done = alerted.get(e["id"]) or []
        for lv, name in ALERT_LEVELS:
            if lv in levels and n == lv and name not in done:
                out.append((e, name))
        if n < 0 and "지남" not in done and n >= -7:
            out.append((e, "지남"))
    return out


# ──────────────────────────────────────────────────────────────
# 13. 검색 (제목·문서번호·기관·메모·붙임)
# ──────────────────────────────────────────────────────────────
def search_events(events, query):
    words = [w for w in re.split(r"\s+", (query or "").strip()) if w]
    if not words:
        return []
    out = []
    for e in events:
        hay = _strip_ws(" ".join([e.get("title", ""), e.get("label", ""), e.get("memo", ""), e.get("doc_no", ""), e.get("org", ""), e.get("note", ""),
                                   e.get("snippet", ""), " ".join(e.get("attachments") or []),
                                   " ".join(e.get("refs") or []), e.get("date", "")]))
        if all(_strip_ws(w) in hay for w in words):
            out.append(e)
    return sorted(out, key=lambda e: e["date"], reverse=True)


# ──────────────────────────────────────────────────────────────
# 14. 처리 현황 엑셀(.xlsx) - 추가 설치 없이 만든다
# ──────────────────────────────────────────────────────────────
def export_xlsx(events, path, today=None):
    import gongmun_xlsx
    today = today or dt.date.today()
    headers = ["상태", "D-day", "구분", "날짜", "시간", "공문 제목", "문서번호", "시행기관", "완료일", "붙임", "메모", "내 실적 메모"]
    rows, styles = [], []
    for e in sorted(events, key=lambda e: (e["date"], e.get("time") or "")):
        n = dday(e["date"], today)
        if e.get("done"):
            state, st = "완료", "done"
        elif n < 0:
            state, st = "기한초과", "late"
        elif n <= 3:
            state, st = "임박", "soon"
        else:
            state, st = "미처리", ""
        rows.append([state, "" if e.get("done") else dday_text(n), e.get("kind", ""), e["date"], e.get("time", ""),
                     e.get("title", ""), e.get("doc_no", ""), e.get("org", ""), e.get("done_at", ""),
                     " / ".join(e.get("attachments") or []), e.get("memo", ""), e.get("note", "")])
        styles.append(st)
    gongmun_xlsx.write_xlsx(path, "업무처리현황", headers, rows, styles,
                            widths=[10, 8, 8, 12, 7, 60, 18, 16, 12, 40, 30, 30])


# ──────────────────────────────────────────────────────────────
# 15. 말로 쓴 메모 분석 ("금요일 3시 회의" -> 이번 금요일 15:00, '회의')
#     병아리대원에게 말한 메모를 달력에 올릴 때 쓴다
# ──────────────────────────────────────────────────────────────
_M_YMD = re.compile(r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\.?")
_M_MD_KOR = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_M_MD = re.compile(r"(?<![\d.:])(\d{1,2})\s*[./]\s*(\d{1,2})(?![\d:])\.?(?:\s*\([월화수목금토일]\))?")
_M_REL_DAY = re.compile(r"(오늘|금일|내일|명일|익일|모레|글피)")
_M_WEEKDAY = re.compile(r"(?:(이번\s*주|금주|이번|다음\s*주|담주|차주|다다음\s*주)\s*)?([월화수목금토일])요일")
_M_AFTER = re.compile(r"(\d{1,3})\s*(일|주)\s*(?:뒤|후)")
_M_MONTH_DAY = re.compile(r"(이번\s*달|다음\s*달|담달)\s*(\d{1,2})\s*일")
_M_DAY_ONLY = re.compile(r"(?<![\d월])(\d{1,2})\s*일(?!\s*(?:이내|간|마다|뒤|후|전|동안|째))")
_M_TIME = re.compile(r"(오전|오후|아침|저녁|밤|낮|새벽)?\s*(\d{1,2})\s*시\s*(?:(\d{1,2})\s*분|(반))?")
_M_CLOCK = re.compile(r"(오전|오후)?\s*(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_M_NOON = re.compile(r"정오")
_M_DEADLINE = ("까지", "마감", "제출", "회신", "보고", "기한", "송부", "신청")
_M_PARTICLE = re.compile(r"^(?:에는|에|엔|까지|부터|에서|는|은|,|·|-|~)\s*|\s*(?:에는|에|엔|까지는|까지|부터|에서|,|·)$")


def _next_weekday(today, wd, week_offset=None):
    if week_offset is None:                             # 그냥 '금요일' = 오늘부터 가장 가까운 금요일
        return today + dt.timedelta(days=(wd - today.weekday()) % 7)
    monday = today - dt.timedelta(days=today.weekday())
    return monday + dt.timedelta(weeks=week_offset, days=wd)


def parse_memo(text, today=None):
    """말로 쓴 메모에서 날짜·시간·내용을 뽑는다.
    돌려주는 값: {"date": 날짜, "time": "HH:MM" 또는 "", "title": 내용, "kind": "메모"/"기한", "found": 날짜를 찾았나}"""
    today = today or dt.date.today()
    raw = re.sub(r"\s+", " ", (text or "").strip())
    spans, day, tm = [], None, ""

    def take(m):
        spans.append(m.span())

    for rx, fn in (
        (_M_YMD, lambda m: _make_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (_M_MD_KOR, lambda m: _md(today, int(m.group(1)), int(m.group(2)))),
        (_M_MONTH_DAY, lambda m: _month_day(today, 1 if "다음" in m.group(1) or "담" in m.group(1) else 0, int(m.group(2)))),
        (_M_AFTER, lambda m: today + dt.timedelta(days=int(m.group(1)) * (7 if m.group(2) == "주" else 1))),
        (_M_WEEKDAY, lambda m: _weekday_from(today, m.group(1), m.group(2))),
        (_M_REL_DAY, lambda m: today + dt.timedelta(days={"오늘": 0, "금일": 0, "내일": 1, "명일": 1, "익일": 1, "모레": 2, "글피": 3}[m.group(1)])),
        (_M_MD, lambda m: _md(today, int(m.group(1)), int(m.group(2)))),
        (_M_DAY_ONLY, lambda m: _month_day(today, 0 if int(m.group(1)) >= today.day else 1, int(m.group(1)))),
    ):
        if day is not None:
            break
        for m in rx.finditer(raw):
            if any(a < m.end() and m.start() < b for a, b in spans):
                continue
            d = fn(m)
            if d:
                day = d
                take(m)
                break

    m = _M_CLOCK.search(raw)
    if m and not any(a < m.end() and m.start() < b for a, b in spans):
        h, mi = int(m.group(2)), int(m.group(3))
        if m.group(1) == "오후" and h < 12:
            h += 12
        if h <= 23 and mi <= 59:
            tm = "%02d:%02d" % (h, mi)
            take(m)
    if not tm:
        m = _M_TIME.search(raw)
        if m and not any(a < m.end() and m.start() < b for a, b in spans):
            h = int(m.group(2))
            mi = 30 if m.group(4) else int(m.group(3) or 0)
            ap = m.group(1)
            if ap in ("오후", "저녁", "밤") and h < 12:
                h += 12
            elif ap is None and 1 <= h <= 7:
                h += 12                                 # '3시 회의' 는 보통 오후 3시
            if h <= 23 and mi <= 59:
                tm = "%02d:%02d" % (h, mi)
                take(m)
    if not tm:
        m = _M_NOON.search(raw)
        if m:
            tm = "12:00"
            take(m)

    title = raw
    for a, b in sorted(spans, reverse=True):
        title = title[:a] + " " + title[b:]
    title = re.sub(r"\s+", " ", title).strip()
    for _ in range(3):
        title = _M_PARTICLE.sub("", title).strip()
    kind = "기한" if any(w in raw for w in _M_DEADLINE) else "메모"
    return {"date": day or today, "time": tm, "title": title or raw, "kind": kind, "found": day is not None}


def _md(today, m, d):
    """연도 없는 월·일: 지난 지 오래(6개월 넘게)됐으면 내년으로"""
    x = _make_date(today.year, m, d)
    if x and (today - x).days > 180:
        x = _make_date(today.year + 1, m, d)
    return x


def _month_day(today, month_offset, d):
    y, m = today.year, today.month + month_offset
    if m > 12:
        y, m = y + 1, m - 12
    return _make_date(y, m, d)


def _weekday_from(today, prefix, wd_name):
    wd = "월화수목금토일".index(wd_name)
    p = re.sub(r"\s+", "", prefix or "")
    if p in ("다음주", "담주", "차주"):
        return _next_weekday(today, wd, 1)
    if p == "다다음주":
        return _next_weekday(today, wd, 2)
    if p in ("이번주", "금주", "이번"):
        return _next_weekday(today, wd, 0)
    return _next_weekday(today, wd)
