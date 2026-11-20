"""Build .docx files laid out for Microsoft Forms 'Quick import'.

Layout rules Quick Import picks up best:
  - Title paragraph = form title, Heading 1 = section
  - Numbered question lines ("1. ...")
  - Choice options on their own lines beneath, lettered ("A. ...")
  - Questions with no options import as Text; "(date)" hint -> Date
  - Text straight after a Heading 1 becomes the section description, so a
    section with a description gets one explicit paragraph before its
    questions (otherwise short question lines get swallowed as description)

Usage: python build_forms.py <out_dir> [fleet|run|decl]   (default: all)
"""
import sys, zipfile
from xml.sax.saxutils import escape

OUT = sys.argv[1]
ONLY = sys.argv[2] if len(sys.argv) > 2 else None

OK3 = ["OK", "Not OK – defect found", "N/A"]
YN = ["Yes", "No"]

# ---------------------------------------------------------------- content
CHECKS = [
    ("Engine and Transmission", [
        "Oil Levels Engine Hydraulics (Top Level)",
        "Coolant Levels (Top Mark)",
        "Fan Belts (Alternator, Cooling Fan, A/C etc.)",
        "Oil / Water Leaks",
        "PTO (Pump, Seals, Cable, Shaft, Augers, Universal Joint)",
    ]),
    ("Electrical System", [
        "Battery Water Level (Top Mark)",
        "Battery Terminals (No Loose Terminals / Acid Build Up)",
        "Battery Master Isolator Switch",
        "Head / Fog Light (Left and Right) Functional",
        "Indicators (Left/Right & Front/Rear Truck) (Functional)",
        "Brake Lights (Left & Right, Truck) (Functional)",
        "Reverse Alarm / Lights (Left & Right Truck) (Functional)",
        "Cabin Interior Spot Light (Functional)",
        "Rear Spot Light (Functional)",
        "Horn (Functional)",
        "Truck / Bulk Bin Electrical Cables (Damage Free)",
        "Cabin Dashboard Gauges / Meters (Functional)",
    ]),
    ("Body and Chassis", [
        "Cabin Doors / Windows / Locks (Functional)",
        "Front / Rear Windscreens (Free of Cracks)",
        "Rear Vision Mirrors / Immediate Vicinity Check Mirrors",
        "Driver / Passenger Seat Belts (Functional)",
        "Springs / U-Bolts / Bin Mounting Nuts and Bolts",
        "Front and Rear Bumpers – Impact Absorption",
    ]),
    ("Brakes and Tyres", [
        "Service / Park Brake Condition",
        "Air Hoses Condition (Any Signs of Leaks)",
        "Tyre Condition (Any Retreads on Steer Wheels)",
        "Wheel Studs (All Present)",
        "Spare Tyre (In Good Condition)",
        "Jack / Wheel Brace / Accessories (All Present and Functional)",
    ]),
    ("Safety Devices", [
        "Cones & Reflector",
        "Drivers PPE (All Present)",
        "Fire Extinguishers (Present / Functional)",
        "First Aid Box (Present and Stocked)",
        "Hand Torch (Operational)",
        "Rain Coat and Helmet (Present / Good Condition)",
    ]),
    ("General", [
        "Greasing Has Been Carried Out to Moving / Rotating Parts",
        "Braking Angle Blocks (Present)",
        "Freezer and Dry Box Locked (Padlock / Seal #)",
        "Driver Money Bag and Lock (Available)",
        "Money Box Available in the Truck",
    ]),
]

fleet = {
    "file": "Fleet Pre-Trip Checklist - MS Forms import.docx",
    "title": "Fleet Pre-Trip Checklist",
    "intro": "All drivers must complete this checklist before starting any vehicle. "
             "All faults or defects must be reported to the Site Manager or Fleet Controller immediately.",
    "answer_lines": False,
    # 23 Oct 2026: each item is its own Yes/No question (like the driver
    # declaration) instead of one "select all that apply" per section, and the
    # office-use section moved to the SharePoint list.
    "sections": [
        *[(name, "Answer Yes if the item has been checked and is in order. Note any defect in the comments.",
           [(item, YN) for item in items] + [(f"{name} – comments", None)])
          for name, items in CHECKS],
        ("Odometer and Remarks", "Record the odometer before leaving.", [
            ("Truck odometer reading before delivery (km)", None),
            ("Remarks", None),
        ]),
        # Matches the live form as the user edited it (23 Oct 2026): driver
        # declaration removed, Site Engineer section added.
        ("Declaration by the Site Engineer / Fleet Controller",
         "This is to verify that the driver has carried out the above checks and I have satisfied myself by cross-checking.", [
            ("Approval for Delivery", ["Approved", "Not Approved"]),
            ("Send for Repairs", ["Send", "Don't Send"]),
            ("Manager / Warehouse Controller", None),
            ("Date of Declaration", None),
        ]),
    ],
}

T = " (hh:mm, 24-hour)"
def stop(last):
    qs = [
        ("Time Out" + T, None),
        ("Destination", None),
        ("# of Ctns", None),
        ("Arrive Time" + T, None),
        ("Truck Temp (°C)", None),
        ("Start Op Time" + T, None),
        ("Complete Op Time" + T, None),
        ("Duration (minutes)", None),
        ("HSEQ Observations, Issues, Comments", None),
    ]
    if not last:
        qs.append(("Do you have another delivery stop?", YN))
    return ("Delivery Stop", "Record this delivery stop as shown on the run sheet.", qs)

