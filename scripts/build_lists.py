"""Build Excel starter files for creating the SharePoint lists
(SharePoint / Microsoft Lists: + New -> List -> From Excel).

Each workbook has:
  - Sheet "List": an Excel table whose headers become the list's columns,
    with one sample row so SharePoint can guess each column's type.
    Delete the sample row after the list is created.
  - Sheet "Column guide": each column's friendly label, the SharePoint
    type to pick in the import screen, and the choices for Choice columns.

Headers are short with no spaces or symbols on purpose: SharePoint fixes a
column's internal name when it's created, and Power Apps uses that name.
Friendlier labels can be set afterwards without breaking anything.

Written by hand (zipfile + XML) because pip can't reach PyPI from this
laptop. Usage: python build_lists.py <out_dir>
"""
import re, sys, zipfile, datetime
from xml.sax.saxutils import escape

OUT = sys.argv[1]

TEXT, NOTE, NUM, DATE, CHOICE = "Single line of text", "Multiple lines of text", "Number", "Date and time (date only)", "Choice"
YN = ["Yes", "No"]
SAMPLE_DATE = datetime.date(2026, 10, 21)

# (internal name, label, type, choices, sample value)
# One Yes/No column per checklist item (23 Oct 2026), mirroring the form's
# one-question-per-item layout. Keys start with the section so the columns
# group together and stay unique if SharePoint shortens the internal name.
SECTIONS = [
    ("Engine", "Engine and Transmission", [
        ("Eng01OilLevels", "Oil Levels Engine Hydraulics (Top Level)"),
        ("Eng02CoolantLevels", "Coolant Levels (Top Mark)"),
        ("Eng03FanBelts", "Fan Belts (Alternator, Cooling Fan, A/C etc.)"),
        ("Eng04OilWaterLeaks", "Oil / Water Leaks"),
        ("Eng05PTO", "PTO (Pump, Seals, Cable, Shaft, Augers, Universal Joint)"),
    ]),
    ("Electrical", "Electrical System", [
        ("Elec01BatteryWater", "Battery Water Level (Top Mark)"),
        ("Elec02BatteryTerminals", "Battery Terminals (No Loose Terminals / Acid Build Up)"),
        ("Elec03IsolatorSwitch", "Battery Master Isolator Switch"),
        ("Elec04HeadFogLights", "Head / Fog Light (Left and Right) Functional"),
        ("Elec05Indicators", "Indicators (Left/Right & Front/Rear Truck) (Functional)"),
        ("Elec06BrakeLights", "Brake Lights (Left & Right, Truck) (Functional)"),
        ("Elec07ReverseAlarm", "Reverse Alarm / Lights (Left & Right Truck) (Functional)"),
        ("Elec08CabinSpotLight", "Cabin Interior Spot Light (Functional)"),
        ("Elec09RearSpotLight", "Rear Spot Light (Functional)"),
        ("Elec10Horn", "Horn (Functional)"),
        ("Elec11Cables", "Truck / Bulk Bin Electrical Cables (Damage Free)"),
        ("Elec12DashGauges", "Cabin Dashboard Gauges / Meters (Functional)"),
    ]),
    ("Body", "Body and Chassis", [
        ("Body01DoorsLocks", "Cabin Doors / Windows / Locks (Functional)"),
        ("Body02Windscreens", "Front / Rear Windscreens (Free of Cracks)"),
        ("Body03Mirrors", "Rear Vision Mirrors / Immediate Vicinity Check Mirrors"),
        ("Body04SeatBelts", "Driver / Passenger Seat Belts (Functional)"),
        ("Body05SpringsBolts", "Springs / U-Bolts / Bin Mounting Nuts and Bolts"),
        ("Body06Bumpers", "Front and Rear Bumpers – Impact Absorption"),
    ]),
    ("Brakes", "Brakes and Tyres", [
        ("Brk01ServiceParkBrake", "Service / Park Brake Condition"),
        ("Brk02AirHoses", "Air Hoses Condition (Any Signs of Leaks)"),
        ("Brk03Tyres", "Tyre Condition (Any Retreads on Steer Wheels)"),
        ("Brk04WheelStuds", "Wheel Studs (All Present)"),
        ("Brk05SpareTyre", "Spare Tyre (In Good Condition)"),
        ("Brk06JackBrace", "Jack / Wheel Brace / Accessories (All Present and Functional)"),
    ]),
    ("Safety", "Safety Devices", [
        ("Safe01ConesReflector", "Cones & Reflector"),
        ("Safe02DriverPPE", "Drivers PPE (All Present)"),
        ("Safe03FireExtinguishers", "Fire Extinguishers (Present / Functional)"),
        ("Safe04FirstAid", "First Aid Box (Present and Stocked)"),
        ("Safe05HandTorch", "Hand Torch (Operational)"),
        ("Safe06RainCoatHelmet", "Rain Coat and Helmet (Present / Good Condition)"),
    ]),
    ("General", "General", [
        ("Gen01Greasing", "Greasing Has Been Carried Out to Moving / Rotating Parts"),
        ("Gen02AngleBlocks", "Braking Angle Blocks (Present)"),
        ("Gen03FreezerDryBox", "Freezer and Dry Box Locked (Padlock / Seal #)"),
        ("Gen04MoneyBag", "Driver Money Bag and Lock (Available)"),
        ("Gen05MoneyBox", "Money Box Available in the Truck"),
    ]),
]

