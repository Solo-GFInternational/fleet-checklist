"""Builds screens/scrPreTrip.txt (the Fleet Checklist screen) from scripts/checklist_items.json.

Usage:  py -3 -I scripts/build_pretrip_screen.py screens

checklist_items.json is the single source for the order, sections, instructions, photo rules,
truck-type rules and who answers each item. Edit the JSON, run this script, paste the screen.

What it builds:
  - Screen chrome (header, stripe, form properties, footer, reviewer sign-off cards) and the
    header/odometer/remarks cards are copied verbatim from the templates at the bottom of this file
    (taken from the hand-built screen, Nov 2026).
  - One section heading card per section.
  - Yes/No items: two checkboxes, Yes (the card's DataCardValueN) and No (chk<Card>No).
    Exclusive via Reset: ticking one resets the other to its Default (blank on a new checklist).
    A multi-line comment box (txt<Card>Cmt) inside the item's card shows when the "problem"
    answer (commentOn) is ticked and is then required. Comments are not columns: frmPreTrip.OnSuccess
    adds one row per problem answer to the GF Fleet Checklist Defects list (weekly reviewer items:
    btnSaveSignoff). When reviewing, the box shows that row's comment (colCheckDefects, OnVisible).
  - Photo buttons per item: one / perTyre (Tyre 1..N, N from the Trucks list, 6 if not found)
    / fourSides (Front, Rear, Left, Right) / multi (accident photos).
  - Weekly reviewer-only items (cabin tilting, greasing): only when reviewing; replaced by
    "... conducted on <date> by <name>" when this truck already has a Yes this week (Mon-Sun).
  - Submit button that names the first missing answer, comment, field or photo.
  - One section per page: ctxPage / ctxSec (colPages, built in OnVisible; header + In the cabin
    are page 1, sign-off cards sit on the last page). Footer: progress label and bar,
    Back / Next, "N still to do" for the current page, Submit and "Go to it" on the last page.
    Starters pass {ctxPage: 1, ctxSec: "licence"} in Navigate.
  - Draft on the phone: every answer, comment, date and header field is written to colDraft
    ({f, a, c}; rows "_truck" and "_started" are made by scrHome) and saved with
    SaveData "fcCheckDraft"; a new checklist's Defaults read it back (reviewing ignores it).
  - Items with "truckDate": the date comes from the GF Fleet Trucks column of that name, shown
    read-only with Expired / Due within 30 days / OK; date picker and photo only when it is blank.

Items with "hidden": true are left off the screen (their SharePoint columns stay).
Stdlib only.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_JSON = os.path.join(HERE, 'checklist_items.json')

# Palette
TEAL = 'RGBA(8, 144, 144, 1)'
DARK_TEAL = 'RGBA(0, 112, 112, 1)'
TINT = 'RGBA(226, 243, 242, 1)'
YELLOW = 'RGBA(248, 208, 0, 1)'
INK = 'RGBA(31, 41, 51, 1)'
MUTED = 'RGBA(96, 108, 118, 1)'
LINE = 'RGBA(208, 216, 218, 1)'
RED = 'RGBA(196, 49, 75, 1)'
CLEAR = 'RGBA(0, 0, 0, 0)'
WHITE = 'RGBA(255, 255, 255, 1)'
YELLOW_TINT = 'RGBA(254, 246, 204, 1)'

FIRST_PAGE = 'cabin'   # header (truck, driver, site) + In the cabin share page 1
LAST_PAGE = 'remarks'    # sign-off cards sit on the last page

MAX_TYRES = 12          # tyre photo buttons generated; NoOfTyres above this is capped
FIRST_NEW_NUMBER = 103  # DataCardValueN numbers for new cards start here (1-102 are used by scrPreTrip/scrTest)
# scrTest (test screen) already uses these numbers, so cards that had them get new numbers
# (control names must be unique across the app).
TAKEN_ELSEWHERE = set(range(5, 18)) | {28, 63} | set(range(71, 103))

# Existing cards keep their names and DataCardValueN numbers (taken from the Nov 2026 screen).
EXISTING_CARDS = {
    'field_1': ('crdTruckNo', 18), 'field_2': ('crdDriverName', 19), 'field_3': ('crdSite', 20),
    'field_4': ('crdOilLevels', 21), 'field_5': ('crdCoolantLevels', 22), 'field_6': ('crdFanBelts', 42),
    'field_7': ('crdOilWaterLeaks', 56), 'field_8': ('crdPTO', 57), 'field_9': ('crdEngineComments', 23),
    'field_10': ('crdBatteryWater', 24), 'field_11': ('crdBatteryTerminals', 30),
    'field_12': ('crdBatteryIsolator', 29), 'field_13': ('crdHeadFogLights', 51),
    'field_14': ('crdIndicators', 53), 'field_15': ('crdBrakeLights', 25), 'field_16': ('crdReverseAlarm', 61),
    'field_17': ('crdCabinSpotLight', 36), 'field_18': ('crdRearSpotLight', 59), 'field_19': ('crdHorn', 52),
    'field_20': ('crdElectricalCables', 70), 'field_21': ('crdDashGauges', 34),
    'field_22': ('crdElectricalComments', 41), 'field_23': ('crdCabinDoors', 35),
    'field_24': ('crdWindscreens', 46), 'field_25': ('crdMirrors', 60), 'field_26': ('crdSeatBelts', 38),
    'field_27': ('crdSpringsUBolts', 66), 'field_28': ('crdBumpers', 47), 'field_29': ('crdBodyComments', 31),
    'field_30': ('crdParkBrake', 64), 'field_31': ('crdAirHoses', 27), 'field_32': ('crdTyreCondition', 68),
    'field_33': ('crdWheelStuds', 67), 'field_34': ('crdSpareTyre', 65), 'field_35': ('crdJackWheelBrace', 54),
    'field_36': ('crdBrakesComments', 32), 'field_37': ('crdConesReflector', 37), 'field_38': ('crdDriverPPE', 40),
    'field_39': ('crdFireExtinguishers', 43), 'field_40': ('crdFirstAidBox', 44), 'field_41': ('crdHandTorch', 50),
    'field_42': ('crdRainCoatHelmet', 58), 'field_43': ('crdSafetyComments', 62), 'field_44': ('crdGreasing', 49),
    'field_45': ('crdAngleBlocks', 33), 'field_46': ('crdFreezerLocked', 45), 'field_47': ('crdMoneyBag', 39),
    'field_48': ('crdMoneyBox', 55), 'field_49': ('crdGeneralComments', 48),
    'AccCOFExpiry': ('crdCOFExpiry', 71), 'AccBlowerServiceDue': ('crdBlowerServiceDue', 72),
    'AccTruckServiceDue': ('crdTruckServiceDue', 73), 'AccSpareTyre': ('crdAccSpareTyre', 74),
    'AccTyreCondition': ('crdAccTyreCondition', 75), 'AccCabinClean': ('crdCabinClean', 76),
    'AccFireExtinguisher': ('crdAccFireExtinguisher', 77), 'AccFirstAidKit': ('crdAccFirstAidKit', 78),
    'AccTrafficCones': ('crdTrafficCones', 79), 'AccFuelCard': ('crdFuelCard', 80), 'AccPlugWire': ('crdPlugWire', 81),
    'AccMats': ('crdMats', 82), 'AccEngJack': ('crdEngJack', 83), 'AccEngWheelBrace': ('crdEngWheelBrace', 84),
    'AccEngPipe': ('crdEngPipe', 85), 'AccEngTyreWinder': ('crdEngTyreWinder', 86),
    'AccEngTrolley': ('crdEngTrolley', 87), 'AccTruckFloor': ('crdTruckFloor', 88),
    'AccComments': ('crdAccComments', 89), 'field_51': ('crdRemarks', 26), 'field_50': ('crdOdometer', 69),
    'NextServiceDue': ('crdNextServiceDue', 90),
}

# Weekly reviewer-only items: variable holding this week's earlier "Yes" record, and the done-note wording.
WEEKLY = {
    'CabTilt': ('varWeekTilt', 'Cabin Tilting inspection'),
    'field_44': ('varWeekGrease', 'Underneath greasing inspection'),
}

def draft_text_mod(field, numeric=False):
    """(old, new) for add_template: a verbatim text input's Default reads the draft; OnChange saves it."""
    review = 'Text(Parent.Default)' if numeric else 'Parent.Default'
    pad = ' ' * 24
    body = [f'{pad}Default: |-', f'{pad}  =If(varReviewing, {review}, {draft_value(field)}.a)',
            f'{pad}OnChange: |-']
    body += [f'{pad}  {ln}' for ln in ('=' + draft_save(field, 'Self.Text')).split('\n')]
    return (f'{pad}Default: =Parent.Default\n', '\n'.join(body) + '\n')


TRUCK_TYPE_RULE = '(IsBlank(varTruckInfo) || varTruckInfo.TruckType.Value = "{t}")'


# ---------------------------------------------------------------- YAML helpers

def fx_str(s):
    """Power Fx text literal."""
    return '"' + s.replace('"', '""') + '"'


def prop_lines(name, formula, indent):
    """One property. Block form when the formula has a line break or ': ' (paste rule PA1001)."""
    pad = ' ' * indent
    if '\n' in formula or ': ' in formula:
        body = ('=' + formula).split('\n')
        return [f'{pad}{name}: |-'] + [f'{pad}  {ln}' if ln else '' for ln in body]
    return [f'{pad}{name}: ={formula}']


def control(name, ctype, props, indent, variant=None, metadata=None, children=None):
    """props: list of (name, formula). children: list of already-built line lists."""
    pad = ' ' * indent
    out = [f'{pad}- {name}:', f'{pad}    Control: {ctype}']
    if variant:
        out.append(f'{pad}    Variant: {variant}')
    if metadata:
        out.append(f'{pad}    MetadataKey: {metadata}')
    out.append(f'{pad}    Properties:')
    for k, v in props:
        out += prop_lines(k, v, indent + 6)
    if children:
        out.append(f'{pad}    Children:')
        for c in children:
            out += c
    return out


CARD = 12   # indent of a card inside frmPreTrip.Children
KID = 18    # indent of a control inside a card


