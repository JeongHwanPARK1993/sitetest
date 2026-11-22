"""추가 설치 없이(파이썬 기본 기능만으로) PDF 의 글자를 읽는 작은 모듈.

회사 PC 처럼 라이브러리를 설치할 수 없는 곳을 위해 만들었다.
온나라 등에서 '저장' 한 공문 PDF(글자가 들어 있는 PDF)를 읽는 데 필요한 만큼만 구현했다.

    pages = read_pdf_text("공문.pdf")   # 쪽마다 '줄 단위' 글자

지원: Flate/ASCIIHex/ASCII85 압축, 객체 스트림(PDF 1.5+), Type0(CID)/TrueType/Type1 글꼴,
      ToUnicode 표, 한글 CMap(UniKS-UCS2/UTF16, KSC/UHC), Form XObject.
      열람 암호 없는 RC4 암호 PDF(온나라 공문에 흔함).
미지원: 열람 암호/AES 암호 PDF, 스캔(이미지) PDF -> 예외 또는 빈 글자.
"""
from __future__ import annotations

import re
import zlib

__all__ = ["read_pdf_lines", "read_pdf_text", "Line", "PdfError"]


class PdfError(Exception):
    pass


# ============================================================ 기본 객체
class Name(str):
    pass


class Ref:
    __slots__ = ("num", "gen")

    def __init__(self, num: int, gen: int):
        self.num, self.gen = num, gen

    def __repr__(self):
        return f"Ref({self.num})"


class Stream:
    __slots__ = ("dict", "raw")

    def __init__(self, d: dict, raw: bytes):
        self.dict, self.raw = d, raw


class Op(str):
    """내용 스트림의 연산자 (Tj, Tf ...)"""


WS = b" \t\r\n\x0c\x00"
DELIM = b"()<>[]{}/%"
_NUM = re.compile(rb"[+-]?(?:\d+\.?\d*|\.\d+)")
_REF = re.compile(rb"\s*(\d+)\s+R(?![A-Za-z0-9_])")
_REGULAR = re.compile(rb"[^\s()<>\[\]{}/%\x00]+")
_ESC = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}


class Lexer:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos, self.n = data, pos, len(data)

    def skip_ws(self) -> None:
        d, p, n = self.data, self.pos, self.n
        while p < n:
            c = d[p]
            if c in WS:
                p += 1
            elif c == 0x25:  # % 주석
                while p < n and d[p] not in b"\r\n":
                    p += 1
            else:
                break
        self.pos = p

    def next(self, allow_ref: bool = True):
        """다음 객체 하나. 끝이면 StopIteration. 연산자/키워드는 Op."""
        self.skip_ws()
        d, p = self.data, self.pos
        if p >= self.n:
            raise StopIteration
        c = d[p]
        if c == 0x2F:  # /Name
            m = _REGULAR.match(d, p + 1)
            raw = m.group(0) if m else b""
            self.pos = p + 1 + len(raw)
            if b"#" in raw:
                raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda x: bytes([int(x.group(1), 16)]), raw)
            return Name(raw.decode("latin-1"))
        if c == 0x28:  # (string)
            return self._literal()
        if c == 0x3C:  # < or <<
            if d[p + 1:p + 2] == b"<":
                self.pos = p + 2
                return self._dict()
            end = d.find(b">", p)
            if end < 0:
                end = self.n
            hx = re.sub(rb"[^0-9A-Fa-f]", b"", d[p + 1:end])
            if len(hx) % 2:
                hx += b"0"
            self.pos = end + 1
            return bytes.fromhex(hx.decode())
        if c == 0x5B:  # [
            self.pos = p + 1
            arr = []
            while True:
                self.skip_ws()
                if self.pos >= self.n:
                    return arr
                if d[self.pos] == 0x5D:
                    self.pos += 1
                    return arr
                arr.append(self.next(allow_ref))
        if c in b">]})":  # 짝이 안 맞는 닫는 기호는 건너뜀
            self.pos = p + (2 if d[p:p + 2] == b">>" else 1)
            return Op(chr(c))
        m = _NUM.match(d, p)
        if m and (m.end() >= self.n or d[m.end()] in WS or d[m.end()] in DELIM):
            s = m.group(0)
            self.pos = m.end()
            if b"." in s:
                return float(s)
            v = int(s)
            if allow_ref:
                r = _REF.match(d, self.pos)
                if r:
                    self.pos = r.end()
                    return Ref(v, int(r.group(1)))
            return v
        m = _REGULAR.match(d, p)
        if not m:
            self.pos = p + 1
            return Op(chr(c))
        self.pos = m.end()
        w = m.group(0)
        if w == b"true":
            return True
        if w == b"false":
            return False
        if w == b"null":
            return None
        return Op(w.decode("latin-1"))

    def _dict(self) -> dict:
        out = {}
        d = self.data
        while True:
            self.skip_ws()
            if self.pos >= self.n:
                return out
            if d[self.pos:self.pos + 2] == b">>":
                self.pos += 2
                return out
            key = self.next()
            if not isinstance(key, Name):
                continue
            self.skip_ws()
            if d[self.pos:self.pos + 2] == b">>":
                out[key] = None
                continue
            out[key] = self.next()

    def _literal(self) -> bytes:
        d, p, n = self.data, self.pos + 1, self.n
        out = bytearray()
        depth = 1
        while p < n:
            c = d[p]
            if c == 0x5C:  # \
                p += 1
                if p >= n:
                    break
                c = d[p]
                if c in _ESC:
                    out.append(_ESC[c])
                    p += 1
                elif 0x30 <= c <= 0x37:
                    m = re.match(rb"[0-7]{1,3}", d[p:p + 3])
                    out.append(int(m.group(0), 8) & 0xFF)
                    p += len(m.group(0))
                elif c == 0x0D:
                    p += 2 if d[p + 1:p + 2] == b"\n" else 1
                elif c == 0x0A:
                    p += 1
                else:
                    out.append(c)
                    p += 1
                continue
            if c == 0x28:
                depth += 1
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    p += 1
                    break
            out.append(c)
            p += 1
        self.pos = p
        return bytes(out)


