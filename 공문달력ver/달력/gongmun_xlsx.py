# -*- coding: utf-8 -*-
"""
gongmun_xlsx.py  -  추가 설치 없이 엑셀(.xlsx) 파일 만들기

엑셀 파일은 사실 XML 파일 몇 개를 zip 으로 묶은 것이라, 파이썬 기본 모듈만으로 만들 수 있다.
  - 첫 줄(제목줄)은 굵게 + 파란 배경, 틀 고정, 자동 필터
  - 줄마다 상태 색: done(회색), late(빨강), soon(노랑)
"""
import zipfile
from xml.sax.saxutils import escape

# 스타일 번호 (아래 STYLES 의 cellXfs 순서)
_STYLE_IDX = {"head": 1, "": 2, "done": 3, "late": 4, "soon": 5}

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="4">
 <font><sz val="10"/><name val="맑은 고딕"/></font>
 <font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="맑은 고딕"/></font>
 <font><sz val="10"/><color rgb="FF888888"/><strike/><name val="맑은 고딕"/></font>
 <font><sz val="10"/><color rgb="FFA12622"/><name val="맑은 고딕"/></font>
</fonts>
<fills count="5">
 <fill><patternFill patternType="none"/></fill>
 <fill><patternFill patternType="gray125"/></fill>
 <fill><patternFill patternType="solid"><fgColor rgb="FF2F6FED"/></patternFill></fill>
 <fill><patternFill patternType="solid"><fgColor rgb="FFFDE2E1"/></patternFill></fill>
 <fill><patternFill patternType="solid"><fgColor rgb="FFFFF3CD"/></patternFill></fill>
</fills>
<borders count="2">
 <border><left/><right/><top/><bottom/><diagonal/></border>
 <border><left style="thin"><color rgb="FFD0D5DD"/></left><right style="thin"><color rgb="FFD0D5DD"/></right><top style="thin"><color rgb="FFD0D5DD"/></top><bottom style="thin"><color rgb="FFD0D5DD"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6">
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
 <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
 <xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
 <xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
 <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _col(n):
    """0 -> A, 25 -> Z, 26 -> AA"""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _clean(v):
    text = "" if v is None else str(v)
    return "".join(ch for ch in text if ch in "\t\n" or ord(ch) >= 32)   # XML 에 못 넣는 글자 제거


def write_xlsx(path, sheet_name, headers, rows, row_styles=None, widths=None):
    row_styles = row_styles or [""] * len(rows)
    last = _col(len(headers) - 1)
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
           '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="18"/>']
    if widths:
        out.append("<cols>" + "".join('<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, w)
                                      for i, w in enumerate(widths)) + "</cols>")
    out.append("<sheetData>")
    for r, (vals, st) in enumerate([(headers, "head")] + list(zip(rows, row_styles)), start=1):
        s = _STYLE_IDX.get(st, 2)
        cells = "".join('<c r="%s%d" t="inlineStr" s="%d"><is><t xml:space="preserve">%s</t></is></c>'
                        % (_col(c), r, s, escape(_clean(v))) for c, v in enumerate(vals))
        out.append('<row r="%d"%s>%s</row>' % (r, ' ht="22" customHeight="1"' if r == 1 else "", cells))
    out.append("</sheetData>")
    out.append('<autoFilter ref="A1:%s%d"/>' % (last, len(rows) + 1))
    out.append("</worksheet>")

    name = escape(sheet_name[:31])
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets>'
            '<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">\'%s\'!$A$1:$%s$%d</definedName></definedNames>'
            '</workbook>' % (name, name, last, len(rows) + 1),
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>',
        "xl/styles.xml": STYLES,
        "xl/worksheets/sheet1.xml": "".join(out),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