def card_frame(row, extra_props, visible=None):
    props = [('BorderColor', LINE)] + extra_props
    if visible:
        props.append(('Visible', visible))
    props += [('Width', 'Parent.Width'), ('WidthFit', 'true'), ('X', '0'), ('Y', str(row))]
    return props


def key_label(n):
    return control(f'DataCardKey{n}', 'Label@2.5.1', [
        ('AutoHeight', 'true'), ('BorderColor', CLEAR), ('BorderStyle', 'BorderStyle.None'),
        ('BorderThickness', '2'), ('Color', INK), ('Size', '14'), ('DisabledBorderColor', CLEAR),
        ('DisabledColor', 'RGBA(161, 159, 157, 1)'), ('FocusedBorderThickness', '4'),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '34'),
        ('PaddingLeft', '0'), ('Text', 'Parent.DisplayName'), ('Width', 'Parent.Width - 60'),
        ('Wrap', 'true'), ('X', '30'), ('Y', '18'),
    ], KID, metadata='FieldName')


def title_label(name, text):
    """Like a DataCardKey label, for blank (photo-only) cards."""
    return control(name, 'Label@2.5.1', [
        ('AutoHeight', 'true'), ('BorderStyle', 'BorderStyle.None'), ('Color', INK), ('Size', '14'),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '34'),
        ('PaddingLeft', '0'), ('Text', fx_str(text)), ('Width', 'Parent.Width - 60'),
        ('Wrap', 'true'), ('X', '30'), ('Y', '18'),
    ], KID)


def hint_label(name, text, y):
    return control(name, 'Label@2.5.1', [
        ('AutoHeight', 'true'), ('BorderStyle', 'BorderStyle.None'), ('Color', MUTED),
        ('Font', "Font.'Segoe UI'"), ('Height', '24'), ('PaddingLeft', '0'), ('PaddingTop', '0'),
        ('Size', '12'), ('Text', fx_str(text)), ('Width', 'Parent.Width - 60'), ('Wrap', 'true'),
        ('X', '30'), ('Y', y),
    ], KID)


def error_label(n, y):
    return control(f'ErrorMessage{n}', 'Label@2.5.1', [
        ('AutoHeight', 'true'), ('BorderColor', CLEAR), ('BorderStyle', 'BorderStyle.None'),
        ('BorderThickness', '2'), ('Color', 'RGBA(168, 0, 0, 1)'), ('DisabledBorderColor', CLEAR),
        ('DisabledColor', 'RGBA(168, 0, 0, 1)'), ('FocusedBorderThickness', '4'),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '10'),
        ('Live', 'Live.Assertive'), ('PaddingBottom', '12'), ('PaddingLeft', '0'), ('PaddingRight', '0'),
        ('PaddingTop', '0'), ('Text', 'Parent.Error'), ('Visible', 'Parent.DisplayMode=DisplayMode.Edit'),
        ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', y),
    ], KID, metadata='ErrorMessage')


def star_label(n):
    return control(f'StarVisible{n}', 'Label@2.5.1', [
        ('Align', 'Align.Center'), ('BorderColor', CLEAR), ('BorderStyle', 'BorderStyle.None'),
        ('BorderThickness', '2'), ('Color', RED), ('DisabledBorderColor', CLEAR),
        ('DisabledColor', 'RGBA(161, 159, 157, 1)'), ('FocusedBorderThickness', '4'),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'),
        ('Height', f'DataCardKey{n}.Height'), ('PaddingLeft', '0'), ('Text', '"*"'),
        ('Visible', 'And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)'), ('Width', '30'),
        ('Wrap', 'false'), ('Y', f'DataCardKey{n}.Y'),
    ], KID, metadata='FieldRequired')


def draft_save(field, answer, comment='""'):
    """Write one row of the phone draft (colDraft) and save it. Skipped when reviewing."""
    return (f'If(!varReviewing,\n'
            f'    RemoveIf(colDraft, f = {fx_str(field)});\n'
            f'    Collect(colDraft, {{f: {fx_str(field)}, a: {answer}, c: {comment}}});\n'
            f'    IfError(SaveData(colDraft, "fcCheckDraft"); true, false))')


def draft_value(field):
    return f'LookUp(colDraft, f = {fx_str(field)})'


def checkbox(name, caption, default, on_check, x, y, visible=None, on_uncheck=None):
    props = [
        ('BorderColor', CLEAR), ('CheckboxBackgroundFill', WHITE), ('CheckboxBorderColor', TEAL),
        ('CheckboxSize', '30'), ('CheckmarkFill', TEAL), ('Color', INK), ('Default', default),
        ('DisabledColor', INK), ('DisplayMode', 'Parent.DisplayMode'), ('Fill', CLEAR),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '48'),
        ('HoverColor', INK), ('HoverFill', TINT), ('OnCheck', on_check),
    ]
    if on_uncheck:
        props.append(('OnUncheck', on_uncheck))
    props += [
        ('PressedColor', INK), ('PressedFill', TINT), ('Size', '15'), ('Text', fx_str(caption)),
    ]
    if visible:
        props.append(('Visible', visible))
    props += [('Width', '110'), ('X', x), ('Y', y)]
    return control(name, 'Classic/CheckBox@2.1.0', props, KID)


def photo_missing(ptype, item):
    return f'IsEmpty(Filter(colPhotos, Type = {fx_str(ptype)} && Item = {fx_str(item)}))'


def photo_taken(ptype, item):
    return '!' + photo_missing(ptype, item)


def photo_onselect(ptype, item_expr):
    return f'Set(varPhotoType, {fx_str(ptype)});\nSet(varPhotoItem, {item_expr});\nNavigate(scrPhotos)'


def secondary_button(name, text, onselect, width, x, y, visible, fill='RGBA(255, 255, 255, 1)', height='44'):
    return control(name, 'Classic/Button@2.2.0', [
        ('BorderColor', TEAL), ('BorderStyle', 'BorderStyle.Solid'), ('BorderThickness', '2'),
        ('Color', DARK_TEAL), ('Fill', fill), ('Font', "Font.'Segoe UI'"),
        ('FontWeight', 'FontWeight.Semibold'), ('Height', height), ('HoverBorderColor', TEAL),
        ('HoverColor', DARK_TEAL), ('HoverFill', TINT), ('OnSelect', onselect),
        ('PressedBorderColor', DARK_TEAL), ('PressedColor', DARK_TEAL), ('PressedFill', TINT),
        ('RadiusBottomLeft', '10'), ('RadiusBottomRight', '10'), ('RadiusTopLeft', '10'),
        ('RadiusTopRight', '10'), ('Size', '14'), ('Text', text), ('Visible', visible),
        ('Width', width), ('X', x), ('Y', y),
    ], KID)


def status_label(name, ok_cond, ok_text, todo_text, width, x, y, visible):
    return control(name, 'Label@2.5.1', [
        ('BorderStyle', 'BorderStyle.None'), ('Color', f'If({ok_cond}, {DARK_TEAL}, {RED})'),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '56'),
        ('PaddingBottom', '12'), ('PaddingLeft', '0'), ('Size', '13'),
        ('Text', f'If({ok_cond}, {ok_text}, {todo_text})'), ('Visible', visible), ('Width', width),
        ('X', x), ('Y', y), ('Wrap', 'true'),
    ], KID)


# ---------------------------------------------------------------- photo rules

def photo_type(it):
    if it['field'] == 'field_50':
        return 'Odometer'
    return {'perTyre': 'Tyre', 'fourSides': 'Profile', 'multi': 'Accident'}.get(it['photo'], 'Accessory')


