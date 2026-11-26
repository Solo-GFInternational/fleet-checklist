"""Build a Word document of QR codes, one per registered truck, for testing
the barcode scanner on the Fleet Checklist app's Home screen.

Usage:
    py -3 -I scripts/build_truck_qr_doc.py "files/Fleet Trucks.csv" files

Arguments:
    1. The trucks CSV (header Truck,Type,Make,Tyres,COF).
    2. The output folder. Writes "Fleet Trucks - QR codes.docx" there.

Each code holds the truck number the way the app writes it, with a space after
the 2-letter prefix ("FU806" -> "FU 806"). One extra code, "ZZ 999", is added
at the end as a deliberately unregistered truck.

Standard library only: the QR encoder (byte mode, error correction M,
versions 1-3), the PNG writer and the .docx (a zip of WordprocessingML parts)
are all written by hand here.
"""

import csv
import os
import struct
import sys
import zipfile
import zlib
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# QR encoder: byte mode, EC level M, versions 1-3 (one RS block each)
# ---------------------------------------------------------------------------

# version: (total data codewords, EC codewords, alignment centre or None)
VERSIONS_M = {
    1: (16, 10, None),
    2: (28, 16, 18),
    3: (44, 26, 22),
}
EC_LEVEL_BITS_M = 0b00  # L=01, M=00, Q=11, H=10

# GF(256) tables, primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D)
GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    GF_EXP[_i] = GF_EXP[_i - 255]


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


def rs_generator(degree):
    """Coefficients of prod_{i<degree}(x - a^i), highest power first, leading 1 dropped."""
    gen = [1]
    for i in range(degree):
        nxt = [0] * (len(gen) + 1)
        for j, c in enumerate(gen):
            nxt[j] ^= c
            nxt[j + 1] ^= gf_mul(c, GF_EXP[i])
        gen = nxt
    return gen[1:]


def rs_ec(data, degree):
    """Reed-Solomon error-correction codewords for one block."""
    gen = rs_generator(degree)
    rem = [0] * degree
    for b in data:
        factor = b ^ rem.pop(0)
        rem.append(0)
        for i, c in enumerate(gen):
            rem[i] ^= gf_mul(c, factor)
    return rem