pretrip = ("Pre-Trip Checks", "Fleet Pre-Trip Checks.xlsx", [
    ("CheckDate", "Check date", DATE, None, SAMPLE_DATE),
    ("TruckNo", "Truck number", TEXT, None, "T07"),
    ("DriverName", "Driver", TEXT, None, "Sample Driver"),
    ("Site", "Site", TEXT, None, "Suva"),
    *[c for key, label, items in SECTIONS for c in (
        *[(k, item, CHOICE, YN, "Yes") for k, item in items],
        (f"{key}Comments", f"{label} – comments", NOTE, None, "Sample comment"),
    )],
    ("Odometer", "Odometer reading (km)", NUM, None, 123456),
    ("Remarks", "Remarks", NOTE, None, "Sample remark"),
    # Site Engineer / Fleet Controller section as the user set it up in Forms
    # (23 Oct 2026); the driver declaration questions were removed there.
    ("ApprovalForDelivery", "Approval for Delivery", CHOICE, ["Approved", "Not Approved"], "Approved"),
    ("SendForRepairs", "Send for Repairs", CHOICE, ["Send", "Don't Send"], "Don't Send"),
    ("ManagerName", "Manager / Warehouse Controller", TEXT, None, "Sample Controller"),
    ("DateOfDeclaration", "Date of Declaration", DATE, None, SAMPLE_DATE),
    ("ResponseID", "Forms response ID (filled by the flow)", TEXT, None, "1"),
])

runsheet = ("Run Sheets", "Vehicle Run Sheets - SharePoint list.xlsx", [
    ("TripDate", "Date", DATE, None, SAMPLE_DATE),
    ("TruckNo", "Truck #", TEXT, None, "T07"),
    ("DriverName", "Driver", TEXT, None, "Sample Driver"),
    ("Partner", "Partner", TEXT, None, "Sample Partner"),
    ("Area", "Area", TEXT, None, "Nadi"),
    ("InvoiceCount", "# of invoices", NUM, None, 12),
    ("StartMileage", "START mileage", NUM, None, 123456),
    ("ExpectedDeparture", "Expected departure time (CD), hh:mm", TEXT, None, "07:30"),
    ("ExpectedArrival", "Expected time of arrival (CD), hh:mm", TEXT, None, "16:00"),
    ("TimeReturned", "Time truck returned, hh:mm", TEXT, None, "15:45"),
    ("EndMileage", "END mileage", NUM, None, 123789),
    ("BalanceInvoice", "Balance invoice", TEXT, None, "INV-0001"),
    ("AnalogTemp", "Analog temp (°C)", NUM, None, -18),
    ("PlugInTemp", "Temp on plug in (°C)", NUM, None, -18),
    ("BalanceDeliveryQty", "Qty on balance delivery", NUM, None, 0),
    ("InvoiceBalanced", "Invoice balanced with cashier", CHOICE, YN, "Yes"),
    ("TeamLeader", "Verified by: Team Leader", TEXT, None, "Sample Leader"),
    ("Status", "Status", CHOICE, ["In progress", "Submitted"], "Submitted"),
])

stops = ("Run Sheet Stops", "Vehicle Run Sheet Stops - SharePoint list.xlsx", [
    ("RunSheetID", "Run sheet (ID of the Run Sheets row)", NUM, None, 1),
    ("StopOrder", "Stop order (1, 2, 3…)", NUM, None, 1),
    ("Destination", "Destination", TEXT, None, "Sample Customer"),
    ("TimeOut", "Time out, hh:mm", TEXT, None, "08:00"),
    ("ArriveTime", "Arrive time, hh:mm", TEXT, None, "08:40"),
    ("Cartons", "# of cartons", NUM, None, 25),
    ("TruckTemp", "Truck temp (°C)", NUM, None, -18),
    ("StartOpTime", "Start op time, hh:mm", TEXT, None, "08:45"),
    ("CompleteOpTime", "Complete op time, hh:mm", TEXT, None, "09:10"),
    ("DurationMinutes", "Duration (minutes)", NUM, None, 25),
    ("HSEQComments", "HSEQ observations, issues, comments", NOTE, None, "Sample comment"),
])