def photo_controls(it, suffix, y, answer_box, show='!varReviewing'):
    """Photo buttons + status for an item. Returns (controls, list of (condition, message) for Submit).
    show: Visible of the 'one' photo button and status."""
    ptype = photo_type(it)
    out, missing = [], []
    rule = it['photo']
    if rule == 'one':
        item = it['photoSlots'][0]
        taken = photo_taken(ptype, item)
        out.append(secondary_button(
            f'btn{suffix}Photo', f'If({taken}, "Retake photo", "Take photo")',
            photo_onselect(ptype, fx_str(item)), '150', '30', y, show))
        out.append(status_label(f'lbl{suffix}Photo', taken, '"✓ Photo taken"', '"Photo required"',
                                'Parent.Width - 210', '192', y, show))
        missing.append((photo_missing(ptype, item), fx_str('Photo needed: ' + item)))
    elif rule in ('perTyre', 'fourSides'):
        if rule == 'perTyre':
            slots = [(f'Tyre{i}', f'Tyre {i}', f'{i} <= varTyreCount') for i in range(1, MAX_TYRES + 1)]
            cols = 3
        else:
            slots = [(s, s, None) for s in it['photoSlots']]
            cols = 2
        w = f'(Parent.Width - {60 + 8 * (cols - 1)}) / {cols}'
        for i, (nm, item, cond) in enumerate(slots):
            taken = photo_taken(ptype, item)
            r, c = divmod(i, cols)
            x = '30' if c == 0 else f'30 + {c} * ({w} + 8)'
            yy = y if r == 0 else f'{y} + {r * 56}'
            vis = '!varReviewing' + (f' && {cond}' if cond else '')
            out.append(secondary_button(
                f'btn{suffix}{nm}', f'If({taken}, {fx_str("✓ " + item)}, {fx_str(item)})',
                photo_onselect(ptype, fx_str(item)), w, x, yy, vis,
                fill=f'If({taken}, {TINT}, RGBA(255, 255, 255, 1))', height='48'))
            miss = photo_missing(ptype, item) if not cond else f'{cond} && {photo_missing(ptype, item)}'
            missing.append((miss, fx_str('Photo needed: ' + item)))
        if rule == 'perTyre':
            rows_expr = f'RoundUp(varTyreCount / {cols}, 0) * 56'
            done = f'CountRows(Filter(colPhotos, Type = {fx_str(ptype)} && Value(Mid(Item, 6)) <= varTyreCount))'
            total = 'varTyreCount'
        else:
            rows_expr = str(-(-len(slots) // cols) * 56)
            done = f'CountRows(Filter(colPhotos, Type = {fx_str(ptype)}))'
            total = str(len(slots))
        out.append(control(f'lbl{suffix}Photo', 'Label@2.5.1', [
            ('BorderStyle', 'BorderStyle.None'), ('Color', MUTED), ('Font', "Font.'Segoe UI'"),
            ('Height', '40'), ('PaddingBottom', '12'), ('PaddingLeft', '0'), ('Size', '13'),
            ('Text', f'{done} & " of " & {total} & " photos taken"'), ('Visible', '!varReviewing'),
            ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', f'{y} + {rows_expr}'),
        ], KID))
    elif rule == 'multi':
        n_taken = f'CountRows(Filter(colPhotos, Type = {fx_str(ptype)}))'
        next_item = (f'First(Filter(ForAll(Sequence(50), {fx_str(ptype + " ")} & Value), '
                     f'!(Value in Filter(colPhotos, Type = {fx_str(ptype)}).Item))).Value')
        vis = f'!varReviewing && {answer_box}.Value'
        out.append(secondary_button(f'btn{suffix}Photo', '"Add photo"', photo_onselect(ptype, next_item),
                                    '150', '30', y, vis))
        out.append(status_label(f'lbl{suffix}Photo', f'{n_taken} > 0', f'{n_taken} & " photo(s) taken"',
                                '"Take a photo of each spot"', 'Parent.Width - 210', '192', y, vis))
        missing.append((f'{answer_box}.Value && {n_taken} = 0', fx_str('Photo needed: ' + it['proposedName'])))
    return out, missing


# ---------------------------------------------------------------- cards

class Builder:
    def __init__(self, data):
        self.data = data
        self.row = 0
        self.next_n = FIRST_NEW_NUMBER
        self.cards = []           # list of line lists
        self.missing = []         # Submit gate: (condition, message expr, page key)
        self.weekly = []          # (field, var, yes box, no box, key n, comment box or None)
        self.page_keys = []       # page (section) keys in order
        self.review_pages = set() # pages that show something when reviewing
        self.defects = []         # driver items with a comment box: (field, key n, problem box, comment box, truck rule)
        self.page_key = FIRST_PAGE  # section key of the page the cards being built sit on

    def new_n(self):
        n = self.next_n
        self.next_n += 1
        return n

    def take_row(self):
        r = self.row
        self.row += 1
        return r

    def card_names(self, it):
        if it['field'] in EXISTING_CARDS:
            card, n = EXISTING_CARDS[it['field']]
            return (card, self.new_n() if n in TAKEN_ELSEWHERE else n)
        return ('crd' + it['field'], self.new_n())

    def renumber(self, text, n):
        """Give a verbatim card a new DataCardValueN number if scrTest already uses its number."""
        if n not in TAKEN_ELSEWHERE:
            return text
        new = self.new_n()
        return re.sub(rf'\b(DataCardValue|DataCardKey|ErrorMessage|StarVisible){n}\b', rf'\g<1>{new}', text)

    # -- verbatim templates
    def add_template(self, text, *mods):
        rows = []

        def sub_y(m):
            rows.append(self.take_row())
            return f'{m.group(1)}{rows[-1]}'
        text = re.sub(r'(?m)^(                  Y: =)\d+$', sub_y, text)
        for old, new in mods:
            assert old in text, old
            text = text.replace(old, new)
        # card-level Visible gets the page rule (inserted when the card has none)
        page = f'ctxSec = {fx_str(self.page_key)}'
        if '\n                  Visible: =varReviewing\n' in text:
            text = text.replace('\n                  Visible: =varReviewing\n',
                                f'\n                  Visible: =varReviewing && {page}\n')
        else:
            assert '\n                  Visible: =' not in text
            text = text.replace('\n                  Width: =Parent.Width\n',
                                f'\n                  Visible: ={page}\n                  Width: =Parent.Width\n', 1)
        self.cards.append(text.rstrip('\n').split('\n'))

    def add_heading(self, key, title, visible=None):
        k = key[0].upper() + key[1:]
        props = [('BorderColor', LINE), ('DisplayName', fx_str(title)), ('Height', '60'),
                 ('Visible', self.page_vis(visible))]
        props += [('Width', 'Parent.Width'), ('WidthFit', 'true'), ('X', '0'), ('Y', str(self.take_row()))]
        lbl = control(f'lblSec{k}', 'Label@2.5.1', [
            ('Wrap', 'true'), ('Align', 'Align.Left'), ('Fill', TEAL), ('PaddingLeft', '16'),
            ('BorderColor', CLEAR), ('BorderStyle', 'BorderStyle.None'), ('BorderThickness', '2'),
            ('Color', WHITE), ('DisabledBorderColor', CLEAR), ('DisabledColor', 'RGBA(161, 159, 157, 1)'),
            ('FocusedBorderThickness', '4'), ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Bold'),
            ('Height', '44'), ('Size', '16'), ('Text', fx_str(title)), ('Width', 'Parent.Width'), ('Y', '10'),
        ], KID)
        self.cards.append(control(f'crdHdr{k}', 'TypedDataCard@1.0.7', props, CARD, variant='BlankCard',
                                  children=[lbl]))

    def add_truck_note(self):
        lbl = control('lblTruckNotFound', 'Label@2.5.1', [
            ('AutoHeight', 'true'), ('BorderStyle', 'BorderStyle.None'), ('Color', INK), ('Fill', YELLOW),
            ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '40'),
            ('PaddingBottom', '8'), ('PaddingLeft', '12'), ('PaddingRight', '12'), ('PaddingTop', '8'),
            ('Size', '13'), ('Text', '"Truck not in the Trucks list – all items shown."'),
            ('Width', 'Parent.Width - 48'), ('Wrap', 'true'), ('X', '24'), ('Y', '10'),
        ], KID)
        props = [('BorderColor', CLEAR), ('DisplayName', '"Truck note"'),
                 ('Height', '60 + (lblTruckNotFound.Height - 40)'), ('Visible', self.page_vis('IsBlank(varTruckInfo)')),
                 ('Width', 'Parent.Width'), ('WidthFit', 'true'), ('X', '0'), ('Y', str(self.take_row()))]
        self.cards.append(control('crdTruckNote', 'TypedDataCard@1.0.7', props, CARD, variant='BlankCard',
                                  children=[lbl]))

    def vis_rule(self, it):
        if it['truckType'] in ('Frozen', 'Ambient'):
            return TRUCK_TYPE_RULE.format(t=it['truckType'])
        return None

    def add_yesno(self, it):
        f = it['field']
        card, n = self.card_names(it)
        sfx = card[3:]
        reviewer = it['answeredBy'] == 'reviewer'
        truck_vis = self.vis_rule(it)
        yes_box, no_box = f'DataCardValue{n}', f'chk{sfx}No'
        if reviewer:
            week_var, week_text = WEEKLY.get(f, (f'varWeek{sfx}', it['proposedName']))
            dm = 'If(varReviewing, DisplayMode.Edit, DisplayMode.View)'
            card_vis = 'varReviewing'
            box_vis = f'IsBlank({week_var})'
            yes_default = no_default = 'false'
        else:
            dm = 'If(varReviewing, DisplayMode.View, DisplayMode.Edit)'
            card_vis = truck_vis
            box_vis = None
            yes_default = f'If(varReviewing, ThisItem.{f}.Value = "Yes", {draft_value(f)}.a = "Yes")'
            no_default = f'If(varReviewing, ThisItem.{f}.Value = "No", {draft_value(f)}.a = "No")'
        cmt = f'txt{sfx}Cmt' if it.get('commentOn') else None
        answer = f'If({yes_box}.Value, "Yes", {no_box}.Value, "No", "")'
        cmt_text = f'{cmt}.Text' if cmt else '""'

        def on_check(ans, other):
            if reviewer:
                return f'Reset({other})'
            # draft first: Reset puts the other box back to its Default, which reads the draft
            return draft_save(f, fx_str(ans), cmt_text) + f';\nReset({other})'
        on_uncheck = None if reviewer else draft_save(f, answer, cmt_text)

        kids = [key_label(n)]
        below = f'DataCardKey{n}.Y + DataCardKey{n}.Height'
        if it['instruction']:
            kids.append(hint_label(f'lbl{sfx}Hint', it['instruction'], f'{below} + 2'))
            below = f'lbl{sfx}Hint.Y + lbl{sfx}Hint.Height'
        box_y = f'{below} + 4'
        kids.append(checkbox(yes_box, 'Yes', yes_default, on_check('Yes', no_box), '30', box_y, box_vis,
                             on_uncheck))
        kids.append(checkbox(no_box, 'No', no_default, on_check('No', yes_box), '150', box_y, box_vis,
                             on_uncheck))
        err_y = f'{yes_box}.Y + {yes_box}.Height'
        if reviewer:
            done = f'lbl{sfx}Done'
            kids.append(control(done, 'Label@2.5.1', [
                ('AutoHeight', 'true'), ('BorderStyle', 'BorderStyle.None'), ('Color', DARK_TEAL),
                ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '48'),
                ('PaddingLeft', '0'), ('Size', '14'),
                ('Text', f'{fx_str(week_text + " conducted on ")} & Text({week_var}.field_55, "dd mmm yyyy") & " by " & {week_var}.field_54'),
                ('Visible', f'!IsBlank({week_var})'), ('Width', 'Parent.Width - 60'), ('Wrap', 'true'),
                ('X', '30'), ('Y', box_y),
            ], KID))
            err_y = f'{box_y} + If(IsBlank({week_var}), {yes_box}.Height, {done}.Height)'
        problem_box = yes_box if it.get('commentOn') == 'Yes' else no_box
        if cmt:
            kids.append(self.comment_box(it, cmt, problem_box, yes_box, reviewer, week_var if reviewer else None,
                                         None if reviewer else draft_save(f, answer, 'Self.Text')))
            err_y = f'If({cmt}.Visible, {cmt}.Y + {cmt}.Height, {err_y})'
        kids.append(error_label(n, err_y))
        kids.append(star_label(n))
        photo_missing_list = []
        if it['photo'] != 'none':
            pc, miss = photo_controls(it, sfx, f'ErrorMessage{n}.Y + ErrorMessage{n}.Height - 4', problem_box)
            kids += pc
            if it['required'] and not reviewer:
                photo_missing_list = [(self.wrap(truck_vis, c), m) for c, m in miss]

        update = f'If({yes_box}.Value, {{Value: "Yes"}}, {no_box}.Value, {{Value: "No"}}, Blank())'
        props = card_frame(self.take_row(), [
            ('DataField', fx_str(f)), ('Default', f'ThisItem.{f}'), ('DisplayMode', dm),
            ('DisplayName', f"DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'{f}')"),
            ('Required', 'false'), ('Update', update),
        ], self.page_vis(card_vis))
        self.cards.append(control(card, 'TypedDataCard@1.0.7', props, CARD, variant='ClassicComboBoxEdit',
                                  children=kids))
        if it['required'] and not reviewer:
            self.missing.append((self.wrap(truck_vis, f'!{yes_box}.Value && !{no_box}.Value'),
                                 f'"Answer: " & DataCardKey{n}.Text'))

        if cmt and not reviewer:
            self.missing.append((self.wrap(truck_vis, f'{problem_box}.Value && IsBlank({cmt}.Text)'),
                                 f'"Comment needed: " & DataCardKey{n}.Text'))
            self.defects.append((f, n, problem_box, cmt, truck_vis))
        self.missing += photo_missing_list
        if reviewer:
            self.weekly.append((f, week_var, yes_box, no_box, n, cmt))

    def page_vis(self, vis=None):
        """Card Visible: its own rule plus 'on the current page'."""
        return self.wrap(vis, f'ctxSec = {fx_str(self.page_key)}')

    @staticmethod
    def wrap(vis, cond):
        return f'{vis} && {cond}' if vis else cond

    @staticmethod
    def comment_box(it, name, problem_box, yes_box, reviewer, week_var, on_change=None):
        """Multi-line comment inside the item's card, below the Yes/No boxes. Saved to the defects list,
        not to a column. Reviewing: shows the saved defect comment, view-only (weekly reviewer items
        stay editable until a defect row exists)."""
        defect = f'LookUp(colCheckDefects, ItemField = {fx_str(it["field"])})'
        if reviewer:
            default = f'{defect}.Comment'
            dm = f'If(IsBlank({defect}), DisplayMode.Edit, DisplayMode.View)'
            vis = f'IsBlank({week_var}) && {problem_box}.Value'
        else:
            default = f'If(varReviewing, {defect}.Comment, {draft_value(it["field"])}.c)'
            dm = 'Parent.DisplayMode'
            vis = f'{problem_box}.Value'
        hint = 'Describe the damage' if it.get('commentOn') == 'Yes' else 'Say what is wrong'
        return control(name, 'Classic/TextInput@2.3.2', [
            ('Mode', 'TextMode.MultiLine'),
            ('BorderColor', f'If(IsBlank(Self.Text) && Self.DisplayMode = DisplayMode.Edit, {RED}, {LINE})'),
            ('Color', INK), ('Default', default), ('DelayOutput', 'true'),
            ('DisabledBorderColor', CLEAR), ('DisabledColor', 'RGBA(161, 159, 157, 1)'),
            ('DisabledFill', 'RGBA(242, 242, 241, 0)'), ('DisplayMode', dm), ('Font', "Font.'Segoe UI'"),
            ('Height', '80'), ('HintText', fx_str(hint)), ('HoverBorderColor', TEAL),
            ('HoverColor', 'RGBA(50, 49, 48, 1)'), ('HoverFill', WHITE)] + (
            [('OnChange', on_change)] if on_change else []) + [('PaddingLeft', '5'),
            ('PressedBorderColor', TEAL), ('PressedColor', 'RGBA(50, 49, 48, 1)'), ('PressedFill', WHITE),
            ('RadiusBottomLeft', '8'), ('RadiusBottomRight', '8'), ('RadiusTopLeft', '8'),
            ('RadiusTopRight', '8'), ('Size', '15'), ('Tooltip', fx_str(hint)), ('Visible', vis),
            ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', f'{yes_box}.Y + {yes_box}.Height + 4'),
        ], KID)

    def add_photo_only(self, it):
        card = 'crd' + it['field']
        sfx = card[3:]
        truck_vis = self.vis_rule(it)
        kids = [title_label(f'lbl{sfx}Title', it['proposedName'])]
        below = f'lbl{sfx}Title.Y + lbl{sfx}Title.Height'
        if it['instruction']:
            kids.append(hint_label(f'lbl{sfx}Hint', it['instruction'], f'{below} + 2'))
            below = f'lbl{sfx}Hint.Y + lbl{sfx}Hint.Height'
        pc, miss = photo_controls(it, sfx, f'{below} + 8', None)
        kids += pc
        if it['required']:
            self.missing += [(self.wrap(truck_vis, c), m) for c, m in miss]
        props = [('BorderColor', LINE), ('DisplayName', fx_str(it['proposedName'])),
                 ('Visible', self.page_vis(self.wrap(truck_vis, '!varReviewing'))),
                 ('Width', 'Parent.Width'), ('WidthFit', 'true'), ('X', '0'), ('Y', str(self.take_row()))]
        self.cards.append(control(card, 'TypedDataCard@1.0.7', props, CARD, variant='BlankCard', children=kids))

    def add_date(self, it):
        f = it['field']
        card, n = self.card_names(it)
        sfx = card[3:]
        truck_vis = self.vis_rule(it)
        kids = [key_label(n)]
        below = f'DataCardKey{n}.Y + DataCardKey{n}.Height'
        if it['instruction']:
            kids.append(hint_label(f'lbl{sfx}Hint', it['instruction'], f'{below} + 2'))
            below = f'lbl{sfx}Hint.Y + lbl{sfx}Hint.Height'
        # truckDate: the Trucks list has the date -> show it read-only (no picker, no photo)
        td = f"varTruckInfo.{it['truckDate']}" if it.get('truckDate') else None
        no_td = f'IsBlank({td})' if td else None     # fall back to picker + photo
        picker = f'DataCardValue{n}'
        draft = f'With({{d: {draft_value(f)}.a}}, If(varReviewing || IsBlank(d), Parent.Default, DateValue(d)))'
        kids.append(control(picker, 'Classic/DatePicker@2.6.0', [
            ('BorderColor', 'If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)'), ('Color', INK),
            ('Height', '48'), ('DefaultDate', draft), ('DisabledBorderColor', CLEAR),
            ('DisabledColor', 'RGBA(161, 159, 157, 1)'), ('DisabledFill', 'RGBA(242, 242, 241, 0)'),
            ('DisplayMode', 'Parent.DisplayMode'), ('EndYear', 'Year(Today())+100'), ('Fill', WHITE),
            ('Font', "Font.'Segoe UI'"), ('IconBackground', TEAL), ('IconFill', WHITE), ('IsEditable', 'true'),
            ('OnChange', draft_save(f, 'Text(Self.SelectedDate, "yyyy-mm-dd")')),
            ('PaddingBottom', '0'), ('PaddingLeft', 'If(Self.DisplayMode = DisplayMode.Edit, 5, 0)'),
            ('Size', '15'), ('StartYear', '1899'), ('Tooltip', 'Parent.DisplayName'),
        ] + ([('Visible', f'varReviewing || {no_td}')] if td else []) + [
            ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', f'{below} + 5'),
        ], KID, metadata='FieldValue'))
        err_y = f'{picker}.Y + {picker}.Height'
        if td:
            date_lbl, status_lbl = f'lbl{sfx}TruckDate', f'lbl{sfx}DueStatus'
            shown = f'!varReviewing && !{no_td}'

            def by_status(expired, due, ok):
                return (f'If({td} < Today(), {expired}, {td} <= DateAdd(Today(), 30, TimeUnit.Days), '
                        f'{due}, {ok})')
            kids.append(control(date_lbl, 'Label@2.5.1', [
                ('BorderStyle', 'BorderStyle.None'), ('Color', INK), ('Font', "Font.'Segoe UI'"),
                ('FontWeight', 'FontWeight.Semibold'), ('Height', '48'), ('PaddingLeft', '0'), ('Size', '15'),
                ('Text', f'Text({td}, "dd mmm yyyy")'), ('Visible', shown), ('Width', '150'),
                ('X', '30'), ('Y', f'{below} + 5'),
            ], KID))
            kids.append(control(status_lbl, 'Label@2.5.1', [
                ('Align', 'Align.Center'), ('BorderStyle', 'BorderStyle.None'),
                ('Color', by_status(WHITE, INK, DARK_TEAL)), ('Fill', by_status(RED, YELLOW_TINT, TINT)),
                ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '36'),
                ('PaddingLeft', '8'), ('PaddingRight', '8'), ('Size', '13'),
                ('Text', by_status('"Expired"', '"Due within 30 days"', '"OK"')), ('Visible', shown),
                ('Width', 'Parent.Width - 220'), ('Wrap', 'true'), ('X', '190'), ('Y', f'{below} + 11'),
            ], KID))
            err_y = f'If({picker}.Visible, {err_y}, {date_lbl}.Y + {date_lbl}.Height)'
        kids.append(error_label(n, err_y))
        kids.append(star_label(n))
        photo_missing_list = []
        fallback = self.wrap(truck_vis, no_td) if td else truck_vis
        if it['photo'] != 'none':
            pc, miss = photo_controls(it, sfx, f'ErrorMessage{n}.Y + ErrorMessage{n}.Height - 4', None,
                                      self.wrap('!varReviewing', no_td))
            kids += pc
            if it['required']:
                photo_missing_list = [(self.wrap(fallback, c), m) for c, m in miss]
        required = self.wrap(fallback, '!varReviewing') if it['required'] else 'false'
        update = f'If(IsBlank({td}), {picker}.SelectedDate, {td})' if td else f'{picker}.SelectedDate'
        props = [('DisplayMode', 'If(varReviewing, DisplayMode.View, DisplayMode.Edit)')] + card_frame(
            self.take_row(), [
                ('DataField', fx_str(f)), ('Default', f'ThisItem.{f}'),
                ('DisplayName', f"DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'{f}')"),
                ('Required', required), ('Update', update),
            ], self.page_vis(truck_vis))
        self.cards.append(control(card, 'TypedDataCard@1.0.7', props, CARD, variant='ClassicDateEdit',
                                  children=kids))
        if it['required']:
            self.missing.append((self.wrap(fallback, f'IsBlank({picker}.SelectedDate)'),
                                 f'"Fill in: " & DataCardKey{n}.Text'))
        self.missing += photo_missing_list

    def add_odometer(self, it):
        ptype, item = photo_type(it), it['photoSlots'][0]
        missing = f'IsEmpty(Filter(colPhotos, Type = {fx_str(ptype)}))'
        taken = '!' + missing
        y = 'ErrorMessage69.Y + ErrorMessage69.Height - 4'
        extra = secondary_button('btnOdometerPhoto', f'If({taken}, "Retake photo", "Take photo")',
                                 photo_onselect(ptype, fx_str(item)), '150', '30', y, '!varReviewing')
        extra += status_label('lblOdometerPhoto', taken, '"✓ Photo taken"', '"Photo required"',
                              'Parent.Width - 210', '192', y, '!varReviewing')
        self.add_template(
            T_ODOMETER + '\n'.join(extra) + '\n',
            draft_text_mod('field_50', numeric=True))
        self.missing.append(('IsBlank(DataCardValue69.Text)', '"Fill in: " & DataCardKey69.Text'))
        self.missing.append((missing, '"Photo needed: odometer"'))

    # -- whole screen
    def build(self):
        sections = {s['key']: s for s in self.data['sections']}
        items = sorted([i for i in self.data['items'] if not i.get('hidden')], key=lambda i: i['order'])
        self.page_key = FIRST_PAGE
        self.add_truck_note()
        current = None
        for it in items:
            sec = it['section']
            if sec != current:
                current = sec
                self.page_key = FIRST_PAGE if sec in ('header', FIRST_PAGE) else sec
                if self.page_key not in self.page_keys:
                    self.page_keys.append(self.page_key)
                if sec != 'header':
                    sec_items = [i for i in items if i['section'] == sec]
                    review_shows = any(i['kind'] != 'photoOnly' for i in sec_items)
                    self.add_heading(sec, sections[sec]['title'], None if review_shows else '!varReviewing')
            if it['kind'] != 'photoOnly' or sec == 'header':
                self.review_pages.add(self.page_key)
            first_gate = len(self.missing)
            f = it['field']
            if f == 'field_1':
                self.add_template(T_TRUCKNO, (
                    '                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)\n',
                    '                  DisplayMode: =DisplayMode.View\n'))
                self.missing.append(('IsBlank(DataCardValue18.Text)', '"Truck number missing: go back and pick a truck"'))
            elif f == 'field_2':
                self.add_template(T_DRIVERNAME)
            elif f == 'field_3':
                self.add_template(T_SITE, ('                  Required: =false\n',
                                           '                  Required: =!varReviewing\n'),
                                  draft_text_mod('field_3'))
                self.missing.append(('IsBlank(DataCardValue20.Text)', '"Fill in: " & DataCardKey20.Text'))
            elif f == 'field_50':
                self.add_odometer(it)
            elif f == 'NextServiceDue':
                self.add_template(self.renumber(T_NEXTSERVICE, 90), draft_text_mod('NextServiceDue', numeric=True))
            elif f == 'field_51':
                self.add_template(T_REMARKS, draft_text_mod('field_51'))
            elif it['kind'] == 'yesno':
                self.add_yesno(it)
            elif it['kind'] == 'date':
                self.add_date(it)
            elif it['kind'] == 'photoOnly':
                self.add_photo_only(it)
            else:
                raise SystemExit(f'No card builder for {f} ({it["kind"]})')
            self.missing[first_gate:] = [(c, m, self.page_key) for c, m in self.missing[first_gate:]]
        assert self.page_keys[-1] == LAST_PAGE, self.page_keys
        self.page_key = LAST_PAGE
        self.add_template(T_SIGNOFF)

    def on_visible(self):
        lines = [
            "Set(varTruckInfo, LookUp('GF Fleet Trucks', Title = If(varReviewing, varCheck.field_1, varTruck) && ActiveYN = true));",
            f'Set(varTyreCount, Min(Coalesce(varTruckInfo.NoOfTyres, 6), {MAX_TYRES}));',
            "If(varReviewing, ClearCollect(colCheckDefects, Filter('GF Fleet Checklist Defects', "
            "ChecklistID = varCheck.ID)), Clear(colCheckDefects));",
            self.pages_formula() + ';',
            f'If(IsBlank(ctxSec), UpdateContext({{ctxPage: 1, ctxSec: {fx_str(FIRST_PAGE)}}}));',
        ]
        if self.weekly:
            # The truck's latest 50 checklists come from SharePoint (truck filter + sort by ID are
            # delegable); the week's dates are checked in the app, so there's no delegation warning.
            sets = []
            for f, var, *_ in self.weekly:
                sets.append(
                    f"        Set({var}, First(Sort(Filter(wkRows, "
                    f'Created >= wkStart && Created < wkEnd && {f}.Value = "Yes"), Created, SortOrder.Descending)))')
            blanks = [f'Set({w[1]}, Blank())' for w in self.weekly]
            lines += [
                'If(varReviewing,',
                '    With({wkDay: Date(Year(varCheck.Created), Month(varCheck.Created), Day(varCheck.Created)),',
                "          wkRows: FirstN(Sort(Filter('Fleet Checklist', field_1 = varCheck.field_1), ID, SortOrder.Descending), 50)},",
                '    With({wkStart: DateAdd(wkDay, 1 - Weekday(wkDay, StartOfWeek.Monday), TimeUnit.Days),',
                '          wkEnd: DateAdd(wkDay, 8 - Weekday(wkDay, StartOfWeek.Monday), TimeUnit.Days)},',
                ';\n'.join(sets) + ')),',
                '    ' + ';\n    '.join(blanks) + ')',
            ]
        return '\n'.join(lines)

    def pages_formula(self):
        """colPages: PageNo, SecKey, SecTitle. Reviewing skips pages with only driver photo cards."""
        titles = {s['key']: s['title'] for s in self.data['sections']}

        def table(keys):
            rows = [f'{{PageNo: {i}, SecKey: {fx_str(k)}, SecTitle: {fx_str(titles[k])}}}'
                    for i, k in enumerate(keys, 1)]
            return 'Table(\n        ' + ',\n        '.join(rows) + ')'
        review = [k for k in self.page_keys if k in self.review_pages]
        return f'ClearCollect(colPages, If(varReviewing,\n    {table(review)},\n    {table(self.page_keys)}))'

    def todo_count(self):
        """Number of Submit-gate entries still open on the current page."""
        parts = []
        for key in self.page_keys:
            conds = [c for c, _m, k in self.missing if k == key]
            if conds:
                parts.append(f'    {fx_str(key)},\n        ' + ' +\n        '.join(f'If({c}, 1, 0)' for c in conds))
        return 'Switch(ctxSec,\n' + ',\n'.join(parts) + ',\n    0)'

    def first_missing_page(self):
        parts = [f'    {c},\n        {fx_str(k)},' for c, _m, k in self.missing]
        return 'If(\n' + '\n'.join(parts) + '\n    ctxSec)'

    def defect_rows(self):
        """Rows for frmPreTrip.OnSuccess: {f, name, no, c} per driver item with a comment box."""
        rows = []
        for f, n, box, cmt, truck_vis in self.defects:
            rows.append(f'{" " * 30}{{f: {fx_str(f)}, name: DataCardKey{n}.Text, '
                        f'no: {self.wrap(truck_vis, box + ".Value")}, c: {cmt}.Text}}')
        return ',\n'.join(rows)

    def submit_text(self):
        parts = []
        for cond, msg, _k in self.missing:
            parts.append(f'    {cond},\n        {msg},')
        return 'If(\n' + '\n'.join(parts) + '\n    "Submit")'

    def signoff_onselect(self):
        checks, patches = [], []
        for f, var, yes, no, key_n, cmt in self.weekly:
            checks.append(f'    IsBlank({var}) && !{yes}.Value && !{no}.Value,\n'
                          f'    Notify("Answer " & DataCardKey{key_n}.Text & " first.", NotificationType.Warning),')
            rec = f'{f}: {{Value: If({yes}.Value, "Yes", "No")}}'
            patches.append(f"        If(IsBlank({var}), Patch('Fleet Checklist', LookUp('Fleet Checklist', ID = varCheck.ID), {{{rec}}}));")
            if cmt:
                checks.append(f'    IsBlank({var}) && {no}.Value && IsBlank({cmt}.Text),\n'
                              f'    Notify("Add a comment for " & DataCardKey{key_n}.Text & ".", NotificationType.Warning),')
                # a No adds one defect row (the comment box is view-only once the row exists)
                patches.append(
                    f"        If(IsBlank({var}) && {no}.Value && IsBlank(LookUp(colCheckDefects, ItemField = {fx_str(f)})),\n"
                    f"            Patch('GF Fleet Checklist Defects', Defaults('GF Fleet Checklist Defects'), {{\n"
                    f'                Title: DataCardKey{key_n}.Text, ChecklistID: varCheck.ID, Truck: varCheck.field_1,\n'
                    f'                ItemField: {fx_str(f)}, Comment: {cmt}.Text}}));')
        return '\n'.join([
            'If(IsBlank(DataCardValue1.Selected.Value) || IsBlank(DataCardValue2.Selected.Value),',
            '    Notify("Choose Approval For Delivery and Send For Repairs first.", NotificationType.Warning),',
            *checks,
            '    IfError(',
            "        Patch('Fleet Checklist', LookUp('Fleet Checklist', ID = varCheck.ID), {",
            '            field_52: DataCardValue1.Selected,',
            '            field_53: DataCardValue2.Selected,',
            '            field_54: Coalesce(DataCardValue3.Text, User().FullName),',
            '            field_55: Coalesce(DataCardValue4.SelectedDate, Today())',
            '        });',
            *patches,
            '        Notify("Sign-off saved", NotificationType.Success);',
            '        Navigate(scrReview),',
            '        Notify("Sign-off not saved: " & FirstError.Message, NotificationType.Error, 0)))',
        ])

    def render(self):
        self.build()
        out = ['Screens:', '  scrPreTrip:', '    Properties:',
               '      Fill: =RGBA(243, 246, 246, 1)', '      ImagePosition: =ImagePosition.Fill',
               '      LoadingSpinnerColor: =RGBA(8, 144, 144, 1)']
        out += prop_lines('OnVisible', self.on_visible(), 6)
        out += T_CHROME.replace('@@DEFECT_ROWS@@', self.defect_rows()).rstrip('\n').split('\n')
        for c in self.cards:
            out += c
        footer = T_FOOTER
        def block(formula):
            return '\n'.join(' ' * 26 + ln if ln else '' for ln in ('=' + formula).split('\n'))
        footer = footer.replace('@@SUBMIT_TEXT@@', block(self.submit_text()))
        footer = footer.replace('@@SIGNOFF_ONSELECT@@', block(self.signoff_onselect()))
        footer = footer.replace('@@TODO_COUNT@@', block(self.todo_count() + ' & " still to do"'))
        footer = footer.replace('@@GO_MISSING@@', block(
            f'With({{goKey: {self.first_missing_page()}}},\n'
            '    UpdateContext({ctxSec: goKey, ctxPage: LookUp(colPages, SecKey = goKey).PageNo}))'))
        out += footer.rstrip('\n').split('\n')
        return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- templates (verbatim from the Nov 2026 screen)