def format_bits(ec_bits, mask):
    """15-bit format information (BCH(15,5) with 0x537, XOR 0x5412)."""
    data = (ec_bits << 3) | mask
    rem = data << 10
    for i in range(14, 9, -1):
        if rem & (1 << i):
            rem ^= 0x537 << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def data_codewords(payload, version):
    capacity, _, _ = VERSIONS_M[version]
    bits = []

    def put(value, n):
        for i in range(n - 1, -1, -1):
            bits.append((value >> i) & 1)

    put(0b0100, 4)            # byte mode
    put(len(payload), 8)      # character count (8 bits for versions 1-9)
    for b in payload:
        put(b, 8)
    put(0, min(4, capacity * 8 - len(bits)))  # terminator
    while len(bits) % 8:
        bits.append(0)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    while len(words) < capacity:
        words.append(pad[(len(words) - len(bits) // 8) % 2])
    return words


MASKS = [
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: (x * y) % 2 + (x * y) % 3 == 0,
    lambda x, y: ((x * y) % 2 + (x * y) % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + (x * y) % 3) % 2 == 0,
]


class QR:
    def __init__(self, version):
        self.version = version
        self.size = 17 + 4 * version
        n = self.size
        self.m = [[0] * n for _ in range(n)]       # m[y][x], 1 = dark
        self.fn = [[False] * n for _ in range(n)]  # function-pattern modules

    def set_fn(self, x, y, dark):
        self.m[y][x] = 1 if dark else 0
        self.fn[y][x] = True

    def draw_function_patterns(self):
        n = self.size
        for i in range(n):  # timing patterns
            self.set_fn(6, i, i % 2 == 0)
            self.set_fn(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):  # finders + separators
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        d = max(abs(dx), abs(dy))
                        self.set_fn(x, y, d not in (2, 4))
        align = VERSIONS_M[self.version][2]
        if align:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    self.set_fn(align + dx, align + dy, max(abs(dx), abs(dy)) != 1)
        self.draw_format(0)  # reserve the format areas (overwritten later)

    def draw_format(self, mask):
        n = self.size
        bits = format_bits(EC_LEVEL_BITS_M, mask)
        bit = lambda i: (bits >> i) & 1
        # copy 1, around the top-left finder
        for i in range(6):
            self.set_fn(8, i, bit(i))
        self.set_fn(8, 7, bit(6))
        self.set_fn(8, 8, bit(7))
        self.set_fn(7, 8, bit(8))
        for i in range(9, 15):
            self.set_fn(14 - i, 8, bit(i))
        # copy 2, split between top-right and bottom-left finders
        for i in range(8):
            self.set_fn(n - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.set_fn(8, n - 15 + i, bit(i))
        self.set_fn(8, n - 8, 1)  # dark module

    def place_data(self, codewords):
        n = self.size
        bits = []
        for w in codewords:
            bits.extend((w >> i) & 1 for i in range(7, -1, -1))
        i = 0
        right = n - 1
        while right >= 1:
            if right == 6:
                right = 5
            upward = ((right + 1) & 2) == 0
            for vert in range(n):
                y = n - 1 - vert if upward else vert
                for j in range(2):
                    x = right - j
                    if not self.fn[y][x]:
                        self.m[y][x] = bits[i] if i < len(bits) else 0  # remainder bits = 0
                        i += 1
            right -= 2
        assert i >= len(bits)

    def apply_mask(self, mask):
        f = MASKS[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.fn[y][x] and f(x, y):
                    self.m[y][x] ^= 1

    def penalty(self):
        n = self.size
        m = self.m
        score = 0
        lines = [row[:] for row in m] + [[m[y][x] for y in range(n)] for x in range(n)]
        for line in lines:
            # rule 1: runs of 5+ same colour
            run = 1
            for k in range(1, n + 1):
                if k < n and line[k] == line[k - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + (run - 5)
                    run = 1
            # rule 3: finder-like 1:1:3:1:1 with 4 light modules either side
            s = "".join(map(str, line))
            for pat in ("10111010000", "00001011101"):
                start = s.find(pat)
                while start != -1:
                    score += 40
                    start = s.find(pat, start + 1)
        # rule 2: 2x2 blocks
        for y in range(n - 1):
            for x in range(n - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        # rule 4: dark/light balance
        dark = sum(map(sum, m))
        total = n * n
        score += 10 * (abs(dark * 100 // total - 50) // 5)
        return score


def choose_version(length):
    for v in sorted(VERSIONS_M):
        # 4 mode bits + 8 count bits + 8 per byte must fit
        if 12 + 8 * length <= VERSIONS_M[v][0] * 8:
            return v
    raise ValueError("text too long for versions 1-3 at level M")


def encode(text):
    """Return (matrix as list of rows of 0/1, version, mask). No quiet zone."""
    payload = text.encode("utf-8")
    version = choose_version(len(payload))
    data = data_codewords(payload, version)
    codewords = data + rs_ec(data, VERSIONS_M[version][1])
    best = None
    for mask in range(8):
        q = QR(version)
        q.draw_function_patterns()
        q.place_data(codewords)
        q.apply_mask(mask)
        q.draw_format(mask)
        p = q.penalty()
        if best is None or p < best[0]:
            best = (p, q, mask)
    _, q, mask = best
    return q.m, version, mask


# ---------------------------------------------------------------------------
# PNG writer (8-bit greyscale)
# ---------------------------------------------------------------------------

def png_bytes(matrix, scale=10, quiet=4):
    n = len(matrix)
    side = (n + 2 * quiet) * scale
    raw = bytearray()
    for py in range(side):
        my = py // scale - quiet
        raw.append(0)  # filter type: none
        for px in range(side):
            mx = px // scale - quiet
            dark = 0 <= mx < n and 0 <= my < n and matrix[my][mx]
            raw.append(0 if dark else 255)

    def chunk(tag, body):
        c = tag + body
        return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# .docx writer
# ---------------------------------------------------------------------------

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

IMG_EMU = 1440000          # 4 cm
COL_TWIPS = 3212           # 3 columns across 17 cm of A4 text width
GREY = "606C76"


def run(text, size_half_pts, bold=False, color=None):
    props = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
    if bold:
        props += "<w:b/>"
    if color:
        props += '<w:color w:val="%s"/>' % color
    props += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size_half_pts, size_half_pts)
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (props, escape(text))


def para(content, center=True, after=0, keep_next=False):
    ppr = ""
    if keep_next:
        ppr += "<w:keepNext/>"
    ppr += '<w:spacing w:before="0" w:after="%d"/>' % after
    if center:
        ppr += '<w:jc w:val="center"/>'
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (ppr, content)


def image_run(rid, pic_id, name):
    return (
        '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="{e}" cy="{e}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="{id}" name="{n}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="{id}" name="{n}"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{e}" cy="{e}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
    ).format(e=IMG_EMU, id=pic_id, n=escape(name, {'"': "&quot;"}), rid=rid)


def cell(inner):
    return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>%s</w:tc>'
            % (COL_TWIPS, inner or "<w:p/>"))


def build_docx(path, items):
    """items: list of (code_text, caption_bold, caption_grey, png_bytes)."""
    rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]
    cells = []
    media = []
    for i, (_, bold, grey, png) in enumerate(items, start=1):
        rid = "rIdImg%d" % i
        fname = "qr%02d.png" % i
        media.append((fname, png))
        rels.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/%s"/>'
                    % (rid, fname))
        inner = (para(image_run(rid, i, "QR " + bold), after=60, keep_next=True)
                 + para(run(bold, 28, bold=True), after=20, keep_next=True)
                 + para(run(grey, 18, color=GREY), after=240))
        cells.append(cell(inner))
    while len(cells) % 3:
        cells.append(cell(""))

    rows = "".join(
        '<w:tr><w:trPr><w:cantSplit/></w:trPr>%s</w:tr>' % "".join(cells[i:i + 3])
        for i in range(0, len(cells), 3))
    none = "".join('<w:%s w:val="nil"/>' % s for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>'
        '<w:tblBorders>%s</w:tblBorders><w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="120" w:type="dxa"/><w:left w:w="57" w:type="dxa"/>'
        '<w:right w:w="57" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblGrid>%s</w:tblGrid>%s</w:tbl>'
        % (COL_TWIPS * 3, none, '<w:gridCol w:w="%d"/>' % COL_TWIPS * 3, rows))

    body = (
        para(run("GF Fleet Trucks – QR codes (test)", 36, bold=True, color="007070"), center=False, after=80)
        + para(run("Scan with the Fleet Checklist app on the Home screen. "
                   "Each code contains the truck number.", 20, color=GREY), center=False, after=240)
        + table
        + '<w:p/><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
          '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
          'w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document %s><w:body>%s</w:body></w:document>' % (NS, body))

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr>'
        '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Arial" w:cs="Arial"/>'
        '<w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="en-NZ"/>'
        '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="0"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/>'
        '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
        '<w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
        '</w:tblCellMar></w:tblPr></w:style>'
        '</w:styles>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>')
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + "".join(rels) + '</Relationships>')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        for fname, png in media:
            z.writestr("word/media/" + fname, png)


# ---------------------------------------------------------------------------

def app_format(truck):
    """Same as the app: strip spaces/hyphens, upper-case, 'XX 123'."""
    t = truck.replace(" ", "").replace("-", "").upper()
    return t[:2] + " " + t[2:12]


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    csv_path, out_dir = argv[1], argv[2]
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        trucks = [r for r in csv.DictReader(f) if (r.get("Truck") or "").strip()]

    items = []
    for r in trucks:
        code = app_format(r["Truck"].strip())
        matrix, _, _ = encode(code)
        items.append((code, code, (r.get("Make") or "").strip(), png_bytes(matrix)))
    bad = "ZZ 999"
    matrix, _, _ = encode(bad)
    items.append((bad, bad, "Not a registered truck (should show 'Vehicle not found')", png_bytes(matrix)))

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Fleet Trucks - QR codes.docx")
    build_docx(out, items)
    print("Wrote %s (%d trucks + 1 invalid test code)" % (out, len(trucks)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