STOPS = 18  # rows on SOP DC/16.0 V007 Appendix II
run = {
    "file": "Vehicle Run Sheet - MS Forms import.docx",
    "title": "Driver Responsibilities and Customer Service",
    "intro": "SOP DC/16.0 V007 Appendix II – Vehicle Run Sheet Checklist. "
             "Complete one response per truck run. Record each delivery stop in order.",
    "answer_lines": False,
    "sections": [
        ("Trip Details", "Fill in before the truck leaves the CD.", [
            ("Date", None),
            ("Truck #", None),
            ("Driver", None),
            ("Partner", None),
            ("Area", None),
            ("# Of Invoices", None),
            ("START Mileage", None),
            ("Expected Departure Time (CD)" + T, None),
            ("Expected Time of Arrival (CD)" + T, None),
        ]),
        *[stop(i == STOPS) for i in range(1, STOPS + 1)],
        ("Return to CD", "Fill in when the truck is back at the CD.", [
            ("Time truck returned" + T, None),
            ("END Mileage", None),
            ("Balance invoice", None),
            ("Analog Temp. (°C)", None),
            ("Temp. on Plug in (°C)", None),
            ("Qty on Balance Delivery", None),
            ("Invoice Balanced with Cashier", YN),
        ]),
        ("Sign-off", "Driver and verifying Team Leader for this run sheet.", [
            ("Truck Driver's Name", None),
            ("Verified By: Team Leader Name", None),
        ]),
    ],
}

DECLARATIONS = [
    "Must hold the appropriate and valid driver's license required to drive the vehicle assigned to me",
    "Am responsible for maintaining the validity and conditions of my driver's license",
    "Have completed the necessary Vehicle Pre-Start Checklist and notified my Supervisor of any defects "
    "which may affect driver safety, vehicle safety and journey safety",
    "Have had adequate rest prior to driving my assigned vehicle. Rest is the hours totalling no less than "
    "nine hours, defined as the number of hours taken sequentially, completely away from all work",
    "Shall not engage in activities such as driving other commercial vehicles, including or not limited to, "
    "driving taxis, hired vehicles, pirate taxis during the rest period above",
    "Am not under any condition (medical, alcohol, drug, etc) that will impair my driving ability "
    "and create a risk to other road users",
    "Shall report any incident (including any traffic infringement notices) to my immediate Supervisor "
    "as soon as possible",
    "Shall agree to undergo an alcohol and drug test at any time during my shift irrespective whether "
    "an incident has occurred or not",
    "Shall not carry any non-Goodman Fielder employees in my assigned vehicle",
    "Shall carry only the number of passengers equal to the number of seat belts in a vehicle",
    "Shall comply with all Fiji legislation and Goodman Fielder Procedural requirements with respect to "
    "road and vehicle use",
    "Shall respond fully and accurately to any requests for information, whether from a Goodman Fielder "
    "leader / representative, a Health Professional, or relevant authorities including (but not limited to) "
    "LTA Officers, Police, etc.",
    "Will immediately declare to my Supervisor if any of the above is in the negative and provide the "
    "necessary detail in the 'Comments' section below",
    "Shall be subject to the company disciplinary processes with consequences leading up to and including "
    "summary dismissal, for making a false declaration",
]

declaration = {
    "file": "Fitness for Driving Driver Declaration - MS Forms import.docx",
    "title": "Fitness for Driving – Driver Declaration Form",
    "intro": "This document is to provide clarity and direction to all Goodman Fielder truck drivers on their "
             "responsibilities with respect to driver safety, vehicle safety and journey safety. "
             "Please answer each declaration prior to signing off.",
    "answer_lines": False,
    # 23 Oct 2026: sign-off name/date dropped (repeat Driver Details; Forms
    # records who and when) and Supervisor section moved to the SharePoint list.
    "sections": [
        ("Driver Details", "Fill in your details before starting your shift.", [
            ("Driver full name", None),
            ("Employee number", None),
            ("Date", None),
        ]),
        ("Declarations", "I hereby declare that I:", [(d, YN) for d in DECLARATIONS]),
        ("Comments", "If you answered No to any declaration, give the details here.", [
            ("Comments", None),
        ]),
        ("Driver Sign-off", "Confirm and sign off your declaration.", [
            ("I confirm that the declarations above are true and correct.", ["I agree"]),
        ]),
    ],
}

# ---------------------------------------------------------------- docx writer
def para(text, style=None, bold=False, indent=0):
    ppr = ""
    if style or indent:
        ppr = "<w:pPr>"
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if indent:
            ppr += f'<w:ind w:left="{indent}"/>'
        ppr += "</w:pPr>"
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def build(form):
    body = [para(form["title"], "Title"), para(form["intro"])]
    n = 0
    for name, *desc, qs in form["sections"]:
        body.append(para(name, "Heading1"))
        for d in desc:
            body.append(para(d))
            body.append(para(""))
        for q, opts in qs:
            n += 1
            body.append(para(f"{n}. {q}", bold=True))
            for i, o in enumerate(opts or []):
                body.append(para(f"{chr(65 + i)}. {o}", indent=720))
            if not opts and form.get("answer_lines", True):  # blank answer line marks it as a text question
                body.append(para("_" * 40, indent=720))
            body.append(para(""))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + "".join(body) +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
           '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
              '<w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="60"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
              '<w:pPr><w:spacing w:after="200"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
              '<w:pPr><w:keepNext/><w:spacing w:before="320" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>'
              '<w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="30"/></w:rPr></w:style>'
              '</w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    docrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>')
    path = f"{OUT}/{form['file']}"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", docrels)
        z.writestr("word/styles.xml", styles)
    print(f"{path}: {n} questions")

if ONLY in (None, "fleet"):
    build(fleet)
if ONLY in (None, "run"):
    build(run)
if ONLY in (None, "decl"):
    build(declaration)