T_CHROME = r'''    Children:
      - conPreTripHeader:
          Control: GroupContainer@1.5.0
          Variant: AutoLayout
          Properties:
            Width: =Parent.Width
            X: =0
            Y: =0
            Fill: =RGBA(255, 255, 255, 1)
            FillPortions: =0
            Height: =84
            LayoutAlignItems: =LayoutAlignItems.Center
            LayoutDirection: =LayoutDirection.Horizontal
            LayoutGap: =12
            LayoutMinHeight: =84
            LayoutMinWidth: =16
            PaddingBottom: =14
            PaddingLeft: =12
            PaddingRight: =16
            PaddingTop: =14
          Children:
            - icoPreTripBack:
                Control: Classic/Icon@2.5.0
                Properties:
                  AccessibleLabel: ="Go back"
                  Color: =RGBA(0, 112, 112, 1)
                  Height: =40
                  Icon: =Icon.ChevronLeft
                  OnSelect: =Back()
                  PaddingBottom: =8
                  PaddingLeft: =8
                  PaddingRight: =8
                  PaddingTop: =8
                  Tooltip: ="Go back"
                  Width: =40
            - imgPreTripLogo:
                Control: Image@2.2.3
                Properties:
                  AccessibleLabel: ="GF logo"
                  Height: =48
                  Image: ='gf-logo'
                  ImagePosition: =ImagePosition.Fit
                  Width: =48
            - conPreTripTitles:
                Control: GroupContainer@1.5.0
                Variant: AutoLayout
                Properties:
                  FillPortions: =1
                  Height: =58
                  LayoutAlignItems: =LayoutAlignItems.Stretch
                  LayoutDirection: =LayoutDirection.Vertical
                  LayoutGap: =2
                  LayoutJustifyContent: =LayoutJustifyContent.Center
                  LayoutMinHeight: =16
                  LayoutMinWidth: =16
                Children:
                  - lblPreTripTitle:
                      Control: Label@2.5.1
                      Properties:
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(0, 112, 112, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Bold
                        Height: =28
                        PaddingLeft: =0
                        Size: =18
                        Text: =If(varReviewing, "Review checklist", "Fleet checklist")
                  - lblPreTripSubtitle:
                      Control: Label@2.5.1
                      Properties:
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(96, 108, 118, 1)
                        Font: =Font.'Segoe UI'
                        Height: =22
                        PaddingLeft: =0
                        Size: =12
                        Text: |-
                          ="Truck: " & If(varReviewing, varCheck.field_1, Coalesce(varTruck, "not selected"))
      - conPreTripStripe:
          Control: GroupContainer@1.5.0
          Variant: AutoLayout
          Properties:
            Width: =Parent.Width
            X: =0
            Y: =84
            Fill: =RGBA(255, 255, 255, 1)
            FillPortions: =0
            Height: =6
            LayoutAlignItems: =LayoutAlignItems.Stretch
            LayoutDirection: =LayoutDirection.Horizontal
            LayoutGap: =0
            LayoutMinHeight: =6
            LayoutMinWidth: =16
          Children:
            - recPreTripStripe1:
                Control: Rectangle@2.3.0
                Properties:
                  BorderColor: =RGBA(0, 0, 0, 0)
                  Fill: =RGBA(8, 144, 144, 1)
                  FillPortions: =1
                  Height: =6
            - recPreTripStripe2:
                Control: Rectangle@2.3.0
                Properties:
                  BorderColor: =RGBA(0, 0, 0, 0)
                  Fill: =RGBA(0, 184, 216, 1)
                  FillPortions: =1
                  Height: =6
            - recPreTripStripe3:
                Control: Rectangle@2.3.0
                Properties:
                  BorderColor: =RGBA(0, 0, 0, 0)
                  Fill: =RGBA(248, 208, 0, 1)
                  FillPortions: =1
                  Height: =6
            - recPreTripStripe4:
                Control: Rectangle@2.3.0
                Properties:
                  BorderColor: =RGBA(0, 0, 0, 0)
                  Fill: =RGBA(160, 200, 80, 1)
                  FillPortions: =1
                  Height: =6
      - frmPreTrip:
          Control: Form@2.4.4
          Variant: Classic
          Layout: Vertical
          Properties:
            BorderColor: =RGBA(0, 0, 0, 0)
            Fill: =RGBA(255, 255, 255, 1)
            DataSource: ='Fleet Checklist'
            DefaultMode: =FormMode.New
            Height: =Parent.Height - 90 - 146
            Item: =varCheck
            NumberOfColumns: =1
            OnFailure: |-
              =Notify("Not saved: " & frmPreTrip.Error, NotificationType.Error, 0)
            OnSuccess: |-
              =If(varReviewing,
                  Notify("Sign-off saved", NotificationType.Success);
                  Navigate(scrReview),
                  With({recId: frmPreTrip.LastSubmit.ID,
                        defects: Filter(
                          Table(
@@DEFECT_ROWS@@
                          ), no)},
                      ForAll(defects,
                          IfError(
                              Patch('GF Fleet Checklist Defects', Defaults('GF Fleet Checklist Defects'), {
                                  Title: name, ChecklistID: recId, Truck: varTruck, ItemField: f,
                                  Comment: c}); true,
                              Collect(colPendingDefects, {RecId: recId, Truck: varTruck, Title: name, ItemField: f, Comment: c}); false));
                      ForAll(colPhotos,
                          IfError(
                              'SaveFleetPhotos'.Run(
                                  Coalesce(varTruck, "Unknown"),
                                  Coalesce(ThisRecord.Type, "Photo"),
                                  Coalesce(ThisRecord.Item, ThisRecord.Type, "Photo"),
                                  recId,
                                  "Fleet Checklist",
                                  {file: {name: "photo.jpg", contentBytes: ThisRecord.Img}}); true,
                              Collect(colPendingPhotos, {RecId: recId, Truck: Coalesce(varTruck, "Unknown"),
                                  Type: Coalesce(ThisRecord.Type, "Photo"), Item: Coalesce(ThisRecord.Item, ThisRecord.Type, "Photo"),
                                  Img: ThisRecord.Img}); false));
                      IfError(SaveData(colPendingDefects, "fcCheckRetry"); SaveData(colPendingPhotos, "fcCheckRetryPhotos"); true, false);
                      If(IsEmpty(colPendingDefects) && IsEmpty(colPendingPhotos),
                          Notify("Checklist saved", NotificationType.Success),
                          Notify("Checklist saved. Some photos or defect notes did not upload; they are kept on this phone and sent when you next open the app with signal.", NotificationType.Warning, 0)));
                  Clear(colPhotos);
                  Clear(colDraft);
                  IfError(SaveData(colDraft, "fcCheckDraft"); SaveData(colPhotos, "fcCheckPhotos"); true, false);
                  ResetForm(frmPreTrip);
                  UpdateContext({ctxPage: 1, ctxSec: "licence"});
                  Navigate(scrHome))
            Width: =Parent.Width
            Y: =90
          Children:
'''

