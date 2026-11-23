# -*- coding: utf-8 -*-
"""
gongmun_kcal.py  -  음력 · 24절기 · 우리나라 공휴일 (추가 설치·인터넷 없이 계산)

  - 음력: 달이 해와 겹치는 순간(합삭)과 해의 위치(중기)를 천문 계산으로 구해
          한국 시간(KST) 기준으로 음력 날짜와 윤달을 정한다.
  - 24절기: 해의 황경이 15도씩 바뀌는 날 (입춘, 입동, 소설 ...)
  - 공휴일: 양력 공휴일 + 설날·부처님오신날·추석 + 대체공휴일

    solar_to_lunar(날짜)  -> (음력 연, 월, 일, 윤달여부)
    day_info(날짜)        -> {"lunar": "10.15", "term": "소설", "holiday": "추석"}
"""
import datetime as dt
from functools import lru_cache
from math import floor, radians, sin

_J2000 = dt.datetime(2000, 1, 1, 12)
_KST = 9 / 24
_DELTA_T = 69.0 / 86400                                 # 지구 자전 보정 (약 69초)

TERMS = {0: "춘분", 15: "청명", 30: "곡우", 45: "입하", 60: "소만", 75: "망종", 90: "하지", 105: "소서",
         120: "대서", 135: "입추", 150: "처서", 165: "백로", 180: "추분", 195: "한로", 210: "상강",
         225: "입동", 240: "소설", 255: "대설", 270: "동지", 285: "소한", 300: "대한", 315: "입춘",
         330: "우수", 345: "경칩"}


def _jd_to_kst_date(jde):
    """천문 시각(JDE) -> 한국 날짜"""
    jd = jde - _DELTA_T + _KST
    return (_J2000 + dt.timedelta(days=jd - 2451545.0)).date()


def _date_to_jd(d):
    return 2451545.0 + (dt.datetime(d.year, d.month, d.day) - _J2000).total_seconds() / 86400


# ---- 해의 위치 ----------------------------------------------------------------
def _sun_longitude(jde):
    T = (jde - 2451545.0) / 36525
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * sin(M) + (0.019993 - 0.000101 * T) * sin(2 * M)
         + 0.000289 * sin(3 * M))
    om = radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * sin(om)) % 360


def _term_jde(year, lon):
    """year 년에 해의 황경이 lon 도가 되는 시각"""
    day = (lon - 280) % 360                              # 황경 280도 ≈ 1월 1일 무렵
    jde = _date_to_jd(dt.date(year, 1, 1)) + day * 365.2422 / 360
    for _ in range(50):
        diff = (lon - _sun_longitude(jde) + 180) % 360 - 180
        jde += diff * 365.2422 / 360
        if abs(diff) < 1e-6:
            break
    return jde


@lru_cache(maxsize=64)
def solar_terms(year):
    """{날짜: 절기이름} (그 해 24개)"""
    return {_jd_to_kst_date(_term_jde(year, lon)): name for lon, name in TERMS.items()}


