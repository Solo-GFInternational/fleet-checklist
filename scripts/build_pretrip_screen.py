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
    A separate comment card (crd<Card>Cmt) for the <field>Cmt column shows when the "problem"
    answer is ticked and is then required.
  - Photo buttons per item: one / perTyre (Tyre 1..N, N from the Trucks list, 6 if not found)
    / fourSides (Front, Rear, Left, Right) / multi (accident photos).
  - Weekly reviewer-only items (cabin tilting, greasing): only when reviewing; replaced by
    "... conducted on <date> by <name>" when this truck already has a Yes this week (Mon-Sun).
  - Submit button that names the first missing answer, comment, field or photo.

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


def checkbox(name, caption, default, on_check, x, y, visible=None):
    props = [
        ('BorderColor', CLEAR), ('CheckboxBackgroundFill', WHITE), ('CheckboxBorderColor', TEAL),
        ('CheckboxSize', '30'), ('CheckmarkFill', TEAL), ('Color', INK), ('Default', default),
        ('DisabledColor', INK), ('DisplayMode', 'Parent.DisplayMode'), ('Fill', CLEAR),
        ('Font', "Font.'Segoe UI'"), ('FontWeight', 'FontWeight.Semibold'), ('Height', '48'),
        ('HoverColor', INK), ('HoverFill', TINT), ('OnCheck', on_check), ('PressedColor', INK),
        ('PressedFill', TINT), ('Size', '15'), ('Text', fx_str(caption)),
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


def photo_controls(it, suffix, y, answer_box):
    """Photo buttons + status for an item. Returns (controls, list of (condition, message) for Submit)."""
    ptype = photo_type(it)
    out, missing = [], []
    rule = it['photo']
    if rule == 'one':
        item = it['photoSlots'][0]
        taken = photo_taken(ptype, item)
        out.append(secondary_button(
            f'btn{suffix}Photo', f'If({taken}, "Retake photo", "Take photo")',
            photo_onselect(ptype, fx_str(item)), '150', '30', y, '!varReviewing'))
        out.append(status_label(f'lbl{suffix}Photo', taken, '"✓ Photo taken"', '"Photo required"',
                                'Parent.Width - 210', '192', y, '!varReviewing'))
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
        self.missing = []         # Submit gate: (condition, message expr)
        self.weekly = []          # (field, var, yes box, no box, key n, cmt n)

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
        self.cards.append(text.rstrip('\n').split('\n'))

    def add_heading(self, key, title, visible=None):
        k = key[0].upper() + key[1:]
        props = [('BorderColor', LINE), ('DisplayName', fx_str(title)), ('Height', '60')]
        if visible:
            props.append(('Visible', visible))
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
                 ('Height', '60 + (lblTruckNotFound.Height - 40)'), ('Visible', 'IsBlank(varTruckInfo)'),
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
            yes_default = f'ThisItem.{f}.Value = "Yes"'
            no_default = f'ThisItem.{f}.Value = "No"'

        kids = [key_label(n)]
        below = f'DataCardKey{n}.Y + DataCardKey{n}.Height'
        if it['instruction']:
            kids.append(hint_label(f'lbl{sfx}Hint', it['instruction'], f'{below} + 2'))
            below = f'lbl{sfx}Hint.Y + lbl{sfx}Hint.Height'
        box_y = f'{below} + 4'
        kids.append(checkbox(yes_box, 'Yes', yes_default, f'Reset({no_box})', '30', box_y, box_vis))
        kids.append(checkbox(no_box, 'No', no_default, f'Reset({yes_box})', '150', box_y, box_vis))
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
        kids.append(error_label(n, err_y))
        kids.append(star_label(n))
        problem_box = yes_box if it.get('commentOn') == 'Yes' else no_box
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
        ], card_vis)
        self.cards.append(control(card, 'TypedDataCard@1.0.7', props, CARD, variant='ClassicComboBoxEdit',
                                  children=kids))
        if it['required'] and not reviewer:
            self.missing.append((self.wrap(truck_vis, f'!{yes_box}.Value && !{no_box}.Value'),
                                 f'"Answer: " & DataCardKey{n}.Text'))

        cmt_n = None
        if it.get('commentField'):
            cmt_n = self.add_comment(it, sfx, problem_box, dm, truck_vis, reviewer, n)
        self.missing += photo_missing_list
        if reviewer:
            self.weekly.append((f, it.get('commentField'), week_var, yes_box, no_box, n, cmt_n))

    @staticmethod
    def wrap(vis, cond):
        return f'{vis} && {cond}' if vis else cond

    def add_comment(self, it, sfx, problem_box, dm, truck_vis, reviewer, item_n):
        cf = it['commentField']
        n = self.new_n()
        if reviewer:
            vis = f'varReviewing && IsBlank({WEEKLY.get(it["field"], ("varWeek" + sfx,))[0]}) && {problem_box}.Value'
            required = 'false'
        else:
            vis = self.wrap(truck_vis, f'{problem_box}.Value')
            required = f'{problem_box}.Value && !varReviewing'
        hint = 'Describe the damage' if it.get('commentOn') == 'Yes' else 'Say what is wrong'
        value = control(f'DataCardValue{n}', 'Classic/TextInput@2.3.2', [
            ('Mode', 'TextMode.MultiLine'),
            ('BorderColor', 'If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)'), ('Color', INK),
            ('Height', '80'), ('Size', '15'), ('Default', 'Parent.Default'), ('DelayOutput', 'true'),
            ('DisabledBorderColor', CLEAR), ('DisabledColor', 'RGBA(161, 159, 157, 1)'),
            ('DisabledFill', 'RGBA(242, 242, 241, 0)'), ('DisplayMode', 'Parent.DisplayMode'),
            ('Font', "Font.'Segoe UI'"), ('HintText', fx_str(hint)), ('HoverBorderColor', TEAL),
            ('HoverColor', 'RGBA(50, 49, 48, 1)'), ('HoverFill', WHITE), ('MaxLength', 'Parent.MaxLength'),
            ('PaddingLeft', '5'), ('PressedBorderColor', TEAL), ('PressedColor', 'RGBA(50, 49, 48, 1)'),
            ('PressedFill', WHITE), ('RadiusBottomLeft', '8'), ('RadiusBottomRight', '8'),
            ('RadiusTopLeft', '8'), ('RadiusTopRight', '8'), ('Tooltip', 'Parent.DisplayName'),
            ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', f'DataCardKey{n}.Y + DataCardKey{n}.Height + 5'),
        ], KID, metadata='FieldValue')
        kids = [key_label(n), value, error_label(n, f'DataCardValue{n}.Y + DataCardValue{n}.Height'), star_label(n)]
        props = card_frame(self.take_row(), [
            ('DataField', fx_str(cf)), ('Default', f'ThisItem.{cf}'), ('DisplayMode', dm),
            ('DisplayName', f"DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'{cf}')"),
            ('MaxLength', f"DataSourceInfo([@'Fleet Checklist'], DataSourceInfo.MaxLength, '{cf}')"),
            ('Required', required), ('Update', f'If({problem_box}.Value, DataCardValue{n}.Text, "")'),
        ], vis)
        self.cards.append(control(f'crd{sfx}Cmt', 'TypedDataCard@1.0.7', props, CARD,
                                  variant='ClassicTextualEdit', children=kids))
        if not reviewer:
            self.missing.append((self.wrap(truck_vis, f'{problem_box}.Value && IsBlank(DataCardValue{n}.Text)'),
                                 f'"Comment needed: " & DataCardKey{item_n}.Text'))
        return n

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
                 ('Visible', self.wrap(truck_vis, '!varReviewing') if truck_vis else '!varReviewing'),
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
        kids.append(control(f'DataCardValue{n}', 'Classic/DatePicker@2.6.0', [
            ('BorderColor', 'If(IsBlank(Parent.Error), Parent.BorderColor, Color.Red)'), ('Color', INK),
            ('Height', '48'), ('DefaultDate', 'Parent.Default'), ('DisabledBorderColor', CLEAR),
            ('DisabledColor', 'RGBA(161, 159, 157, 1)'), ('DisabledFill', 'RGBA(242, 242, 241, 0)'),
            ('DisplayMode', 'Parent.DisplayMode'), ('EndYear', 'Year(Today())+100'), ('Fill', WHITE),
            ('Font', "Font.'Segoe UI'"), ('IconBackground', TEAL), ('IconFill', WHITE), ('IsEditable', 'true'),
            ('PaddingBottom', '0'), ('PaddingLeft', 'If(Self.DisplayMode = DisplayMode.Edit, 5, 0)'),
            ('Size', '15'), ('StartYear', '1899'), ('Tooltip', 'Parent.DisplayName'),
            ('Width', 'Parent.Width - 60'), ('X', '30'), ('Y', f'{below} + 5'),
        ], KID, metadata='FieldValue'))
        kids.append(error_label(n, f'DataCardValue{n}.Y + DataCardValue{n}.Height'))
        kids.append(star_label(n))
        photo_missing_list = []
        if it['photo'] != 'none':
            pc, miss = photo_controls(it, sfx, f'ErrorMessage{n}.Y + ErrorMessage{n}.Height - 4', None)
            kids += pc
            if it['required']:
                photo_missing_list = [(self.wrap(truck_vis, c), m) for c, m in miss]
        required = self.wrap(truck_vis, '!varReviewing') if it['required'] else 'false'
        props = [('DisplayMode', 'If(varReviewing, DisplayMode.View, DisplayMode.Edit)')] + card_frame(
            self.take_row(), [
                ('DataField', fx_str(f)), ('Default', f'ThisItem.{f}'),
                ('DisplayName', f"DataSourceInfo([@'Fleet Checklist'],DataSourceInfo.DisplayName,'{f}')"),
                ('Required', required), ('Update', f'DataCardValue{n}.SelectedDate'),
            ], truck_vis)
        self.cards.append(control(card, 'TypedDataCard@1.0.7', props, CARD, variant='ClassicDateEdit',
                                  children=kids))
        if it['required']:
            self.missing.append((self.wrap(truck_vis, f'IsBlank(DataCardValue{n}.SelectedDate)'),
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
        self.add_template(T_ODOMETER + '\n'.join(extra) + '\n')
        self.missing.append(('IsBlank(DataCardValue69.Text)', '"Fill in: " & DataCardKey69.Text'))
        self.missing.append((missing, '"Photo needed: odometer"'))

    # -- whole screen
    def build(self):
        sections = {s['key']: s for s in self.data['sections']}
        items = sorted([i for i in self.data['items'] if not i.get('hidden')], key=lambda i: i['order'])
        self.add_truck_note()
        current = None
        for it in items:
            sec = it['section']
            if sec != current:
                current = sec
                if sec != 'header':
                    sec_items = [i for i in items if i['section'] == sec]
                    review_shows = any(i['kind'] != 'photoOnly' for i in sec_items)
                    self.add_heading(sec, sections[sec]['title'], None if review_shows else '!varReviewing')
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
                                           '                  Required: =!varReviewing\n'))
                self.missing.append(('IsBlank(DataCardValue20.Text)', '"Fill in: " & DataCardKey20.Text'))
            elif f == 'field_50':
                self.add_odometer(it)
            elif f == 'NextServiceDue':
                self.add_template(self.renumber(T_NEXTSERVICE, 90))
            elif f == 'field_51':
                self.add_template(T_REMARKS)
            elif it['kind'] == 'yesno':
                self.add_yesno(it)
            elif it['kind'] == 'date':
                self.add_date(it)
            elif it['kind'] == 'photoOnly':
                self.add_photo_only(it)
            else:
                raise SystemExit(f'No card builder for {f} ({it["kind"]})')
        self.add_template(T_SIGNOFF)

    def on_visible(self):
        lines = [
            "Set(varTruckInfo, LookUp('GF Fleet Trucks', Title = If(varReviewing, varCheck.field_1, varTruck) && ActiveYN = true));",
            f'Set(varTyreCount, Min(Coalesce(varTruckInfo.NoOfTyres, 6), {MAX_TYRES}));',
        ]
        if self.weekly:
            sets = []
            for f, _cf, var, *_ in self.weekly:
                sets.append(
                    f"        Set({var}, First(Sort(Filter('Fleet Checklist', field_1 = varCheck.field_1 && "
                    f'Created >= wkStart && Created < wkEnd && {f}.Value = "Yes"), Created, SortOrder.Descending)))')
            blanks = [f'Set({w[2]}, Blank())' for w in self.weekly]
            lines += [
                'If(varReviewing,',
                '    With({wkDay: Date(Year(varCheck.Created), Month(varCheck.Created), Day(varCheck.Created))},',
                '    With({wkStart: DateAdd(wkDay, 1 - Weekday(wkDay, StartOfWeek.Monday), TimeUnit.Days),',
                '          wkEnd: DateAdd(wkDay, 8 - Weekday(wkDay, StartOfWeek.Monday), TimeUnit.Days)},',
                ';\n'.join(sets) + ')),',
                '    ' + ';\n    '.join(blanks) + ')',
            ]
        return '\n'.join(lines)

    def submit_text(self):
        parts = []
        for cond, msg in self.missing:
            parts.append(f'    {cond},\n        {msg},')
        return 'If(\n' + '\n'.join(parts) + '\n    "Submit")'

    def signoff_onselect(self):
        checks, patches = [], []
        for f, cf, var, yes, no, key_n, cmt_n in self.weekly:
            checks.append(f'    IsBlank({var}) && !{yes}.Value && !{no}.Value,\n'
                          f'    Notify("Answer " & DataCardKey{key_n}.Text & " first.", NotificationType.Warning),')
            rec = f'{f}: {{Value: If({yes}.Value, "Yes", "No")}}'
            if cmt_n:
                checks.append(f'    IsBlank({var}) && {no}.Value && IsBlank(DataCardValue{cmt_n}.Text),\n'
                              f'    Notify("Add a comment for " & DataCardKey{key_n}.Text & ".", NotificationType.Warning),')
                rec += f', {cf}: If({no}.Value, DataCardValue{cmt_n}.Text, "")'
            patches.append(f"        If(IsBlank({var}), Patch('Fleet Checklist', LookUp('Fleet Checklist', ID = varCheck.ID), {{{rec}}}));")
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
        out += T_CHROME.rstrip('\n').split('\n')
        for c in self.cards:
            out += c
        footer = T_FOOTER
        footer = footer.replace('@@SUBMIT_TEXT@@', '\n'.join(
            '                    ' + ln if ln else '' for ln in ('=' + self.submit_text()).split('\n')))
        footer = footer.replace('@@SIGNOFF_ONSELECT@@', '\n'.join(
            '                    ' + ln if ln else '' for ln in ('=' + self.signoff_onselect()).split('\n')))
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
                          ="Truck: " & If(varReviewing, varCheck.'Truck No', Coalesce(varTruck, "not selected"))
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
            Height: =Parent.Height - 90 - 88
            Item: =varCheck
            NumberOfColumns: =1
            OnFailure: |-
              =Notify("Not saved: " & frmPreTrip.Error, NotificationType.Error, 0)
            OnSuccess: |-
              =If(varReviewing,
                  Notify("Sign-off saved", NotificationType.Success);
                  Navigate(scrReview),
                  With({recId: frmPreTrip.LastSubmit.ID},
                      IfError(
                          ForAll(colPhotos,
                              'SaveFleetPhoto'.Run(
                                  Coalesce(varTruck, "Unknown"),
                                  Coalesce(ThisRecord.Type, "Photo"),
                                  Coalesce(ThisRecord.Item, ThisRecord.Type, "Photo"),
                                  recId,
                                  "Fleet Checklist",
                                  {file: {name: "photo.jpg", contentBytes: ThisRecord.Img}}));
                          Notify("Checklist saved", NotificationType.Success),
                          Notify("Checklist saved, but the photos did not upload: " & FirstError.Message, NotificationType.Warning, 0)));
                  Clear(colPhotos);
                  ResetForm(frmPreTrip);
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
                  Default: =If(varReviewing, ThisItem.'Truck No', varTruck)
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
                    =If(varReviewing, ThisItem.'Driver Name', User().FullName)
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
                  Default: =ThisItem.Site
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
                  Default: =ThisItem.Remarks
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
                  Default: =ThisItem.'Truck odometer reading before delivery (km)'
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
                  Default: =ThisItem.'Approval For Delivery'
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
                  Default: =ThisItem.'Send For Repairs'
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
                  Default: =If(varReviewing, Coalesce(ThisItem.'Date Of Declaration', Today()), Blank())
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
                  Default: =If(varReviewing, Coalesce(ThisItem.'Manager Name', User().FullName), Blank())
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
            Height: =88
            LayoutAlignItems: =LayoutAlignItems.Center
            LayoutDirection: =LayoutDirection.Horizontal
            LayoutGap: =12
            PaddingBottom: =16
            PaddingLeft: =16
            PaddingRight: =16
            PaddingTop: =16
            Width: =Parent.Width
            X: =0
            Y: =Parent.Height - 88
          Children:
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
                  FillPortions: =1
                  Font: =Font.'Segoe UI'
                  FontWeight: =FontWeight.Semibold
                  Height: =56
                  HoverBorderColor: =RGBA(8, 144, 144, 1)
                  HoverColor: =RGBA(0, 112, 112, 1)
                  HoverFill: =RGBA(226, 243, 242, 1)
                  OnSelect: |-
                    =Set(varPhotoType, Blank());
                    Set(varPhotoItem, Blank());
                    Navigate(scrPhotos)
                  PressedBorderColor: =RGBA(0, 112, 112, 1)
                  PressedColor: =RGBA(0, 112, 112, 1)
                  PressedFill: =RGBA(226, 243, 242, 1)
                  RadiusBottomLeft: =10
                  RadiusBottomRight: =10
                  RadiusTopLeft: =10
                  RadiusTopRight: =10
                  Size: =15
                  Text: ="Photos (" & CountRows(colPhotos) & ")"
                  Visible: =!varReviewing
            - btnSubmitChecklist:
                Control: Classic/Button@2.2.0
                Properties:
                  BorderColor: =RGBA(0, 0, 0, 0)
                  BorderStyle: =BorderStyle.None
                  Color: =RGBA(255, 255, 255, 1)
                  DisabledBorderColor: =RGBA(0, 0, 0, 0)
                  DisabledColor: =RGBA(255, 255, 255, 1)
                  DisabledFill: =RGBA(186, 198, 200, 1)
                  DisplayMode: =If(Self.Text = "Submit", DisplayMode.Edit, DisplayMode.Disabled)
                  Fill: =RGBA(8, 144, 144, 1)
                  FillPortions: =1
                  Font: =Font.'Segoe UI'
                  FontWeight: =FontWeight.Semibold
                  Height: =56
                  HoverBorderColor: =RGBA(0, 0, 0, 0)
                  HoverColor: =RGBA(255, 255, 255, 1)
                  HoverFill: =RGBA(0, 112, 112, 1)
                  OnSelect: =SubmitForm(frmPreTrip)
                  PressedBorderColor: =RGBA(0, 0, 0, 0)
                  PressedColor: =RGBA(255, 255, 255, 1)
                  PressedFill: =RGBA(0, 112, 112, 1)
                  RadiusBottomLeft: =10
                  RadiusBottomRight: =10
                  RadiusTopLeft: =10
                  RadiusTopRight: =10
                  Size: =If(Self.Text = "Submit", 15, 13)
                  Text: |-
@@SUBMIT_TEXT@@
                  Visible: =!varReviewing
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
                  FillPortions: =1
                  Font: =Font.'Segoe UI'
                  FontWeight: =FontWeight.Semibold
                  Height: =56
                  HoverBorderColor: =RGBA(0, 0, 0, 0)
                  HoverColor: =RGBA(255, 255, 255, 1)
                  HoverFill: =RGBA(0, 112, 112, 1)
                  OnSelect: |-
@@SIGNOFF_ONSELECT@@
                  PressedBorderColor: =RGBA(0, 0, 0, 0)
                  PressedColor: =RGBA(255, 255, 255, 1)
                  PressedFill: =RGBA(0, 112, 112, 1)
                  RadiusBottomLeft: =10
                  RadiusBottomRight: =10
                  RadiusTopLeft: =10
                  RadiusTopRight: =10
                  Size: =15
                  Text: ="Save sign-off"
                  Visible: =varReviewing
'''



def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: py -3 -I scripts/build_pretrip_screen.py <output folder>')
    with open(ITEMS_JSON, encoding='utf-8') as fh:
        data = json.load(fh)
    text = Builder(data).render()
    os.makedirs(sys.argv[1], exist_ok=True)
    path = os.path.join(sys.argv[1], 'scrPreTrip.txt')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(f'wrote {path} ({text.count(chr(10))} lines)')


if __name__ == '__main__':
    main()