T_TRUCKNO = r'''            - crdTruckNo:
                Control: TypedDataCard@1.0.7
                Variant: ClassicTextualEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_1"
                  Default: =If(varReviewing, ThisItem.field_1, varTruck)
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_1')
                  MaxLength: =DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, 'field_1')
                  Required: =!varReviewing
                  Update: =DataCardValue18.Text
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =0
                Children:
                  - DataCardKey18:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue18:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        MaxLength: =Parent.MaxLength
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey18.Y + DataCardKey18.Height + 5
                  - ErrorMessage18:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue18.Y + DataCardValue18.Height
                  - StarVisible18:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey18.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey18.Y
'''

T_DRIVERNAME = r'''            - crdDriverName:
                Control: TypedDataCard@1.0.7
                Variant: ClassicTextualEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_2"
                  Default: |+
                    =If(varReviewing, ThisItem.field_2, User().FullName)
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_2')
                  MaxLength: =DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, 'field_2')
                  Required: =false
                  Update: =DataCardValue19.Text
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =1
                Children:
                  - DataCardKey19:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue19:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        MaxLength: =Parent.MaxLength
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey19.Y + DataCardKey19.Height + 5
                  - ErrorMessage19:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue19.Y + DataCardValue19.Height
                  - StarVisible19:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey19.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey19.Y
'''