# ============================================================ 압축 풀기
def _flate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except zlib.error:
        # 끝이 잘렸거나 헤더가 이상한 경우: 풀 수 있는 만큼만
        for wbits in (15, -15):
            try:
                return zlib.decompressobj(wbits).decompress(data)
            except zlib.error:
                continue
        raise


def _ahx(data: bytes) -> bytes:
    data = data.split(b">")[0]
    hx = re.sub(rb"[^0-9A-Fa-f]", b"", data)
    if len(hx) % 2:
        hx += b"0"
    return bytes.fromhex(hx.decode())


def _a85(data: bytes) -> bytes:
    import base64

    data = re.sub(rb"\s", b"", data)
    if data.startswith(b"<~"):
        data = data[2:]
    if not data.endswith(b"~>"):
        data += b"~>"
    return base64.a85decode(b"<~" + data, adobe=True)


def _png_predict(data: bytes, columns: int, colors: int = 1, bpc: int = 8) -> bytes:
    bpp = max(1, colors * bpc // 8)
    row_len = (columns * colors * bpc + 7) // 8
    out = bytearray()
    prev = bytearray(row_len)
    i = 0
    while i < len(data):
        ft = data[i]
        row = bytearray(data[i + 1:i + 1 + row_len])
        i += 1 + row_len
        for k in range(len(row)):
            a = row[k - bpp] if k >= bpp else 0
            b = prev[k] if k < len(prev) else 0
            c = prev[k - bpp] if k >= bpp else 0
            if ft == 1:
                row[k] = (row[k] + a) & 0xFF
            elif ft == 2:
                row[k] = (row[k] + b) & 0xFF
            elif ft == 3:
                row[k] = (row[k] + ((a + b) >> 1)) & 0xFF
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[k] = (row[k] + pr) & 0xFF
        out += row
        prev = row
    return bytes(out)


# ============================================================ 암호 (표준 보안, RC4)
# 온나라 공문 PDF 는 '열람 암호 없이 인쇄/수정만 막는' RC4 암호가 걸린 경우가 많다.
# 열람 암호가 비어 있으면 파이썬 기본 기능(md5)만으로 풀 수 있다.
_PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")


def _rc4(key: bytes, data: bytes) -> bytes:
    S = list(range(256))
    j = 0
    kl = len(key)
    for i in range(256):
        j = (j + S[i] + key[i % kl]) & 0xFF
        S[i], S[j] = S[j], S[i]
    out = bytearray(len(data))
    i = j = 0
    for k, b in enumerate(data):
        i = (i + 1) & 0xFF
        si = S[i]
        j = (j + si) & 0xFF
        sj = S[j]
        S[i], S[j] = sj, si
        out[k] = b ^ S[(si + sj) & 0xFF]
    return bytes(out)


class _Crypt:
    def __init__(self, enc: dict, file_id: bytes):
        from hashlib import md5

        if enc.get("Filter") != "Standard":
            raise PdfError("지원하지 않는 암호 방식입니다")
        v = int(enc.get("V", 0) or 0)
        r = int(enc.get("R", 2) or 2)
        n = int(enc.get("Length", 40) or 40) // 8
        if v == 4:
            cf = enc.get("CF") or {}
            std = cf.get(enc.get("StmF", "StdCF")) if isinstance(cf, dict) else None
            cfm = std.get("CFM") if isinstance(std, dict) else None
            if cfm == "AESV2":
                raise PdfError("AES 암호가 걸린 PDF 는 읽을 수 없습니다")
            if isinstance(std, dict) and std.get("Length"):
                ln = int(std["Length"])
                n = ln if ln <= 16 else ln // 8
        elif v >= 5 or v == 3:
            raise PdfError("지원하지 않는 암호 방식입니다 (AES-256 등)")
        if r == 2:
            n = 5
        n = max(5, min(16, n))
        o = bytes(enc.get("O") or b"")[:32]
        u = bytes(enc.get("U") or b"")[:32]
        p = int(enc.get("P", 0) or 0) & 0xFFFFFFFF
        h = md5(_PAD + o + p.to_bytes(4, "little") + file_id)
        if r >= 4 and enc.get("EncryptMetadata") is False:
            h.update(b"\xff\xff\xff\xff")
        key = h.digest()[:n]
        if r >= 3:
            for _ in range(50):
                key = md5(key[:n]).digest()[:n]
        if r == 2:
            ok = _rc4(key, _PAD) == u
        else:
            x = _rc4(key, md5(_PAD + file_id).digest())
            for i in range(1, 20):
                x = _rc4(bytes(b ^ i for b in key), x)
            ok = x[:16] == u[:16]
        if not ok:
            raise PdfError("열람 암호가 걸린 PDF 는 읽을 수 없습니다")
        self.key, self.n = key, n

    def obj_key(self, num: int, gen: int) -> bytes:
        from hashlib import md5

        return md5(self.key + num.to_bytes(3, "little") + gen.to_bytes(2, "little")).digest()[:min(self.n + 5, 16)]

    def decrypt_obj(self, obj, key: bytes):
        if isinstance(obj, bytes):
            return _rc4(key, obj)
        if isinstance(obj, list):
            return [self.decrypt_obj(x, key) for x in obj]
        if isinstance(obj, dict):
            return {k: self.decrypt_obj(v, key) for k, v in obj.items()}
        if isinstance(obj, Stream):
            d = {k: self.decrypt_obj(v, key) for k, v in obj.dict.items()}
            raw = obj.raw if obj.dict.get("Type") == "XRef" else _rc4(key, obj.raw)
            return Stream(d, raw)
        return obj


# ============================================================ 문서
class Document:
    def __init__(self, data: bytes):
        if not data.lstrip()[:5] == b"%PDF-" and b"%PDF-" not in data[:1024]:
            raise PdfError("PDF 파일이 아닙니다")
        self.data = data
        self.offsets: dict[int, tuple[int, int]] = {}
        for m in re.finditer(rb"(?<![0-9])(\d+)\s+(\d+)\s+obj(?![A-Za-z])", data):
            self.offsets[int(m.group(1))] = (m.end(), int(m.group(2)))  # 뒤에 나온 것(수정본)이 우선
        self.cache: dict[int, object] = {}
        self._objstm_index: dict[int, tuple[int, int]] | None = None
        self.crypt: _Crypt | None = None
        self.enc_num = -1
        trailer = self._trailer()
        enc_ref = trailer.get("Encrypt")
        if enc_ref is not None:
            enc = self.resolve(enc_ref)
            if not isinstance(enc, dict):
                raise PdfError("암호 정보를 읽지 못했습니다")
            ids = trailer.get("ID")
            file_id = ids[0] if isinstance(ids, list) and ids and isinstance(ids[0], bytes) else b""
            self.crypt = _Crypt(enc, file_id)
            self.enc_num = enc_ref.num if isinstance(enc_ref, Ref) else -1
            self.cache.clear()
        root = self.resolve(trailer.get("Root"))
        if not isinstance(root, dict):
            root = self._find_catalog()
        if not isinstance(root, dict):
            raise PdfError("PDF 구조(Catalog)를 찾지 못했습니다")
        self.root = root

    # -------------------------------------------------- 객체 읽기
    def _trailer(self) -> dict:
        d = self.data
        merged: dict = {}
        # 옛 형식 trailer << >> 와 XRef 스트림 사전을 모두 본다 (앞→뒤, 뒤쪽이 우선)
        for m in re.finditer(rb"trailer\s*<<", d):
            lx = Lexer(d, m.end() - 2)
            try:
                t = lx.next()
                if isinstance(t, dict):
                    merged.update(t)
            except StopIteration:
                pass
        if "Root" not in merged or "Encrypt" not in merged:
            for m in re.finditer(rb"/Type\s*/XRef", d):
                start = d.rfind(b"<<", 0, m.start())
                if start < 0:
                    continue
                try:
                    t = Lexer(d, start).next()
                except StopIteration:
                    continue
                if isinstance(t, dict):
                    for k in ("Root", "Encrypt", "ID"):
                        if k in t and k not in merged:
                            merged[k] = t[k]
        return merged

    def _find_catalog(self):
        for m in re.finditer(rb"/Type\s*/Catalog", self.data):
            num = None
            for om in re.finditer(rb"(\d+)\s+\d+\s+obj", self.data[max(0, m.start() - 4000):m.start()]):
                num = int(om.group(1))
            if num is not None:
                obj = self.get(num)
                if isinstance(obj, dict):
                    return obj
        return None

    def get(self, num: int):
        if num in self.cache:
            return self.cache[num]
        self.cache[num] = None  # 순환 참조 방지
        obj = None
        if num in self.offsets:
            pos, gen = self.offsets[num]
            obj = self._parse_at(pos)
            if self.crypt is not None and num != self.enc_num:
                obj = self.crypt.decrypt_obj(obj, self.crypt.obj_key(num, gen))
        else:
            obj = self._from_objstm(num)  # 객체 스트림 전체가 이미 풀려 있음
        self.cache[num] = obj
        return obj

    def _parse_at(self, pos: int):
        lx = Lexer(self.data, pos)
        try:
            obj = lx.next()
        except StopIteration:
            return None
        if isinstance(obj, dict):
            lx.skip_ws()
            if self.data.startswith(b"stream", lx.pos):
                p = lx.pos + 6
                if self.data[p:p + 2] == b"\r\n":
                    p += 2
                elif self.data[p:p + 1] in (b"\n", b"\r"):
                    p += 1
                raw = None
                length = obj.get("Length")
                if isinstance(length, Ref):
                    length = self.get(length.num)
                if isinstance(length, int) and 0 <= length <= len(self.data) - p:
                    tail = self.data[p + length:p + length + 32].lstrip(WS)
                    if tail.startswith(b"endstream"):
                        raw = self.data[p:p + length]
                if raw is None:
                    end = self.data.find(b"endstream", p)
                    if end < 0:
                        end = len(self.data)
                    raw = self.data[p:end]
                    if raw.endswith(b"\r\n"):
                        raw = raw[:-2]
                    elif raw.endswith((b"\n", b"\r")):
                        raw = raw[:-1]
                return Stream(obj, raw)
        return obj

    def _from_objstm(self, num: int):
        if self._objstm_index is None:
            self._objstm_index = {}
            for m in re.finditer(rb"/Type\s*/ObjStm", self.data):
                # 이 사전이 속한 객체 번호 찾기
                head = self.data[max(0, m.start() - 600):m.start()]
                oms = list(re.finditer(rb"(\d+)\s+\d+\s+obj", head))
                if not oms:
                    continue
                snum = int(oms[-1].group(1))
                st = self.get(snum)
                if not isinstance(st, Stream):
                    continue
                try:
                    body = self.decode(st)
                except Exception:
                    continue
                n = int(self.resolve(st.dict.get("N", 0)) or 0)
                first = int(self.resolve(st.dict.get("First", 0)) or 0)
                nums = re.findall(rb"\d+", body[:first])
                for i in range(min(n, len(nums) // 2)):
                    onum, off = int(nums[2 * i]), int(nums[2 * i + 1])
                    self._objstm_index.setdefault(onum, (snum, first + off))
        loc = self._objstm_index.get(num)
        if not loc:
            return None
        st = self.get(loc[0])
        body = self.decode(st)
        try:
            return Lexer(body, loc[1]).next()
        except StopIteration:
            return None

    def resolve(self, obj):
        depth = 0
        while isinstance(obj, Ref) and depth < 32:
            obj = self.get(obj.num)
            depth += 1
        return obj

    def decode(self, st: Stream) -> bytes:
        filters = self.resolve(st.dict.get("Filter"))
        parms = self.resolve(st.dict.get("DecodeParms"))
        if filters is None:
            return st.raw
        if not isinstance(filters, list):
            filters, parms = [filters], [parms]
        elif not isinstance(parms, list):
            parms = [parms] * len(filters)
        data = st.raw
        for f, prm in zip(filters, parms + [None] * (len(filters) - len(parms))):
            f = self.resolve(f)
            prm = self.resolve(prm) or {}
            if f in ("FlateDecode", "Fl"):
                data = _flate(data)
                pred = int(self.resolve(prm.get("Predictor", 1)) or 1) if isinstance(prm, dict) else 1
                if pred >= 10:
                    data = _png_predict(data, int(self.resolve(prm.get("Columns", 1)) or 1),
                                        int(self.resolve(prm.get("Colors", 1)) or 1),
                                        int(self.resolve(prm.get("BitsPerComponent", 8)) or 8))
            elif f in ("ASCIIHexDecode", "AHx"):
                data = _ahx(data)
            elif f in ("ASCII85Decode", "A85"):
                data = _a85(data)
            else:
                raise PdfError(f"지원하지 않는 압축 방식: {f}")
        return data

    # -------------------------------------------------- 쪽
    def pages(self) -> list[tuple[dict, dict]]:
        """(쪽 사전, 물려받은 Resources) 목록"""
        out: list[tuple[dict, dict]] = []
        seen: set[int] = set()

        def walk(node, res, depth):
            node = self.resolve(node)
            if not isinstance(node, dict) or depth > 64 or id(node) in seen:
                return
            seen.add(id(node))
            r = self.resolve(node.get("Resources"))
            if isinstance(r, dict):
                res = r
            kids = self.resolve(node.get("Kids"))
            if isinstance(kids, list) and node.get("Type") != "Page":
                for k in kids:
                    walk(k, res, depth + 1)
            else:
                out.append((node, res or {}))

        walk(self.root.get("Pages"), {}, 0)
        return out

    def page_content(self, page: dict) -> bytes:
        c = self.resolve(page.get("Contents"))
        parts = c if isinstance(c, list) else [c]
        chunks = []
        for p in parts:
            p = self.resolve(p)
            if isinstance(p, Stream):
                try:
                    chunks.append(self.decode(p))
                except Exception:
                    continue
        return b"\n".join(chunks)


# ============================================================ 글꼴
_GLYPH = {"space": " ", "period": ".", "comma": ",", "hyphen": "-", "parenleft": "(", "parenright": ")",
          "colon": ":", "slash": "/", "bullet": "•", "endash": "–", "emdash": "—",
          "quoteleft": "‘", "quoteright": "’", "quotedblleft": "“", "quotedblright": "”"}


class Font:
    def __init__(self, doc: Document, fd: dict):
        self.cmap: dict[bytes, str] = {}
        self.code_lens: list[int] = [1]
        self.widths: dict[int, float] = {}
        self.dw = 1000.0
        self.cid_font = fd.get("Subtype") == "Type0"
        self.byte_decode = None  # 한글 CMap 등 바이트 해석 방식
        enc = doc.resolve(fd.get("Encoding"))

        if self.cid_font:
            self.code_lens = [2]
            desc = doc.resolve(fd.get("DescendantFonts"))
            if isinstance(desc, list) and desc:
                d0 = doc.resolve(desc[0])
                if isinstance(d0, dict):
                    self.dw = float(doc.resolve(d0.get("DW", 1000)) or 1000)
                    self._parse_w(doc, doc.resolve(d0.get("W")))
            if isinstance(enc, str):
                e = enc.upper()
                if "UCS2" in e or "UTF16" in e:
                    self.byte_decode = "utf-16-be"
                elif "KSC" in e or "UHC" in e:
                    self.byte_decode = "cp949"
                    self.code_lens = [1, 2]
        else:
            first = int(doc.resolve(fd.get("FirstChar", 0)) or 0)
            ws = doc.resolve(fd.get("Widths"))
            if isinstance(ws, list):
                for i, w in enumerate(ws):
                    w = doc.resolve(w)
                    if isinstance(w, (int, float)):
                        self.widths[first + i] = float(w)
            self.dw = 500.0
            self.byte_decode = "cp1252"
            if isinstance(enc, dict):
                diffs = doc.resolve(enc.get("Differences"))
                if isinstance(diffs, list):
                    code = 0
                    for x in diffs:
                        x = doc.resolve(x)
                        if isinstance(x, int):
                            code = x
                        elif isinstance(x, Name):
                            ch = _GLYPH.get(x)
                            if ch is None and re.fullmatch(r"uni[0-9A-Fa-f]{4}", x):
                                ch = chr(int(x[3:], 16))
                            if ch is None and len(x) == 1:
                                ch = x
                            if ch is not None:
                                self.cmap[bytes([code & 0xFF])] = ch
                            code += 1

        tu = doc.resolve(fd.get("ToUnicode"))
        if isinstance(tu, Stream):
            try:
                self._parse_tounicode(doc.decode(tu))
            except Exception:
                pass

    def _parse_w(self, doc: Document, w) -> None:
        if not isinstance(w, list):
            return
        i = 0
        w = [doc.resolve(x) for x in w]
        while i < len(w):
            c = w[i]
            if i + 1 < len(w) and isinstance(w[i + 1], list):
                for k, v in enumerate(w[i + 1]):
                    v = doc.resolve(v)
                    if isinstance(v, (int, float)):
                        self.widths[int(c) + k] = float(v)
                i += 2
            elif i + 2 < len(w):
                lo, hi, v = w[i], w[i + 1], w[i + 2]
                if isinstance(lo, int) and isinstance(hi, int) and isinstance(v, (int, float)) and hi - lo < 70000:
                    for k in range(lo, hi + 1):
                        self.widths[k] = float(v)
                i += 3
            else:
                break

    def _parse_tounicode(self, data: bytes) -> None:
        def u(b: bytes) -> str:
            if len(b) % 2:
                b = b"\x00" + b
            try:
                return b.decode("utf-16-be", "replace")
            except Exception:
                return ""

        lens = set()
        for blk in re.findall(rb"begincodespacerange(.*?)endcodespacerange", data, re.S):
            for lo in re.findall(rb"<([0-9A-Fa-f\s]+)>\s*<[0-9A-Fa-f\s]+>", blk):
                lens.add(len(re.sub(rb"\s", b"", lo)) // 2)
        for blk in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
            for src, dst in re.findall(rb"<([0-9A-Fa-f\s]*)>\s*<([0-9A-Fa-f\s]*)>", blk):
                s = bytes.fromhex(re.sub(rb"\s", b"", src).decode())
                self.cmap[s] = u(bytes.fromhex(re.sub(rb"\s", b"", dst).decode()))
                lens.add(len(s))
        for blk in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
            for lo, hi, rest in re.findall(rb"<([0-9A-Fa-f\s]*)>\s*<([0-9A-Fa-f\s]*)>\s*(<[0-9A-Fa-f\s]*>|\[[^\]]*\])", blk):
                lo_b = bytes.fromhex(re.sub(rb"\s", b"", lo).decode())
                lo_i = int.from_bytes(lo_b, "big") if lo_b else 0
                hi_i = int(re.sub(rb"\s", b"", hi) or b"0", 16)
                n = len(lo_b) or 1
                lens.add(n)
                if hi_i - lo_i > 70000:
                    continue
                if rest.startswith(b"["):
                    dsts = re.findall(rb"<([0-9A-Fa-f\s]*)>", rest)
                    for k, dh in enumerate(dsts):
                        if lo_i + k > hi_i:
                            break
                        self.cmap[(lo_i + k).to_bytes(n, "big")] = u(bytes.fromhex(re.sub(rb"\s", b"", dh).decode()))
                else:
                    db = bytes.fromhex(re.sub(rb"\s", b"", rest[1:-1]).decode())
                    base = int.from_bytes(db, "big") if db else 0
                    for k in range(hi_i - lo_i + 1):
                        self.cmap[(lo_i + k).to_bytes(n, "big")] = u((base + k).to_bytes(max(2, len(db)), "big"))
        if lens and self.byte_decode not in ("cp949",):
            self.code_lens = sorted(lens)

    def iter_codes(self, s: bytes):
        """(코드 바이트, 글자, 너비/1000) 를 하나씩"""
        i, n = 0, len(s)
        while i < n:
            if self.byte_decode == "cp949" and not self.cmap:
                ln = 2 if s[i] >= 0x81 and i + 1 < n else 1
            elif len(self.code_lens) == 1:
                ln = self.code_lens[0]
            else:
                ln = next((L for L in self.code_lens if s[i:i + L] in self.cmap), self.code_lens[-1])
            code = s[i:i + ln]
            i += ln
            ch = self.cmap.get(code)
            if ch is None:
                if self.byte_decode:
                    try:
                        ch = code.decode(self.byte_decode)
                    except Exception:
                        ch = ""
                else:
                    ch = ""
            cid = int.from_bytes(code, "big")
            w = self.widths.get(cid)
            if w is None:
                w = self.dw if not (self.byte_decode == "cp949" and ln == 1) else self.dw / 2
            yield code, ch, w / 1000.0


# ============================================================ 내용 해석
def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


ID = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class _Glyph:
    __slots__ = ("x", "y", "x2", "size", "ch")

    def __init__(self, x, y, x2, size, ch):
        self.x, self.y, self.x2, self.size, self.ch = x, y, x2, size, ch


class _Interp:
    def __init__(self, doc: Document):
        self.doc = doc
        self.glyphs: list[_Glyph] = []
        self.font_cache: dict[int, Font] = {}

    def font(self, res: dict, name):
        fonts = self.doc.resolve(res.get("Font")) if isinstance(res, dict) else None
        if not isinstance(fonts, dict):
            return None
        ref = fonts.get(name)
        fd = self.doc.resolve(ref)
        if not isinstance(fd, dict):
            return None
        key = ref.num if isinstance(ref, Ref) else id(fd)
        if key not in self.font_cache:
            self.font_cache[key] = Font(self.doc, fd)
        return self.font_cache[key]

    def run(self, content: bytes, res: dict, ctm=ID, depth: int = 0) -> None:
        if depth > 8:
            return
        lx = Lexer(content)
        ops: list = []
        st = {"ctm": ctm, "font": None, "size": 0.0, "Tc": 0.0, "Tw": 0.0, "Th": 1.0, "TL": 0.0, "Ts": 0.0}
        stack = []
        tm = tlm = ID
        while True:
            try:
                tok = lx.next(allow_ref=False)
            except StopIteration:
                break
            if not isinstance(tok, Op):
                ops.append(tok)
                if len(ops) > 64:
                    ops = ops[-64:]
                continue
            op = str(tok)
            a = ops
            ops = []
            try:
                if op == "BI":  # 인라인 이미지 건너뛰기
                    m = re.search(rb"\sID[\s]", content[lx.pos:])
                    if m:
                        e = re.search(rb"\sEI(?=[\s]|$)", content[lx.pos + m.end():])
                        lx.pos = lx.pos + m.end() + (e.end() if e else 0)
                elif op == "q":
                    stack.append(dict(st))
                elif op == "Q":
                    if stack:
                        st = stack.pop()
                elif op == "cm" and len(a) >= 6:
                    st["ctm"] = _mul(tuple(float(x) for x in a[-6:]), st["ctm"])
                elif op == "BT":
                    tm = tlm = ID
                elif op == "Tf" and len(a) >= 2:
                    st["font"] = self.font(res, a[-2])
                    st["size"] = float(a[-1])
                elif op == "Tc" and a:
                    st["Tc"] = float(a[-1])
                elif op == "Tw" and a:
                    st["Tw"] = float(a[-1])
                elif op == "Tz" and a:
                    st["Th"] = float(a[-1]) / 100.0
                elif op == "TL" and a:
                    st["TL"] = float(a[-1])
                elif op == "Ts" and a:
                    st["Ts"] = float(a[-1])
                elif op in ("Td", "TD") and len(a) >= 2:
                    tx, ty = float(a[-2]), float(a[-1])
                    if op == "TD":
                        st["TL"] = -ty
                    tlm = _mul((1, 0, 0, 1, tx, ty), tlm)
                    tm = tlm
                elif op == "Tm" and len(a) >= 6:
                    tlm = tm = tuple(float(x) for x in a[-6:])
                elif op == "T*":
                    tlm = _mul((1, 0, 0, 1, 0, -st["TL"]), tlm)
                    tm = tlm
                elif op == "Tj" and a:
                    tm = self.show(a[-1], st, tm)
                elif op == "'" and a:
                    tlm = _mul((1, 0, 0, 1, 0, -st["TL"]), tlm)
                    tm = self.show(a[-1], st, tlm)
                elif op == '"' and len(a) >= 3:
                    st["Tw"], st["Tc"] = float(a[-3]), float(a[-2])
                    tlm = _mul((1, 0, 0, 1, 0, -st["TL"]), tlm)
                    tm = self.show(a[-1], st, tlm)
                elif op == "TJ" and a and isinstance(a[-1], list):
                    for el in a[-1]:
                        if isinstance(el, bytes):
                            tm = self.show(el, st, tm)
                        elif isinstance(el, (int, float)):
                            tx = -float(el) / 1000.0 * st["size"] * st["Th"]
                            tm = _mul((1, 0, 0, 1, tx, 0), tm)
                elif op == "Do" and a:
                    self.do_xobject(res, a[-1], st["ctm"], depth)
            except (TypeError, ValueError, IndexError):
                continue

    def do_xobject(self, res, name, ctm, depth):
        xo = self.doc.resolve(res.get("XObject")) if isinstance(res, dict) else None
        if not isinstance(xo, dict):
            return
        obj = self.doc.resolve(xo.get(name))
        if not isinstance(obj, Stream) or obj.dict.get("Subtype") != "Form":
            return
        mat = self.doc.resolve(obj.dict.get("Matrix"))
        m = tuple(float(self.doc.resolve(x)) for x in mat) if isinstance(mat, list) and len(mat) == 6 else ID
        sub_res = self.doc.resolve(obj.dict.get("Resources"))
        try:
            data = self.doc.decode(obj)
        except Exception:
            return
        self.run(data, sub_res if isinstance(sub_res, dict) else res, _mul(m, ctm), depth + 1)

    def show(self, s, st, tm):
        font = st["font"]
        if not isinstance(s, bytes) or font is None:
            return tm
        size, th = st["size"], st["Th"]
        for code, ch, w in font.iter_codes(s):
            trm = _mul((size * th, 0, 0, size, 0, st["Ts"]), _mul(tm, st["ctm"]))
            fsize = (trm[2] ** 2 + trm[3] ** 2) ** 0.5 or abs(size)
            tx = (w * size + st["Tc"] + (st["Tw"] if code == b" " else 0.0)) * th
            x, y = trm[4], trm[5]
            # 글자 끝 위치 = 글자 너비만큼 이동한 지점
            end = _mul((1, 0, 0, 1, w * size * th, 0), _mul(tm, st["ctm"]))
            if ch and ch not in "\x00":
                self.glyphs.append(_Glyph(x, y, end[4], fsize, ch))
            tm = _mul((1, 0, 0, 1, tx, 0), tm)
        return tm


class Line:
    """한 줄의 글자와 위치. xs[i] 는 text[i] 글자의 왼쪽 x 좌표(pt), y 는 기준선(위로 갈수록 큼)."""
    __slots__ = ("text", "xs", "y", "size")

    def __init__(self, text: str, xs: list[float], y: float, size: float):
        self.text, self.xs, self.y, self.size = text, xs, y, size

    @property
    def x0(self) -> float:
        return self.xs[0] if self.xs else 0.0

    def __repr__(self):
        return f"Line(x0={self.x0:.0f}, y={self.y:.0f}, {self.text!r})"


def _to_lines(glyphs: list[_Glyph]) -> list[Line]:
    """글자 위치로 줄을 묶어 위→아래, 왼→오 순서로 만든다."""
    if not glyphs:
        return []
    gs = sorted(glyphs, key=lambda g: -g.y)
    groups: list[list[_Glyph]] = []
    for g in gs:
        tol = max(g.size * 0.45, 1.0)
        if groups and abs(groups[-1][0].y - g.y) <= tol:
            groups[-1].append(g)
        else:
            groups.append([g])
    out: list[Line] = []
    for grp in groups:
        grp.sort(key=lambda g: g.x)
        chars: list[str] = []
        xs: list[float] = []
        prev = None
        for g in grp:
            if prev is not None:
                # 굵게 표현용으로 같은 글자를 겹쳐 찍은 것은 하나만
                if g.ch == prev.ch and abs(g.x - prev.x) < g.size * 0.3:
                    continue
                gap = g.x - prev.x2
                if gap > g.size * 0.22 and chars and chars[-1] != " " and not g.ch[:1].isspace():
                    chars.append(" ")
                    xs.append(prev.x2)
            for c in g.ch:
                if c.isspace():
                    if not chars or chars[-1] == " ":
                        continue
                    c = " "
                chars.append(c)
                xs.append(g.x)
            prev = g
        while chars and chars[-1] == " ":
            chars.pop()
            xs.pop()
        if chars:
            size = sorted(g.size for g in grp)[len(grp) // 2]
            out.append(Line("".join(chars), xs, grp[0].y, size))
    return out


def read_pdf_lines(path, max_pages: int = 40) -> list[list[Line]]:
    """PDF 쪽별 줄 목록. 쪽이 많으면 앞/뒤 일부만 읽는다(제목은 앞, 시행란은 뒤)."""
    with open(path, "rb") as f:
        data = f.read()
    doc = Document(data)
    pages = doc.pages()
    if not pages:
        raise PdfError("쪽(page)을 찾지 못했습니다")
    want = set(range(len(pages)))
    if len(pages) > max_pages:
        half = max_pages // 2
        want = set(range(half)) | set(range(len(pages) - half, len(pages)))
    out: list[list[Line]] = []
    for i, (page, res) in enumerate(pages):
        if i not in want:
            out.append([])
            continue
        interp = _Interp(doc)
        try:
            interp.run(doc.page_content(page), res)
        except Exception:
            pass
        out.append(_to_lines(interp.glyphs))
    return out


def read_pdf_text(path, max_pages: int = 40) -> list[str]:
    """PDF 쪽별 글자(줄 단위 문자열)."""
    return ["\n".join(ln.text for ln in page) for page in read_pdf_lines(path, max_pages)]


if __name__ == "__main__":
    import sys

    for p in sys.argv[1:]:
        for i, t in enumerate(read_pdf_text(p), 1):
            print(f"===== {p} [{i}쪽]")
            print(t)
