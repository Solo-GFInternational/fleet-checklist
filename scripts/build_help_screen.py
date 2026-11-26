"""Builds screens/scrHelp.txt (the in-app user manual) and the screenshot list from
scripts/manual_content.json.

Usage:  py -3 -I scripts/build_help_screen.py screens files

manual_content.json is the single source for the manual: the topics (chapters), which roles see
each topic and in what order, the wording, and the screenshots. Edit the JSON, run this script,
paste the screen into Power Apps.

What it builds:
  - screens/scrHelp.txt: GF header (back icon, logo, "How to use the app", "<role> guide"),
    brand stripe, a topic list showing only the topics for the signed-in role (varRole), and one
    scrolling page per topic (ctxTopic). Footer on a topic page: "All topics" and "Next: <topic>"
    (the next topic in that role's order). Each topic has its own scroll container, so it opens
    at the top.
  - Block kinds in a topic: "h" sub-heading, "p" text, "step" numbered step, "tip" (teal box),
    "warn" (yellow box), "shot" (phone screenshot + caption).
  - Screenshots: shot S07 is the media image 'help_s07'. It is only referenced when
    files/manual-screenshots/app/help_s07.jpg exists (made by scripts/prepare_manual_screenshots.ps1
    from the phone screenshot files/manual-screenshots/S07.png), so the screen pastes without errors
    before every screenshot is taken. A missing one shows a "Screenshot coming soon" box.
    After adding screenshots: run the .ps1, run this script, upload the new help_sNN.jpg files to
    the app's Media, paste the screen.
  - files/Manual - screenshot list.md: every shot with the account to use, how to get there, what
    must be on screen, the topics that use it and whether it is done.

Stdlib only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_JSON = os.path.join(HERE, 'manual_content.json')

TEAL = 'RGBA(8, 144, 144, 1)'
DARK_TEAL = 'RGBA(0, 112, 112, 1)'
TINT = 'RGBA(226, 243, 242, 1)'
CYAN = 'RGBA(0, 184, 216, 1)'
YELLOW = 'RGBA(248, 208, 0, 1)'
LIME = 'RGBA(160, 200, 80, 1)'
INK = 'RGBA(31, 41, 51, 1)'
MUTED = 'RGBA(96, 108, 118, 1)'
LINE = 'RGBA(208, 216, 218, 1)'
BG = 'RGBA(243, 246, 246, 1)'
WHITE = 'RGBA(255, 255, 255, 1)'
CLEAR = 'RGBA(0, 0, 0, 0)'
YELLOW_TINT = 'RGBA(254, 246, 204, 1)'
FONT = "Font.'Segoe UI'"
ROLES = ['Driver', 'Reviewer', 'Admin', 'None']


def fx_str(s):
    return '"' + s.replace('"', '""') + '"'


def prop_lines(name, formula, indent):
    pad = ' ' * indent
    if '\n' in formula or ': ' in formula or formula.startswith(('"', "'")) and len(formula) > 60:
        body = ('=' + formula).split('\n')
        return [f'{pad}{name}: |-'] + [f'{pad}  {ln}' if ln else '' for ln in body]
    return [f'{pad}{name}: ={formula}']


def control(name, ctype, props, indent, variant=None, children=None):
    pad = ' ' * indent
    out = [f'{pad}- {name}:', f'{pad}    Control: {ctype}']
    if variant:
        out.append(f'{pad}    Variant: {variant}')
    out.append(f'{pad}    Properties:')
    for k, v in props:
        out += prop_lines(k, v, indent + 6)
    if children:
        out.append(f'{pad}    Children:')
        for c in children:
            out += c
    return out


def radius(r):
    return [(f'Radius{c}', str(r)) for c in ('BottomLeft', 'BottomRight', 'TopLeft', 'TopRight')]


def label(name, text, indent, size=14, color=INK, weight='FontWeight.Normal', fill=None, pad=0,
          visible=None, extra=None):
    props = [('AutoHeight', 'true'), ('BorderStyle', 'BorderStyle.None'), ('Color', color)]
    if fill:
        props.append(('Fill', fill))
    props += [('Font', FONT), ('FontWeight', weight), ('Height', str(24 + 2 * pad)),
              ('PaddingBottom', str(pad)), ('PaddingLeft', str(pad)), ('PaddingRight', str(pad)),
              ('PaddingTop', str(pad)), ('Size', str(size)), ('Text', text)]
    if visible:
        props.append(('Visible', visible))
    props += (extra or []) + [('Wrap', 'true')]
    return control(name, 'Label@2.5.1', props, indent)


def button(name, text, onselect, indent, primary, visible=None, extra=None):
    if primary:
        props = [('BorderColor', CLEAR), ('BorderStyle', 'BorderStyle.None'), ('Color', WHITE),
                 ('Fill', TEAL), ('HoverBorderColor', CLEAR), ('HoverColor', WHITE),
                 ('HoverFill', DARK_TEAL), ('PressedBorderColor', CLEAR), ('PressedColor', WHITE),
                 ('PressedFill', DARK_TEAL)]
    else:
        props = [('BorderColor', TEAL), ('BorderStyle', 'BorderStyle.Solid'), ('BorderThickness', '2'),
                 ('Color', DARK_TEAL), ('Fill', WHITE), ('HoverBorderColor', TEAL),
                 ('HoverColor', DARK_TEAL), ('HoverFill', TINT), ('PressedBorderColor', DARK_TEAL),
                 ('PressedColor', DARK_TEAL), ('PressedFill', TINT)]
    props += [('Font', FONT), ('FontWeight', 'FontWeight.Semibold'), ('Height', '56'),
              ('OnSelect', onselect)] + radius(10) + [('Size', '15'), ('Text', text)]
    if visible:
        props.append(('Visible', visible))
    props += extra or []
    return control(name, 'Classic/Button@2.2.0', props, indent)


def role_cond(roles):
    roles = [r for r in roles if r in ROLES]
    if set(roles) >= set(ROLES):
        return 'true'
    return 'varRole in [' + ', '.join(fx_str(r) for r in roles) + ']'


def topic_roles(data, key):
    return [r for r in ROLES if key in data['roleOrder'].get(r, [])]


# ------------------------------------------------------------------------------------------ build

def build(data, shots_dir):
    topics = {t['key']: t for t in data['topics']}
    shots = {s['id']: s for s in data['shots']}
    for r, keys in data['roleOrder'].items():
        assert r in ROLES, r
        for k in keys:
            assert k in topics, (r, k)
    have_img = {sid for sid in shots
                if os.path.exists(os.path.join(shots_dir, 'app', f'help_{sid.lower()}.jpg'))}
    used = {}

    # ---- topic list (menu)
    M = 18   # indent of a child of conHelpMenu
    menu_kids = [label('lblHelpIntro',
                       'Switch(varRole, ' + ', '.join(
                           f'{fx_str(r)}, {fx_str(data["intro"][r])}' for r in ROLES if r in data['intro'])
                       + f', {fx_str(data["intro"]["None"])})',
                       M, size=14, color=INK)]
    menu_kids.append(label('lblHelpTopicsHeading', fx_str('Pick a topic'), M, size=15, color=DARK_TEAL,
                           weight='FontWeight.Semibold', extra=[('PaddingTop', '8')]))
    for t in data['topics']:
        roles = topic_roles(data, t['key'])
        if not roles:
            continue
        num = 'Switch(varRole, ' + ', '.join(
            f'{fx_str(r)}, {fx_str(str(data["roleOrder"][r].index(t["key"]) + 1) + ".  ")}'
            for r in roles) + ', "")'
        menu_kids.append(button(f'btnHelpTopic{t["key"]}', f'{num} & {fx_str(t["title"])}',
                                f'UpdateContext({{ctxTopic: {fx_str(t["key"])}}})', M, primary=False,
                                visible=role_cond(roles),
                                extra=[('Align', 'Align.Left'), ('PaddingLeft', '16')]))
    menu = control('conHelpMenu', 'GroupContainer@1.5.0', [
        ('Fill', BG), ('FillPortions', '1'), ('LayoutAlignItems', 'LayoutAlignItems.Stretch'),
        ('LayoutDirection', 'LayoutDirection.Vertical'), ('LayoutGap', '12'), ('LayoutMinHeight', '16'),
        ('LayoutMinWidth', '16'), ('LayoutOverflowY', 'LayoutOverflow.Scroll'), ('PaddingBottom', '24'),
        ('PaddingLeft', '16'), ('PaddingRight', '16'), ('PaddingTop', '16'),
        ('Visible', 'IsBlank(ctxTopic)'),
    ], 12, variant='AutoLayout', children=menu_kids)

    # ---- one page per topic
    pages = []
    for t in data['topics']:
        k = t['key']
        if not topic_roles(data, k):
            continue
        kids = [label(f'lblHelp{k}Title', fx_str(t['title']), M, size=19, color=DARK_TEAL,
                      weight='FontWeight.Bold')]
        if t.get('summary'):
            kids.append(label(f'lblHelp{k}Summary', fx_str(t['summary']), M, size=14, color=MUTED))
        step = 0
        for i, b in enumerate(t['blocks'], 1):
            kind = b[0]
            n = f'{k}B{i}'
            if kind != 'step':
                step = 0 if kind == 'h' else step
            if kind == 'h':
                kids.append(label(f'lblHelp{n}', fx_str(b[1]), M, size=16, color=DARK_TEAL,
                                  weight='FontWeight.Semibold', extra=[('PaddingTop', '10')]))
            elif kind == 'p':
                kids.append(label(f'lblHelp{n}', fx_str(b[1]), M))
            elif kind == 'step':
                step += 1
                kids.append(label(f'lblHelp{n}', fx_str(f'{step}.  {b[1]}'), M))
            elif kind == 'tip':
                kids.append(label(f'lblHelp{n}', fx_str('Tip:  ' + b[1]), M, size=14, color=INK,
                                  fill=TINT, pad=12))
            elif kind == 'warn':
                kids.append(label(f'lblHelp{n}', fx_str('Important:  ' + b[1]), M, size=14, color=INK,
                                  fill=YELLOW_TINT, pad=12, weight='FontWeight.Semibold'))
            elif kind == 'shot':
                sid = b[1]
                assert sid in shots, (k, sid)
                used.setdefault(sid, []).append(t['title'])
                caption = b[2] if len(b) > 2 else shots[sid]['title']
                if sid in have_img:
                    kids.append(control(f'imgHelp{n}', 'Image@2.2.3', [
                        ('AccessibleLabel', fx_str(caption)), ('AlignInContainer', 'AlignInContainer.Center'),
                        ('BorderColor', LINE), ('BorderThickness', '1'),
                        ('Height', 'Self.Width * 2.17'), ('Image', f"'help_{sid.lower()}'"),
                        ('ImagePosition', 'ImagePosition.Fit'),
                    ] + radius(12) + [('Width', 'Min(Parent.Width - 72, 300)')], M))
                else:
                    kids.append(label(f'lblHelp{n}Missing',
                                      fx_str(f'Screenshot {sid} coming soon: {shots[sid]["title"]}'), M,
                                      size=13, color=MUTED, fill=WHITE, pad=16,
                                      extra=[('Align', 'Align.Center'), ('BorderColor', LINE),
                                             ('BorderStyle', 'BorderStyle.Dashed'), ('BorderThickness', '2'),
                                             ('AlignInContainer', 'AlignInContainer.Center'),
                                             ('Width', 'Min(Parent.Width - 72, 300)')]))
                kids.append(label(f'lblHelp{n}Caption', fx_str(caption), M, size=12, color=MUTED,
                                  extra=[('Align', 'Align.Center')]))
            else:
                raise ValueError((k, b))
        pages.append(control(f'conHelpTopic{k}', 'GroupContainer@1.5.0', [
            ('Fill', BG), ('FillPortions', '1'), ('LayoutAlignItems', 'LayoutAlignItems.Stretch'),
            ('LayoutDirection', 'LayoutDirection.Vertical'), ('LayoutGap', '12'),
            ('LayoutMinHeight', '16'), ('LayoutMinWidth', '16'),
            ('LayoutOverflowY', 'LayoutOverflow.Scroll'), ('PaddingBottom', '24'), ('PaddingLeft', '16'),
            ('PaddingRight', '16'), ('PaddingTop', '16'), ('Visible', f'ctxTopic = {fx_str(k)}'),
        ], 12, variant='AutoLayout', children=kids))

    # ---- footer: All topics / Next
    def next_map():
        rows = []
        for r in ROLES:
            order = data['roleOrder'].get(r, [])
            for a, b in zip(order, order[1:]):
                rows.append((r, a, b))
        return rows
    nm = next_map()
    nxt = ('Switch(varRole & "|" & ctxTopic, '
           + ', '.join(f'{fx_str(r + "|" + a)}, {fx_str(b)}' for r, a, b in nm) + ', "")')
    nxt_title = ('Switch(varRole & "|" & ctxTopic, '
                 + ', '.join(f'{fx_str(r + "|" + a)}, {fx_str(topics[b]["title"])}' for r, a, b in nm)
                 + ', "")')
    footer = control('conHelpFooter', 'GroupContainer@1.5.0', [
        ('DropShadow', 'DropShadow.Light'), ('Fill', WHITE), ('FillPortions', '0'),
        ('Height', 'If(IsBlank(lblHelpNextKey.Text), 88, 152)'),
        ('LayoutAlignItems', 'LayoutAlignItems.Stretch'), ('LayoutDirection', 'LayoutDirection.Vertical'),
        ('LayoutGap', '8'), ('LayoutMinHeight', '16'), ('LayoutMinWidth', '16'), ('PaddingBottom', '16'),
        ('PaddingLeft', '16'), ('PaddingRight', '16'), ('PaddingTop', '16'), ('Visible', '!IsBlank(ctxTopic)'),
    ], 12, variant='AutoLayout', children=[
        button('btnHelpNext', f'"Next:  " & {nxt_title}',
               'UpdateContext({ctxTopic: lblHelpNextKey.Text})', 18, primary=True,
               visible='!IsBlank(lblHelpNextKey.Text)'),
        button('btnHelpAllTopics', '"All topics"', 'UpdateContext({ctxTopic: Blank()})', 18, primary=False),
        control('lblHelpNextKey', 'Label@2.5.1', [('Height', '0'), ('Text', nxt), ('Visible', 'false')], 18),
    ])

    header = HEADER.strip('\n').split('\n')
    stripe = STRIPE.strip('\n').split('\n')
    lines = ['Screens:', '  scrHelp:', '    Properties:', f'      Fill: ={BG}',
             f'      LoadingSpinnerColor: ={TEAL}', '      OnVisible: |-', '        =UpdateContext({ctxTopic: Blank()})',
             '    Children:']
    body = [header, stripe, menu] + pages + [footer]
    lines += control('conHelp', 'GroupContainer@1.5.0', [
        ('Fill', BG), ('Height', 'Parent.Height'), ('LayoutAlignItems', 'LayoutAlignItems.Stretch'),
        ('LayoutDirection', 'LayoutDirection.Vertical'), ('LayoutGap', '0'), ('Width', 'Parent.Width'),
    ], 6, variant='AutoLayout', children=body)
    return '\n'.join(lines) + '\n', used, have_img


def shot_list(data, used, have_img):
    out = ['# Manual – screenshot list', '',
           'Generated by `scripts/build_help_screen.py` from `scripts/manual_content.json`. '
           'Don\'t edit by hand.', '',
           '## How to take and add the screenshots', '',
           '1. Use a phone (portrait). Turn on signal, set the phone to light mode, and use a **test** '
           'truck and **test** data only (no real customer names or driver details you don\'t want '
           'staff to see).',
           '2. Sign in with an account that has the role in the "Account" column. Get the screen into '
           'the state described, then take a screenshot (iPhone: side button + volume up; '
           'Android: power + volume down).',
           '3. Copy each screenshot to `files/manual-screenshots/` named exactly as the ID, '
           'e.g. `S07.png` (or `.jpg`).',
           '4. Run `powershell -ExecutionPolicy Bypass -File scripts/prepare_manual_screenshots.ps1`. '
           'It makes small copies `files/manual-screenshots/app/help_s07.jpg` (about 450 px wide, '
           'so the app stays small).',
           '5. Run `py -3 -I scripts/build_help_screen.py screens files`.',
           '6. In Power Apps Studio: **Media → Upload** the new `help_sNN.jpg` files (the media name must '
           'stay `help_s07` etc.), then paste the new `screens/scrHelp.txt` and Publish.',
           '',
           f'Done: {len(have_img & set(used))} of {len(used)}.', '',
           '| ID | Done | Account | Screenshot | How to get there | Must be on screen | Used in |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    for s in data['shots']:
        if s['id'] not in used:
            continue
        out.append('| {id} | {done} | {acc} | {t} | {how} | {show} | {uses} |'.format(
            id=s['id'], done='✓' if s['id'] in have_img else '', acc=s['account'], t=s['title'],
            how=s['how'].replace('|', '/'), show=s['show'].replace('|', '/'),
            uses='; '.join(dict.fromkeys(used[s['id']]))))
    unused = [s['id'] for s in data['shots'] if s['id'] not in used]
    if unused:
        out += ['', 'Not used by any topic: ' + ', '.join(unused)]
    return '\n'.join(out) + '\n'


HEADER = f'''
            - conHelpHeader:
                Control: GroupContainer@1.5.0
                Variant: AutoLayout
                Properties:
                  Fill: ={WHITE}
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
                  - icoHelpBack:
                      Control: Classic/Icon@2.5.0
                      Properties:
                        AccessibleLabel: ="Go back"
                        Color: ={DARK_TEAL}
                        Height: =40
                        Icon: =Icon.ChevronLeft
                        OnSelect: |-
                          =If(IsBlank(ctxTopic), Navigate(scrHome), UpdateContext({{ctxTopic: Blank()}}))
                        PaddingBottom: =8
                        PaddingLeft: =8
                        PaddingRight: =8
                        PaddingTop: =8
                        Tooltip: ="Go back"
                        Width: =40
                  - imgHelpLogo:
                      Control: Image@2.2.3
                      Properties:
                        AccessibleLabel: ="GF logo"
                        Height: =48
                        Image: ='gf-logo'
                        ImagePosition: =ImagePosition.Fit
                        Width: =48
                  - conHelpTitles:
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
                        - lblHelpTitle:
                            Control: Label@2.5.1
                            Properties:
                              BorderStyle: =BorderStyle.None
                              Color: ={DARK_TEAL}
                              Font: ={FONT}
                              FontWeight: =FontWeight.Bold
                              Height: =28
                              PaddingLeft: =0
                              Size: =18
                              Text: ="How to use the app"
                        - lblHelpSubtitle:
                            Control: Label@2.5.1
                            Properties:
                              BorderStyle: =BorderStyle.None
                              Color: ={MUTED}
                              Font: ={FONT}
                              Height: =22
                              PaddingLeft: =0
                              Size: =12
                              Text: =If(varRole in ["Driver", "Reviewer", "Admin"], varRole & " guide", "Getting started")
'''

STRIPE = f'''
            - conHelpStripe:
                Control: GroupContainer@1.5.0
                Variant: AutoLayout
                Properties:
                  Fill: ={WHITE}
                  FillPortions: =0
                  Height: =6
                  LayoutAlignItems: =LayoutAlignItems.Stretch
                  LayoutDirection: =LayoutDirection.Horizontal
                  LayoutGap: =0
                  LayoutMinHeight: =6
                  LayoutMinWidth: =16
                Children:
                  - recHelpStripe1:
                      Control: Rectangle@2.3.0
                      Properties:
                        BorderColor: ={CLEAR}
                        Fill: ={TEAL}
                        FillPortions: =1
                        Height: =6
                  - recHelpStripe2:
                      Control: Rectangle@2.3.0
                      Properties:
                        BorderColor: ={CLEAR}
                        Fill: ={CYAN}
                        FillPortions: =1
                        Height: =6
                  - recHelpStripe3:
                      Control: Rectangle@2.3.0
                      Properties:
                        BorderColor: ={CLEAR}
                        Fill: ={YELLOW}
                        FillPortions: =1
                        Height: =6
                  - recHelpStripe4:
                      Control: Rectangle@2.3.0
                      Properties:
                        BorderColor: ={CLEAR}
                        Fill: ={LIME}
                        FillPortions: =1
                        Height: =6
'''


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    screens_dir, files_dir = sys.argv[1], sys.argv[2]
    data = json.load(open(CONTENT_JSON, encoding='utf-8'))
    shots_dir = os.path.join(files_dir, 'manual-screenshots')
    screen, used, have_img = build(data, shots_dir)
    p = os.path.join(screens_dir, 'scrHelp.txt')
    with open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(screen)
    print(f'wrote {p} ({screen.count(chr(10))} lines)')
    q = os.path.join(files_dir, 'Manual - screenshot list.md')
    with open(q, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(shot_list(data, used, have_img))
    print(f'wrote {q} ({len(have_img & set(used))} of {len(used)} screenshots in place)')


if __name__ == '__main__':
    main()