T_SITE = r'''            - crdSite:
                Control: TypedDataCard@1.0.7
                Variant: ClassicTextualEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_3"
                  Default: =ThisItem.field_3
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_3')
                  MaxLength: =DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, 'field_3')
                  Required: =false
                  Update: =DataCardValue20.Text
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =2
                Children:
                  - DataCardKey20:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue20:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        MaxLength: =Parent.MaxLength
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey20.Y + DataCardKey20.Height + 5
                  - ErrorMessage20:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue20.Y + DataCardValue20.Height
                  - StarVisible20:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey20.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey20.Y
'''

T_REMARKS = r'''            - crdRemarks:
                Control: TypedDataCard@1.0.7
                Variant: ClassicTextualEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_51"
                  Default: =ThisItem.field_51
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_51')
                  MaxLength: =DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, 'field_51')
                  Required: =false
                  Update: =DataCardValue26.Text
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =70
                Children:
                  - DataCardKey26:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue26:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        Mode: =TextMode.MultiLine
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =104
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        MaxLength: =Parent.MaxLength
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey26.Y + DataCardKey26.Height + 5
                  - ErrorMessage26:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue26.Y + DataCardValue26.Height
                  - StarVisible26:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey26.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey26.Y
'''

T_ODOMETER = r'''            - crdOdometer:
                Control: TypedDataCard@1.0.7
                Variant: ClassicNumberEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_50"
                  Default: =ThisItem.field_50
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_50')
                  Required: =!varReviewing
                  Update: =Value(DataCardValue69.Text)
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =71
                Children:
                  - DataCardKey69:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue69:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        Format: =TextFormat.Number
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey69.Y + DataCardKey69.Height + 5
                  - ErrorMessage69:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue69.Y + DataCardValue69.Height
                  - StarVisible69:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey69.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey69.Y
'''