# ---- 합삭 (음력 초하루) -----------------------------------------------------------
def _new_moon_jde(k):
    """k 번째 합삭 시각 (Meeus, Astronomical Algorithms 49장)"""
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2 - 0.000000150 * T ** 3
           + 0.00000000073 * T ** 4)
    E = 1 - 0.002516 * T - 0.0000074 * T ** 2
    M = radians(2.5534 + 29.10535670 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3)
    Mp = radians(201.5643 + 385.81693528 * k + 0.0107582 * T ** 2 + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = radians(160.7108 + 390.67050284 * k - 0.0016118 * T ** 2 - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    Om = radians(124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3)
    corr = (-0.40720 * sin(Mp) + 0.17241 * E * sin(M) + 0.01608 * sin(2 * Mp) + 0.01039 * sin(2 * F)
            + 0.00739 * E * sin(Mp - M) - 0.00514 * E * sin(Mp + M) + 0.00208 * E * E * sin(2 * M)
            - 0.00111 * sin(Mp - 2 * F) - 0.00057 * sin(Mp + 2 * F) + 0.00056 * E * sin(2 * Mp + M)
            - 0.00042 * sin(3 * Mp) + 0.00042 * E * sin(M + 2 * F) + 0.00038 * E * sin(M - 2 * F)
            - 0.00024 * E * sin(2 * Mp - M) - 0.00017 * sin(Om) - 0.00007 * sin(Mp + 2 * M)
            + 0.00004 * sin(2 * Mp - 2 * F) + 0.00004 * sin(3 * M) + 0.00003 * sin(Mp + M - 2 * F)
            + 0.00003 * sin(2 * Mp + 2 * F) - 0.00003 * sin(Mp + M + 2 * F) + 0.00003 * sin(Mp - M + 2 * F)
            - 0.00002 * sin(Mp - M - 2 * F) - 0.00002 * sin(3 * Mp + M) + 0.00002 * sin(4 * Mp))
    A = [299.77 + 0.107408 * k - 0.009173 * T * T, 251.88 + 0.016321 * k, 251.83 + 26.651886 * k,
         349.42 + 36.412478 * k, 84.66 + 18.206239 * k, 141.74 + 53.303771 * k, 207.14 + 2.453732 * k,
         154.84 + 7.306860 * k, 34.52 + 27.261239 * k, 207.19 + 0.121824 * k, 291.34 + 1.844379 * k,
         161.72 + 24.198154 * k, 239.56 + 25.513099 * k, 331.55 + 3.592518 * k]
    coef = [0.000325, 0.000165, 0.000164, 0.000126, 0.000110, 0.000062, 0.000060, 0.000056, 0.000047,
            0.000042, 0.000040, 0.000037, 0.000035, 0.000023]
    return jde + corr + sum(c * sin(radians(a)) for c, a in zip(coef, A))


def _new_moon_on_or_before(d):
    """d 날짜(포함) 이전의 가장 가까운 합삭 날짜"""
    k = floor((d - dt.date(2000, 1, 6)).days / 29.530588861) + 1
    while True:
        nm = _jd_to_kst_date(_new_moon_jde(k))
        if nm <= d:
            return nm, k
        k -= 1


def _winter_solstice(year):
    return _jd_to_kst_date(_term_jde(year, 270))


@lru_cache(maxsize=64)
def _lunar_window(y):
    """(y-1)년 동지가 든 달(11월) ~ y년 동지가 든 달 직전까지의 음력 달 목록.
    [(초하루 날짜, 음력 연, 월, 윤달여부)] 과 그다음 11월 초하루"""
    start, k = _new_moon_on_or_before(_winter_solstice(y - 1))
    end, _ = _new_moon_on_or_before(_winter_solstice(y))
    starts = []
    while True:
        nm = _jd_to_kst_date(_new_moon_jde(k))
        if nm >= end:
            break
        starts.append(nm)
        k += 1
    starts.append(end)
    n = len(starts) - 1                                  # 12 또는 13 (13이면 윤달이 있는 해)
    leap_idx = None
    if n == 13:
        majors = sorted(d for yy in (y - 1, y) for d, name in solar_terms(yy).items()
                        if [lon for lon, nm_ in TERMS.items() if nm_ == name][0] % 30 == 0)
        for i in range(n):                               # 중기(황경 30도 배수)가 없는 첫 달 = 윤달
            if not any(starts[i] <= m < starts[i + 1] for m in majors):
                leap_idx = i
                break
    months, num = [], 11
    for i in range(n):
        leap = i == leap_idx
        if i > 0 and not leap:
            num = num % 12 + 1
        ly = y - 1 if num >= 11 and i < 3 else y
        months.append((starts[i], ly, num, leap))
    return tuple(months), end


def solar_to_lunar(d):
    """양력 날짜 -> (음력 연, 월, 일, 윤달여부)"""
    y = d.year
    for yy in (y, y + 1, y - 1):
        months, end = _lunar_window(yy)
        if months[0][0] <= d < end:
            for i, (s, ly, m, leap) in enumerate(months):
                nxt = months[i + 1][0] if i + 1 < len(months) else end
                if s <= d < nxt:
                    return ly, m, (d - s).days + 1, leap
    raise ValueError(d)


def lunar_to_solar(ly, m, day, leap=False):
    """음력 날짜 -> 양력 날짜 (없으면 None)"""
    for yy in (ly, ly + 1):
        for s, y2, m2, lp in _lunar_window(yy)[0]:
            if y2 == ly and m2 == m and lp == leap:
                return s + dt.timedelta(days=day - 1)
    return None


# ---- 공휴일 ---------------------------------------------------------------------
@lru_cache(maxsize=32)
def holidays(year):
    """{날짜: 공휴일 이름}  (대체공휴일 포함)"""
    h = {}
    fixed = {(1, 1): "신정", (3, 1): "삼일절", (5, 5): "어린이날", (6, 6): "현충일", (8, 15): "광복절",
             (10, 3): "개천절", (10, 9): "한글날", (12, 25): "성탄절"}
    for (m, d), name in fixed.items():
        h[dt.date(year, m, d)] = name
    seol = lunar_to_solar(year, 1, 1)
    chu = lunar_to_solar(year, 8, 15)
    buddha = lunar_to_solar(year, 4, 8)
    groups = []
    if seol:
        days = [seol - dt.timedelta(days=1), seol, seol + dt.timedelta(days=1)]
        for x in days:
            h[x] = "설날"
        groups.append(("설날", days, False))
    if chu:
        days = [chu - dt.timedelta(days=1), chu, chu + dt.timedelta(days=1)]
        for x in days:
            h[x] = "추석"
        groups.append(("추석", days, False))
    if buddha:
        h[buddha] = (h[buddha] + "·" if buddha in h else "") + "부처님오신날"
        groups.append(("부처님오신날", [buddha], True))
    for (m, d), name in fixed.items():
        if name not in ("신정", "현충일"):
            groups.append((name, [dt.date(year, m, d)], True))

    # 대체공휴일: 설날·추석은 일요일(또는 다른 공휴일)과 겹치면, 나머지는 토·일(또는 다른 공휴일)과 겹치면
    #            그다음 첫 평일(공휴일 아닌 날)을 쉰다
    base = dict(h)
    subs, paid = {}, set()                               # paid: 겹친 날에 대해 이미 하루 준 날짜
    for name, days, sat_too in groups:
        hit = False
        for x in days:
            other = any(x in ds for n2, ds, _ in groups if n2 != name)
            if x.weekday() == 6 or (sat_too and x.weekday() == 5):
                hit = True
            elif other and x not in paid:               # 공휴일끼리 겹치면 하루만 더 쉰다
                hit = True
                paid.add(x)
        if hit:
            x = max(days) + dt.timedelta(days=1)
            while x.weekday() >= 5 or x in base or x in subs:
                x += dt.timedelta(days=1)
            subs[x] = "대체공휴일"
    h.update(subs)
    for d, name in SPECIAL_DAYS.items():                 # 선거일 등 그해만 쉬는 날
        if d.year == year:
            h.setdefault(d, name)
    return h


# 해마다 다른 임시공휴일 (필요하면 여기에 한 줄 추가)
SPECIAL_DAYS = {
    dt.date(2026, 6, 3): "지방선거",
    dt.date(2028, 4, 12): "국회의원선거",
}


def day_info(d, lunar=True):
    """달력 칸에 적을 정보 {"holiday", "term", "lunar"}"""
    info = {"holiday": holidays(d.year).get(d, ""), "term": solar_terms(d.year).get(d, ""), "lunar": ""}
    if lunar:
        try:
            _, m, day, leap = solar_to_lunar(d)
            info["lunar"] = "%s%d.%d" % ("윤" if leap else "", m, day)
        except ValueError:
            pass
    return info