DECLS = [
    ("D01Licence", "Holds the appropriate and valid driver's license"),
    ("D02LicenceValid", "Responsible for maintaining license validity and conditions"),
    ("D03PreStartDone", "Completed the Vehicle Pre-Start Checklist and reported defects"),
    ("D04Rested", "Had adequate rest (at least nine hours away from all work)"),
    ("D05NoOtherDriving", "No other commercial driving during the rest period"),
    ("D06NotImpaired", "Not under any impairing condition (medical, alcohol, drug)"),
    ("D07ReportIncidents", "Will report any incident or traffic infringement notice"),
    ("D08DrugTest", "Agrees to alcohol and drug testing during the shift"),
    ("D09NoNonGFPassengers", "Will not carry non-Goodman Fielder employees"),
    ("D10SeatBeltLimit", "Passengers no more than the number of seat belts"),
    ("D11ComplyLaw", "Will comply with Fiji legislation and GF procedures"),
    ("D12RespondToRequests", "Will respond fully and accurately to requests for information"),
    ("D13DeclareNegatives", "Will declare any negative answer to the Supervisor"),
    ("D14FalseDeclaration", "Subject to disciplinary process for a false declaration"),
]

declaration = ("Driver Declarations", "Driver Declarations.xlsx", [
    ("DeclDate", "Date", DATE, None, SAMPLE_DATE),
    ("DriverName", "Driver full name", TEXT, None, "Sample Driver"),
    ("EmployeeNo", "Employee number", TEXT, None, "W0000"),
    *[(key, label, CHOICE, YN, "Yes") for key, label in DECLS],
    ("Comments", "Comments", NOTE, None, "Sample comment"),
    ("DriverConfirmed", "Driver confirmed declarations are true", CHOICE, YN, "Yes"),
    ("SupervisorName", "Supervisor name (office use)", TEXT, None, "Sample Supervisor"),
    ("SupervisorDate", "Supervisor sign-off date (office use)", DATE, None, SAMPLE_DATE),
])


# ---------------------------------------------------------------- xlsx writer
def col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

def cell(ref, v, header=False):
    if isinstance(v, datetime.date):
        serial = (v - datetime.date(1899, 12, 30)).days
        return f'<c r="{ref}" s="1"><v>{serial}</v></c>'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"><v>{v}</v></c>'
    style = ' s="2"' if header else ""
    return f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'

def sheet(rows, widths, table=False):
    cols = "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths))
    data = "".join(
        f'<row r="{r+1}">' + "".join(cell(f"{col(c)}{r+1}", v, header=(r == 0)) for c, v in enumerate(row)) + "</row>"
        for r, row in enumerate(rows))
    parts = '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>' if table else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<cols>{cols}</cols><sheetData>{data}</sheetData>{parts}</worksheet>')

# Lists whose headers get spaces between words ("CheckDate" -> "Check Date"),
# at the user's request (23 Oct 2026). SharePoint stores a space in the
# internal name as _x0020_ (e.g. Check_x0020_Date).
SPACED = {"Pre-Trip Checks", "Driver Declarations"}

def spaced(h):
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[0-9])(?=[A-Z])", " ", h)

def build(spec):
    name, file, columns = spec
    if name in SPACED:
        columns = [(spaced(c[0]), *c[1:]) for c in columns]
    headers = [c[0] for c in columns]
    sample = [c[4] for c in columns]
    ref = f"A1:{col(len(headers) - 1)}2"
    table_name = name.replace(" ", "").replace("-", "")
    table = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             f'<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="{table_name}" '
             f'displayName="{table_name}" ref="{ref}" totalsRowShown="0"><autoFilter ref="{ref}"/>'
             f'<tableColumns count="{len(headers)}">'
             + "".join(f'<tableColumn id="{i+1}" name="{escape(h)}"/>' for i, h in enumerate(headers)) +
             '</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" '
             'showRowStripes="1" showColumnStripes="0"/></table>')
    guide_rows = [["Column (internal name)", "Label to show", "SharePoint type", "Choices"]] + [
        [c[0], c[1], c[2] + (" (allow multiple: no)" if c[2] == CHOICE else ""), ", ".join(c[3] or [])] for c in columns]
    list_sheet = sheet([headers, sample], [max(14, len(h) + 4) for h in headers], table=True)
    guide_sheet = sheet(guide_rows, [26, 58, 30, 50])
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
              '</styleSheet>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="List" sheetId="1" r:id="rId1"/><sheet name="Column guide" sheetId="2" r:id="rId2"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
               '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>')
    sheet_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>'
                  '</Relationships>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '</Types>')
    path = f"{OUT}/{file}"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/worksheets/sheet1.xml", list_sheet)
        z.writestr("xl/worksheets/_rels/sheet1.xml.rels", sheet_rels)
        z.writestr("xl/worksheets/sheet2.xml", guide_sheet)
        z.writestr("xl/tables/table1.xml", table)
    print(f"{path}: {len(headers)} columns")

ONLY = sys.argv[2:]  # optional list names to build, e.g. "Pre-Trip Checks"
for spec in (pretrip, runsheet, stops, declaration):
    if not ONLY or spec[0] in ONLY:
        build(spec)