T_NEXTSERVICE = r'''            - crdNextServiceDue:
                Control: TypedDataCard@1.0.7
                Variant: ClassicNumberEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="NextServiceDue"
                  Default: =ThisItem.NextServiceDue
                  DisplayMode: =If(varReviewing, DisplayMode.View, DisplayMode.Edit)
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'NextServiceDue')
                  Required: =false
                  Update: =Value(DataCardValue90.Text)
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =72
                Children:
                  - DataCardKey90:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue90:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        Format: =TextFormat.Number
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey90.Y + DataCardKey90.Height + 5
                  - ErrorMessage90:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue90.Y + DataCardValue90.Height
                  - StarVisible90:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey90.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey90.Y
'''

T_SIGNOFF = r'''            - crdApproval:
                Control: TypedDataCard@1.0.7
                Variant: ClassicComboBoxEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_52"
                  Default: =ThisItem.field_52
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_52')
                  Required: =varReviewing
                  Update: =DataCardValue1.Selected
                  Visible: =varReviewing
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =73
                Children:
                  - DataCardKey1:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =lblDeclarationText.Y + lblDeclarationText.Height + 12
                  - DataCardValue1:
                      Control: Classic/DropDown@2.3.1
                      MetadataKey: FieldValue
                      Properties:
                        AllowEmptySelection: =true
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        ChevronBackground: =RGBA(8, 144, 144, 1)
                        ChevronDisabledBackground: =RGBA(242, 242, 241, 0)
                        ChevronDisabledFill: =RGBA(161, 159, 157, 1)
                        ChevronFill: =RGBA(255, 255, 255, 1)
                        ChevronHoverBackground: =RGBA(0, 112, 112, 1)
                        ChevronHoverFill: =RGBA(255, 255, 255, 1)
                        Color: =RGBA(31, 41, 51, 1)
                        Default: =ThisItem.field_52.Value
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Fill: =RGBA(255, 255, 255, 1)
                        Height: =48
                        Size: =15
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(31, 41, 51, 1)
                        HoverFill: =RGBA(226, 243, 242, 1)
                        Items: =Choices([@'Fleet Checklist'].'field_52')
                        Items.Value: =Value
                        PaddingLeft: =If(Self.DisplayMode = DisplayMode.Edit, 5, 0)
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(255, 255, 255, 1)
                        PressedFill: =RGBA(8, 144, 144, 1)
                        SelectionColor: =RGBA(255, 255, 255, 1)
                        SelectionFill: =RGBA(8, 144, 144, 1)
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey1.Y + DataCardKey1.Height + 5
                  - ErrorMessage1:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue1.Y + DataCardValue1.Height
                  - StarVisible1:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey1.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey1.Y
                  - lblSecDeclaration:
                      Control: Label@2.5.1
                      Properties:
                        Align: =Align.Left
                        Fill: =RGBA(8, 144, 144, 1)
                        PaddingLeft: =16
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(255, 255, 255, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Bold
                        Size: =16
                        Text: ="Declaration by the Site Engineer / Fleet Controller"
                        Width: =Parent.Width
                        X: =0
                  - lblDeclarationText:
                      Control: Label@2.5.1
                      Properties:
                        AutoHeight: =true
                        Align: =Align.Left
                        Wrap: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(96, 108, 118, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        Height: =60
                        Text: ="This is to verify that the driver has carried out the above checks and I have satisfied myself by cross-checking"
                        Width: =Parent.Width - 48
                        X: =24
                        Y: =lblSecDeclaration.Y + lblSecDeclaration.Height + 4
            - crdSendForRepairs:
                Control: TypedDataCard@1.0.7
                Variant: ClassicComboBoxEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_53"
                  Default: =ThisItem.field_53
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_53')
                  Required: =varReviewing
                  Update: =DataCardValue2.Selected
                  Visible: =varReviewing
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =74
                Children:
                  - DataCardKey2:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue2:
                      Control: Classic/DropDown@2.3.1
                      MetadataKey: FieldValue
                      Properties:
                        AllowEmptySelection: =true
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        ChevronBackground: =RGBA(8, 144, 144, 1)
                        ChevronDisabledBackground: =RGBA(242, 242, 241, 0)
                        ChevronDisabledFill: =RGBA(161, 159, 157, 1)
                        ChevronFill: =RGBA(255, 255, 255, 1)
                        ChevronHoverBackground: =RGBA(0, 112, 112, 1)
                        ChevronHoverFill: =RGBA(255, 255, 255, 1)
                        Color: =RGBA(31, 41, 51, 1)
                        Default: =ThisItem.field_53.Value
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Fill: =RGBA(255, 255, 255, 1)
                        Height: =48
                        Size: =15
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(31, 41, 51, 1)
                        HoverFill: =RGBA(226, 243, 242, 1)
                        Items: =Choices([@'Fleet Checklist'].'field_53')
                        Items.Value: =Value
                        PaddingLeft: =If(Self.DisplayMode = DisplayMode.Edit, 5, 0)
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(255, 255, 255, 1)
                        PressedFill: =RGBA(8, 144, 144, 1)
                        SelectionColor: =RGBA(255, 255, 255, 1)
                        SelectionFill: =RGBA(8, 144, 144, 1)
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey2.Y + DataCardKey2.Height + 5
                  - ErrorMessage2:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue2.Y + DataCardValue2.Height
                  - StarVisible2:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey2.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey2.Y
            - crdDeclarationDate:
                Control: TypedDataCard@1.0.7
                Variant: ClassicDateEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_55"
                  Default: =If(varReviewing, Coalesce(ThisItem.field_55, Today()), Blank())
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_55')
                  Required: =false
                  Update: =DataCardValue4.SelectedDate
                  Visible: =varReviewing
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =75
                Children:
                  - DataCardKey4:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue4:
                      Control: Classic/DatePicker@2.6.0
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        DefaultDate: =Parent.Default
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        EndYear: =Year(Today())+100
                        Fill: =RGBA(245, 245, 245, 1)
                        Font: =Font.'Segoe UI'
                        IconBackground: =RGBA(0, 120, 212, 1)
                        IconFill: =RGBA(255, 255, 255, 1)
                        IsEditable: =true
                        PaddingBottom: =0
                        PaddingLeft: =If(Self.DisplayMode = DisplayMode.Edit, 5, 0)
                        Size: =13
                        StartYear: =1899
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey4.Y + DataCardKey4.Height + 5
                  - ErrorMessage4:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue4.Y + DataCardValue4.Height
                  - StarVisible4:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey4.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey4.Y
            - crdManagerName:
                Control: TypedDataCard@1.0.7
                Variant: ClassicTextualEdit
                Properties:
                  BorderColor: =RGBA(208, 216, 218, 1)
                  DataField: ="field_54"
                  Default: =If(varReviewing, Coalesce(ThisItem.field_54, User().FullName), Blank())
                  DisplayMode: =DisplayMode.View
                  DisplayName: =DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'field_54')
                  Height: =91
                  MaxLength: =DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, 'field_54')
                  Required: =false
                  Update: =DataCardValue3.Text
                  Visible: =varReviewing
                  Width: =Parent.Width
                  WidthFit: =true
                  X: =0
                  Y: =76
                Children:
                  - DataCardKey3:
                      Control: Label@2.5.1
                      MetadataKey: FieldName
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(31, 41, 51, 1)
                        Size: =14
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =34
                        PaddingLeft: =0
                        Text: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        Wrap: =true
                        X: =30
                        Y: =18
                  - DataCardValue3:
                      Control: Classic/TextInput@2.3.2
                      MetadataKey: FieldValue
                      Properties:
                        BorderColor: =If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)
                        Color: =RGBA(31, 41, 51, 1)
                        Height: =48
                        Size: =15
                        Default: =Parent.Default
                        DelayOutput: =true
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        DisabledFill: =RGBA(242, 242, 241, 0)
                        DisplayMode: =Parent.DisplayMode
                        Font: =Font.'Segoe UI'
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(50, 49, 48, 1)
                        HoverFill: =RGBA(255, 255, 255, 1)
                        MaxLength: =Parent.MaxLength
                        PaddingLeft: =5
                        PressedBorderColor: =RGBA(8, 144, 144, 1)
                        PressedColor: =RGBA(50, 49, 48, 1)
                        PressedFill: =RGBA(255, 255, 255, 1)
                        RadiusBottomLeft: =8
                        RadiusBottomRight: =8
                        RadiusTopLeft: =8
                        RadiusTopRight: =8
                        Tooltip: =Parent.DisplayName
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardKey3.Y + DataCardKey3.Height + 5
                  - ErrorMessage3:
                      Control: Label@2.5.1
                      MetadataKey: ErrorMessage
                      Properties:
                        AutoHeight: =true
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(168, 0, 0, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(168, 0, 0, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =10
                        Live: =Live.Assertive
                        PaddingBottom: =12
                        PaddingLeft: =0
                        PaddingRight: =0
                        PaddingTop: =0
                        Text: =Parent.Error
                        Visible: =Parent.DisplayMode=DisplayMode.Edit
                        Width: =Parent.Width - 60
                        X: =30
                        Y: =DataCardValue3.Y + DataCardValue3.Height
                  - StarVisible3:
                      Control: Label@2.5.1
                      MetadataKey: FieldRequired
                      Properties:
                        Align: =Align.Center
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        BorderThickness: =2
                        Color: =RGBA(196, 49, 75, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(161, 159, 157, 1)
                        FocusedBorderThickness: =4
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =DataCardKey3.Height
                        PaddingLeft: =0
                        Text: ="*"
                        Visible: =And(Parent.Required, Parent.DisplayMode=DisplayMode.Edit)
                        Width: =30
                        Wrap: =false
                        Y: =DataCardKey3.Y
'''

