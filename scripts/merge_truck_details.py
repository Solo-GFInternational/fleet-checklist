"""Merge the office's truck spreadsheet into the CSV that create_trucks_list.js imports.

Reads the "Details" and "Tires" sheets of the truck workbook, matches rows by registration
(column A, "Veh #") and writes "<output folder>/Fleet Trucks.csv" with the header
    Truck,Type,Make,Tyres,COF

    Truck  registration as in the sheet (the JS script writes it as "FU 806")
    Type   Details column B: Dry -> Ambient, Freezer -> Frozen (the list's choices; the app checks "Frozen")
    Make   Details column C ("Type"); the Tires sheet's Type is used only when Details has none
    Tyres  Tires column D ("No of Tyres (Inclusive Spare)") minus 1, so the spare is not photographed
    COF    Details column F (an Excel date) as yyyy-mm-dd; left blank if it is not a sensible date

Blower service due and Truck service due are not in the workbook; reviewers fill them in SharePoint.

Usage:  py -3 -I scripts/merge_truck_details.py "files/Truck Details updated.xlsx" files
Needs only the Python standard library (reads the .xlsx XML directly).
"""
import csv
import datetime as dt
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
TYPE_MAP = {'dry': 'Ambient', 'ambient': 'Ambient', 'freezer': 'Frozen', 'frozen': 'Frozen'}


def read_sheets(path):
    """Return {sheet name: [ {column letter: text} per row ]}."""
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheets = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
        target = rels[s.get('{%s}id' % NS['r'])].lstrip('/')
        if not target.startswith('xl/'):
            target = 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter('{%s}row' % NS['m']):
            cells = {}
            for c in row.findall('m:c', NS):
                col = re.match(r'[A-Z]+', c.get('r')).group()
                v = c.find('m:v', NS)
                if c.get('t') == 's' and v is not None:
                    val = shared[int(v.text)]
                elif c.get('t') == 'inlineStr':
                    val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
                else:
                    val = v.text if v is not None else ''
                cells[col] = (val or '').strip()
            rows.append(cells)
        sheets[s.get('name')] = rows
    return sheets


def by_rego(rows):
    out = {}
    for r in rows[1:]:  # row 1 is the header
        rego = re.sub(r'[\s-]', '', r.get('A', '')).upper()
        if re.fullmatch(r'[A-Z]{2}\d{1,6}', rego):
            out[rego] = r
    return out


def excel_date(v):
    try:
        d = dt.date(1899, 12, 30) + dt.timedelta(days=int(float(v)))
    except (ValueError, OverflowError):
        return None
    return d if 2000 <= d.year <= 2100 else None


def clean(s):
    return re.sub(r'\s+', ' ', s.replace(',', ' ')).strip()


def main(xlsx, outdir):
    sheets = read_sheets(xlsx)
    details, tires = by_rego(sheets['Details']), by_rego(sheets['Tires'])
    notes, rows = [], []
    for rego in sorted(details):
        d, t = details[rego], tires.get(rego)
        if t is None:
            notes.append(f'{rego}: not on the Tires sheet, number of tyres left blank')
        type_ = TYPE_MAP.get(d.get('B', '').lower())
        if not type_:
            notes.append(f'{rego}: truck type "{d.get("B", "")}" not Dry/Freezer, left blank')
        make = clean(d.get('C', '') or (t or {}).get('B', ''))
        if t and clean(t.get('B', '')) and clean(t.get('B', '')).lower() != make.lower():
            notes.append(f'{rego}: Make differs (Details "{make}", Tires "{clean(t["B"])}"), Details used')
        if type_ and re.search(r'freezer|dry', make, re.I) and type_ != ('Frozen' if re.search('freezer', make, re.I) else 'Ambient'):
            notes.append(f'{rego}: type "{d.get("B")}" but make says "{make}", please check')
        tyres = ''
        if t and t.get('D', '').isdigit():
            tyres = str(int(t['D']) - 1)
        cof = excel_date(d.get('F', ''))
        if d.get('F') and not cof:
            notes.append(f'{rego}: COF value "{d["F"]}" is not a sensible date, left blank')
        rows.append([rego, type_ or '', make, tyres, cof.isoformat() if cof else ''])
    for rego in sorted(set(tires) - set(details)):
        notes.append(f'{rego}: on the Tires sheet only, not imported')

    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, 'Fleet Trucks.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['Truck', 'Type', 'Make', 'Tyres', 'COF'])
        w.writerows(rows)
    print(f'wrote {path} ({len(rows)} trucks)')
    xpath = os.path.join(outdir, 'Fleet Trucks - SharePoint list.xlsx')
    write_xlsx(xpath, rows, notes)
    print(f'wrote {xpath}')
    for n in notes:
        print('NOTE', n)


# ---------------------------------------------------------------- spreadsheet (standard library only)
LIST_COLS = [  # (header = SharePoint display name, internal name, width)
    ('Truck number', 'Title', 14), ('Truck type', 'TruckType', 12), ('Make', 'Make', 32),
    ('Number of tyres', 'NoOfTyres', 16), ('Active', 'ActiveYN', 9), ('COF expiry', 'COFExpiry', 13),
    ('Blower service due', 'BlowerServiceDue', 19), ('Truck service due', 'TruckServiceDue', 18)]


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def _col(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, value, style, kind='s'):
    if value is None or value == '':
        return f'<c r="{ref}" s="{style}"/>'
    if kind == 'n':
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{_esc(value)}</t></is></c>'


STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts>
<fonts count="4">
<font><sz val="10"/><name val="Arial"/></font>
<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>
<font><b/><sz val="12"/><color rgb="FF007070"/><name val="Arial"/></font>
<font><b/><sz val="10"/><name val="Arial"/></font>
</fonts>
<fills count="5">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF089090"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2B3"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF8CBAD"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFD0D8DA"/></left><right style="thin"><color rgb="FFD0D8DA"/></right><top style="thin"><color rgb="FFD0D8DA"/></top><bottom style="thin"><color rgb="FFD0D8DA"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="11">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="1" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="164" fontId="0" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def _sheet(rows_xml, cols_xml, extra='', freeze=False):
    pane = ('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>') if freeze else '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{pane}<sheetFormatPr defaultRowHeight="15"/><cols>{cols_xml}</cols>'
            f'<sheetData>{rows_xml}</sheetData>{extra}</worksheet>')


def write_xlsx(path, rows, notes):
    """Sheet 1 'Trucks': one row per truck, columns = the GF Fleet Trucks list. Sheet 2 'Read me'."""
    flagged_type = {n.split(':')[0] for n in notes if 'please check' in n}
    n = len(rows)
    out = ['<row r="1" ht="30" customHeight="1">' +
           ''.join(_cell(f'{_col(i)}1', h, 1) for i, (h, _, _) in enumerate(LIST_COLS)) + '</row>']
    for r, (rego, type_, make, tyres, cof) in enumerate(rows, start=2):
        truck = f'{rego[:2]} {rego[2:]}'
        cof_serial = (dt.date.fromisoformat(cof) - dt.date(1899, 12, 30)).days if cof else ''
        cells = [
            _cell(f'A{r}', truck, 2),
            _cell(f'B{r}', type_, 6 if rego in flagged_type else 7),
            _cell(f'C{r}', make, 2),
            _cell(f'D{r}', tyres, 3, 'n'),
            _cell(f'E{r}', 'Yes', 7),
            _cell(f'F{r}', cof_serial, 4 if cof else 5, 'n'),
            _cell(f'G{r}', '', 5),
            _cell(f'H{r}', '', 5),
        ]
        out.append(f'<row r="{r}">' + ''.join(cells) + '</row>')
    last = n + 1
    cols = ''.join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, (_, _, w) in enumerate(LIST_COLS))
    dv = (f'<autoFilter ref="A1:H{last}"/>'
          '<dataValidations count="3">'
          f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="B2:B{last}"><formula1>"Ambient,Frozen"</formula1></dataValidation>'
          f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="E2:E{last}"><formula1>"Yes,No"</formula1></dataValidation>'
          f'<dataValidation type="whole" allowBlank="1" showErrorMessage="1" sqref="D2:D{last}"><formula1>1</formula1><formula2>30</formula2></dataValidation>'
          '</dataValidations>')
    trucks = _sheet(''.join(out), cols, dv, freeze=True)

    info = [('GF Fleet Trucks: import sheet', 8), ('', 0),
            ('Each column matches a column of the GF Fleet Trucks SharePoint list (header = display name).', 9),
            ('Made from the office truck workbook (Details and Tires sheets, matched by registration) by scripts/merge_truck_details.py.', 9),
            ('', 0), ('Column sources', 10),
            ('Truck number: Details column A, written as the app writes it ("FU806" -> "FU 806").', 9),
            ('Truck type: Details column B. Dry -> Ambient, Freezer -> Frozen (the list\'s choices; Frozen shows the freezer items).', 9),
            ('Make: Details column C ("Type").', 9),
            ('Number of tyres: Tires column D (inclusive of spare) minus 1; the app asks for one photo per tyre.', 9),
            ('Active: Yes for every truck. Set No instead of deleting a truck.', 9),
            ('COF expiry: Details column F.', 9),
            ('Blower service due / Truck service due: not in the workbook; reviewers fill them in SharePoint.', 9),
            ('', 0), ('Colours', 10),
            ('Yellow cell: to be filled in (missing date).', 9),
            ('Orange cell: please check (truck type disagrees with the make).', 9),
            ('', 0), ('To check', 10)] + [(x, 9) for x in notes]
    info_rows = ''.join(f'<row r="{i}">' + _cell(f'A{i}', t, s) + '</row>' for i, (t, s) in enumerate(info, start=1))
    readme = _sheet(info_rows, '<col min="1" max="1" width="110" customWidth="1"/>')

    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          '<sheet name="Trucks" sheetId="1" r:id="rId1"/><sheet name="Read me" sheetId="2" r:id="rId2"/></sheets>'
          f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">Trucks!$A$1:$H${last}</definedName></definedNames>'
          '</workbook>')
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    files = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{rel}/worksheet" Target="worksheets/sheet2.xml"/>'
            f'<Relationship Id="rId3" Type="{rel}/styles" Target="styles.xml"/></Relationships>',
        'xl/workbook.xml': wb,
        'xl/styles.xml': STYLES,
        'xl/worksheets/sheet1.xml': trucks,
        'xl/worksheets/sheet2.xml': readme,
    }
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