T_FOOTER = r'''      - conPreTripFooter:
          Control: GroupContainer@1.5.0
          Variant: AutoLayout
          Properties:
            DropShadow: =DropShadow.Light
            Fill: =RGBA(255, 255, 255, 1)
            Height: =146
            LayoutAlignItems: =LayoutAlignItems.Stretch
            LayoutDirection: =LayoutDirection.Vertical
            LayoutGap: =8
            PaddingBottom: =12
            PaddingLeft: =16
            PaddingRight: =16
            PaddingTop: =10
            Width: =Parent.Width
            X: =0
            Y: =Parent.Height - 146
          Children:
            - conPreTripProgress:
                Control: GroupContainer@1.5.0
                Variant: ManualLayout
                Properties:
                  Fill: =RGBA(208, 216, 218, 1)
                  FillPortions: =0
                  Height: =4
                  LayoutMinHeight: =4
                Children:
                  - recPreTripProgress:
                      Control: Rectangle@2.3.0
                      Properties:
                        BorderColor: =RGBA(0, 0, 0, 0)
                        Fill: =RGBA(8, 144, 144, 1)
                        Height: =4
                        Width: =Parent.Width * ctxPage / Max(1, CountRows(colPages))
                        X: =0
                        Y: =0
            - conPreTripInfo:
                Control: GroupContainer@1.5.0
                Variant: AutoLayout
                Properties:
                  FillPortions: =0
                  Height: =48
                  LayoutAlignItems: =LayoutAlignItems.Center
                  LayoutDirection: =LayoutDirection.Horizontal
                  LayoutGap: =8
                  LayoutMinHeight: =48
                Children:
                  - lblPreTripProgress:
                      Control: Label@2.5.1
                      Properties:
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(31, 41, 51, 1)
                        FillPortions: =1
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =48
                        PaddingLeft: =0
                        Size: =13
                        Text: ="Section " & ctxPage & " of " & CountRows(colPages) & " · " & LookUp(colPages, PageNo = ctxPage).SecTitle
                        Wrap: =true
                  - lblPreTripToDo:
                      Control: Label@2.5.1
                      Properties:
                        Align: =Align.Right
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(196, 49, 75, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        Height: =48
                        PaddingLeft: =0
                        PaddingRight: =0
                        Size: =13
                        Text: |-
@@TODO_COUNT@@
                        Visible: =!varReviewing && ctxPage < CountRows(colPages) && !StartsWith(Self.Text, "0 ")
                        Width: =110
                        Wrap: =true
                  - btnPreTripGoMissing:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(8, 144, 144, 1)
                        BorderStyle: =BorderStyle.Solid
                        BorderThickness: =2
                        Color: =RGBA(0, 112, 112, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(255, 255, 255, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(0, 112, 112, 1)
                        HoverFill: =RGBA(226, 243, 242, 1)
                        PressedBorderColor: =RGBA(0, 112, 112, 1)
                        PressedColor: =RGBA(0, 112, 112, 1)
                        PressedFill: =RGBA(226, 243, 242, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        Height: =48
                        OnSelect: |-
@@GO_MISSING@@
                        Size: =14
                        Text: ="Go to it"
                        Visible: =!varReviewing && ctxPage >= CountRows(colPages) && btnSubmitChecklist.Text <> "Submit"
                        Width: =110
            - conPreTripButtons:
                Control: GroupContainer@1.5.0
                Variant: AutoLayout
                Properties:
                  FillPortions: =0
                  Height: =56
                  LayoutAlignItems: =LayoutAlignItems.Center
                  LayoutDirection: =LayoutDirection.Horizontal
                  LayoutGap: =10
                  LayoutMinHeight: =56
                Children:
                  - btnPreTripBack:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(8, 144, 144, 1)
                        BorderStyle: =BorderStyle.Solid
                        BorderThickness: =2
                        Color: =RGBA(0, 112, 112, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(255, 255, 255, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(0, 112, 112, 1)
                        HoverFill: =RGBA(226, 243, 242, 1)
                        PressedBorderColor: =RGBA(0, 112, 112, 1)
                        PressedColor: =RGBA(0, 112, 112, 1)
                        PressedFill: =RGBA(226, 243, 242, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        Height: =56
                        OnSelect: |-
                          =UpdateContext({ctxPage: ctxPage - 1, ctxSec: LookUp(colPages, PageNo = ctxPage - 1).SecKey})
                        Size: =15
                        Text: ="Back"
                        Visible: =ctxPage > 1
                        Width: =88
                  - btnPhotos:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(8, 144, 144, 1)
                        BorderStyle: =BorderStyle.Solid
                        BorderThickness: =2
                        Color: =RGBA(0, 112, 112, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(255, 255, 255, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(8, 144, 144, 1)
                        HoverColor: =RGBA(0, 112, 112, 1)
                        HoverFill: =RGBA(226, 243, 242, 1)
                        PressedBorderColor: =RGBA(0, 112, 112, 1)
                        PressedColor: =RGBA(0, 112, 112, 1)
                        PressedFill: =RGBA(226, 243, 242, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        FillPortions: =1
                        Height: =56
                        OnSelect: |-
                          =Set(varPhotoType, Blank());
                          Set(varPhotoItem, Blank());
                          Navigate(scrPhotos)
                        Size: =15
                        Text: ="Photos (" & CountRows(colPhotos) & ")"
                        Visible: =!varReviewing
                  - btnPreTripNext:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(255, 255, 255, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(8, 144, 144, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        HoverColor: =RGBA(255, 255, 255, 1)
                        HoverFill: =RGBA(0, 112, 112, 1)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        PressedColor: =RGBA(255, 255, 255, 1)
                        PressedFill: =RGBA(0, 112, 112, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        FillPortions: =1
                        Height: =56
                        OnSelect: |-
                          =UpdateContext({ctxPage: ctxPage + 1, ctxSec: LookUp(colPages, PageNo = ctxPage + 1).SecKey})
                        Size: =15
                        Text: ="Next"
                        Visible: =ctxPage < CountRows(colPages)
                  - btnSubmitChecklist:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(255, 255, 255, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(8, 144, 144, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        HoverColor: =RGBA(255, 255, 255, 1)
                        HoverFill: =RGBA(0, 112, 112, 1)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        PressedColor: =RGBA(255, 255, 255, 1)
                        PressedFill: =RGBA(0, 112, 112, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        DisplayMode: =If(Self.Text = "Submit", DisplayMode.Edit, DisplayMode.Disabled)
                        FillPortions: =2
                        Height: =56
                        OnSelect: =SubmitForm(frmPreTrip)
                        Size: =If(Self.Text = "Submit", 15, 12)
                        Text: |-
@@SUBMIT_TEXT@@
                        Visible: =!varReviewing && ctxPage >= CountRows(colPages)
                  - btnSaveSignoff:
                      Control: Classic/Button@2.2.0
                      Properties:
                        BorderColor: =RGBA(0, 0, 0, 0)
                        BorderStyle: =BorderStyle.None
                        Color: =RGBA(255, 255, 255, 1)
                        DisabledBorderColor: =RGBA(0, 0, 0, 0)
                        DisabledColor: =RGBA(255, 255, 255, 1)
                        DisabledFill: =RGBA(186, 198, 200, 1)
                        Fill: =RGBA(8, 144, 144, 1)
                        Font: =Font.'Segoe UI'
                        FontWeight: =FontWeight.Semibold
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        HoverColor: =RGBA(255, 255, 255, 1)
                        HoverFill: =RGBA(0, 112, 112, 1)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        PressedColor: =RGBA(255, 255, 255, 1)
                        PressedFill: =RGBA(0, 112, 112, 1)
                        RadiusBottomLeft: =10
                        RadiusBottomRight: =10
                        RadiusTopLeft: =10
                        RadiusTopRight: =10
                        FillPortions: =2
                        Height: =56
                        OnSelect: |-
@@SIGNOFF_ONSELECT@@
                        Size: =15
                        Text: ="Save sign-off"
                        Visible: =varReviewing && ctxPage >= CountRows(colPages)
'''



def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: py -3 -I scripts/build_pretrip_screen.py <output folder>')
    with open(ITEMS_JSON, encoding='utf-8') as fh:
        data = json.load(fh)
    text = Builder(data).render()
    # Paging hides cards on other sections, but SubmitForm still validates hidden
    # cards, so a driver-required card only counts while its page is showing. The
    # Submit gate (btnSubmitChecklist) checks every required value across pages.
    text = re.sub(r'(\n *Required: =)(?!false\n|varReviewing\n)([^\n]+)',
                  lambda m: f'{m.group(1)}({m.group(2)}) && Self.Visible', text)
    os.makedirs(sys.argv[1], exist_ok=True)
    path = os.path.join(sys.argv[1], 'scrPreTrip.txt')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(f'wrote {path} ({text.count(chr(10))} lines)')


if __name__ == '__main__':
    main()
