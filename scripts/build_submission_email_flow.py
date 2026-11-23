"""
Builds an import package for the updated "Run Sheet - Submission email" flow, so the changes in
the setup guide's step 2.2 don't have to be made by hand.

It reads the package you exported from Power Automate (My flows -> ... -> Export -> Package (.zip))
and writes a new package with the changes built in:
  - the fixed 1-minute Delay becomes a "Wait for the run" loop that checks every few minutes until
    every stop (NoofStops) and every invoice photo (NoofInvoicePhotos, by RunKey) has arrived;
  - an invoice PDF (one page per photo, newest copy of each) is built as an HTML file in the PDF
    folder and converted to PDF with "Send an HTTP request to SharePoint" (no OneDrive connection
    needed), saved in the photo library, attached to your email when it's small enough and linked;
  - "Update item" moves out of the per-stop For each, so the run is marked as emailed once;
  - optional: an email to you if the flow fails.
Your trigger, trigger conditions, stops table, ⚠ flags and email layout are kept as they are.

Usage (from the repo folder):
    py -3 -I scripts/build_submission_email_flow.py <output folder> <exported package .zip>
e.g.
    py -3 -I scripts/build_submission_email_flow.py files "files/Solo_20261123212614.zip"

Then in Power Automate: My flows -> Import -> Import Package (Legacy) -> upload the new .zip ->
for the flow choose "Create as new", for each connection (SharePoint, Office 365 Outlook) pick yours
-> Import. Turn the new flow on and the old one off. Details: files/Setup guide - Nov 2026 release.md.

The exported package and the new one contain your site address, list IDs and email address:
keep both out of git (files/.gitignore ignores *.zip).
"""
import io
import json
import os
import sys
import zipfile
from urllib.parse import quote

# =====================================================================================
# INPUTS: check these before running
# =====================================================================================
# 1. Name of the new flow (the import creates it next to your existing one).
FLOW_NAME = 'Run Sheet - Submission email v2'

# 2. The photo library's name exactly as SharePoint shows it (the list title).
PHOTOS_LIBRARY = 'Fleet Photos'

# 3. Folder for the saved PDFs, as a path inside the site. The first part is the library's
#    URL name, which can differ from its title: open the library and look at the address bar,
#    e.g. ".../sites/<site>/Fleet%20Photos/Forms/AllItems.aspx" -> "/Fleet Photos". The folder
#    itself must exist (setup guide step 1.6). The temporary HTML file is made here too, converted
#    to PDF, then deleted.
PDF_FOLDER = '/Fleet Photos/Run sheet PDFs'

# 4. Who is told if the flow fails. Leave '' to leave the failure email out.
FAILURE_EMAIL = 'Solomone.Tuilagivou@gfinternational.com.au'

# 5. Timing and size (defaults are fine).
WAIT_MINUTES = 2        # minutes between checks for stops and photos
MAX_CHECKS = 30         # give up waiting after this many checks (30 x 2 min = about an hour)
ATTACH_LIMIT_MB = 19    # attach the PDF only below this size; bigger ones are linked
# =====================================================================================

SP_API = '/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
O365_API = '/providers/Microsoft.PowerApps/apis/shared_office365'
AUTH = "@parameters('$authentication')"


def sp(op, params, after):
    return {'type': 'OpenApiConnection', 'runAfter': after,
            'inputs': {'parameters': params, 'authentication': AUTH,
                       'host': {'apiId': SP_API, 'connectionName': 'shared_sharepointonline', 'operationId': op}}}


def sp_http(site, uri, after, json_reply=True):
    """SharePoint "Send an HTTP request to SharePoint" (GET)."""
    params = {'dataset': site, 'parameters/method': 'GET', 'parameters/uri': uri}
    if json_reply:
        params['parameters/headers'] = {'Accept': 'application/json'}
    return sp('HttpRequest', params, after)


def ok(name):
    return {name: ['Succeeded']}


def init_var(name, typ, value, after):
    return {'type': 'InitializeVariable', 'runAfter': after,
            'inputs': {'variables': [{'name': name, 'type': typ, 'value': value}]}}


def fail(msg):
    raise SystemExit('STOPPED: ' + msg)


def main():
    if len(sys.argv) != 3:
        fail('usage: py -3 -I scripts/build_submission_email_flow.py <output folder> <exported package .zip>')
    out_dir, src = sys.argv[1], sys.argv[2]
    zin = zipfile.ZipFile(src)
    files = {n: zin.read(n) for n in zin.namelist()}
    defs = [n for n in files if n.endswith('/definition.json')]
    if len(defs) != 1:
        fail('the package must contain exactly one flow')
    flow_dir = defs[0].rsplit('/', 1)[0]
    load = lambda n: json.loads(files[n].decode('utf-8-sig'))
    flow = load(defs[0])
    manifest = load('manifest.json')
    apis = load(flow_dir + '/apisMap.json')
    conns = load(flow_dir + '/connectionsMap.json')

    props = flow['properties']
    df = props['definition']
    acts = df['actions']
    trig = next(iter(df['triggers'].values()))

    # ---- check this is the flow we expect
    for name in ('Get_items', 'Condition'):
        if name not in acts:
            fail(f'action "{name}" not found: is this the Run Sheet - Submission email export?')
    cond = acts['Condition']['actions']
    for name in ('Create_HTML_table', 'Send_an_email_(V2)'):
        if name not in cond:
            fail(f'action "{name}" not found in the Condition')
    update = None
    for name, a in list(cond.items()):
        if a['type'] == 'Foreach' and 'Update_item' in a.get('actions', {}):
            update = a['actions']['Update_item']
            del cond[name]
    if update is None and 'Update_item' in cond:
        update = cond.pop('Update_item')
    if update is None:
        fail('"Update item" (marks the run as emailed) not found')
    if 'Wait_for_the_run' in acts:
        fail('this flow already has the changes (Wait_for_the_run exists)')
    site = trig['inputs']['parameters']['dataset']
    if not site.startswith('https://'):
        fail('could not read the site address from the trigger')

    run_key = "coalesce(triggerOutputs()?['body/RunKey'], 'none')"
    run_id = "triggerOutputs()?['body/ID']"
    limit_chars = int(ATTACH_LIMIT_MB * 1024 * 1024 * 4 / 3)  # base64 length of the PDF
    small = f"less(length(string(body('Convert_to_PDF')?['$content'])), {limit_chars})"

    # ---- top level: variables, wait loop, then the existing Get items + Condition
    acts.pop('Delay', None)
    top = {}
    prev = {}
    for name, typ, val in [('stopsFound', 'integer', 0), ('photosFound', 'integer', 0), ('tries', 'integer', 0),
                           ('seen', 'array', []), ('keep', 'array', []),
                           ('html', 'string', '<html><body style="font-family:Arial,sans-serif">')]:
        key = f'Init_{name}'
        top[key] = init_var(name, typ, val, prev)
        prev = ok(key)

    loop = {
        'Wait_a_minute': {'type': 'Wait', 'runAfter': {},
                          'inputs': {'interval': {'count': WAIT_MINUTES, 'unit': 'Minute'}}},
        'Check_stops': sp('GetItems', {'dataset': site, 'table': acts['Get_items']['inputs']['parameters']['table'],
                                       '$filter': f"RunSheetID eq @{{{run_id}}}", '$top': 500}, ok('Wait_a_minute')),
        'Check_photos': sp('GetFileItems', {'dataset': site, 'table': PHOTOS_LIBRARY,
                                            '$filter': f"RunKey eq '@{{{run_key}}}'", '$top': 500}, ok('Check_stops')),
        'Photo_slots': {'type': 'Select', 'runAfter': ok('Check_photos'),
                        'inputs': {'from': "@body('Check_photos')?['value']",
                                   'select': "@concat(item()?['StopKey'], '|', item()?['Item'])"}},
        'Set_stopsFound': {'type': 'SetVariable', 'runAfter': ok('Photo_slots'),
                           'inputs': {'name': 'stopsFound', 'value': "@length(body('Check_stops')?['value'])"}},
        'Set_photosFound': {'type': 'SetVariable', 'runAfter': ok('Set_stopsFound'),
                            'inputs': {'name': 'photosFound',
                                       'value': "@length(union(body('Photo_slots'), body('Photo_slots')))"}},
        'Increment_tries': {'type': 'IncrementVariable', 'runAfter': ok('Set_photosFound'),
                            'inputs': {'name': 'tries', 'value': 1}},
    }
    top['Wait_for_the_run'] = {
        'type': 'Until', 'runAfter': prev, 'actions': loop, 'limit': {'count': MAX_CHECKS + 10, 'timeout': 'PT2H'},
        'expression': ("@or(and(greaterOrEquals(variables('stopsFound'), int(coalesce(triggerOutputs()?['body/NoofStops'], 0))), "
                       "greaterOrEquals(variables('photosFound'), int(coalesce(triggerOutputs()?['body/NoofInvoicePhotos'], 0)))), "
                       f"greaterOrEquals(variables('tries'), {MAX_CHECKS}))"),
    }
    get_items = acts['Get_items']
    get_items['runAfter'] = ok('Wait_for_the_run')
    top['Get_items'] = get_items
    top['Condition'] = acts['Condition']
    for name, a in acts.items():      # anything else the user added stays, after the Condition
        if name not in top and name != 'Delay':
            top[name] = a

    # ---- PDF steps inside the Condition, between the stops table and the email
    lib_part, _, in_lib = PDF_FOLDER.strip('/').partition('/')
    if not lib_part:
        fail('PDF_FOLDER must start with the library, e.g. "/Fleet Photos/Run sheet PDFs"')
    in_lib_enc = ('/' + quote(in_lib)) if in_lib else ''
    lib_q = PHOTOS_LIBRARY.replace("'", "''")
    http_libs = sp_http(site, '_api/v2.0/drives?$select=id,name', ok('Create_HTML'))
    convert = sp_http(site, f"_api/v2.0/drives/@{{first(body('Find_photo_library'))?['id']}}/root:{in_lib_enc}/"
                            f"@{{outputs('Create_HTML')?['body/Name']}}:/content?format=pdf", ok('Find_photo_library'),
                      json_reply=False)
    seen_key = "concat(items('For_each_file')?['StopKey'], '|', items('For_each_file')?['Item'])"
    pdf = {
        'Get_invoice_files': sp('GetFileItems', {'dataset': site, 'table': PHOTOS_LIBRARY,
                                                 '$filter': f"RunKey eq '@{{{run_key}}}'",
                                                 '$orderby': 'Created desc', '$top': 500}, ok('Create_HTML_table')),
        'For_each_file': {
            'type': 'Foreach', 'foreach': "@body('Get_invoice_files')?['value']", 'runAfter': ok('Get_invoice_files'),
            'runtimeConfiguration': {'concurrency': {'repetitions': 1}},
            'actions': {'New_slot': {
                'type': 'If', 'runAfter': {},
                'expression': {'and': [{'equals': [f"@contains(variables('seen'), {seen_key})", False]}]},
                'actions': {
                    'Remember_slot': {'type': 'AppendToArrayVariable', 'runAfter': {},
                                      'inputs': {'name': 'seen', 'value': f'@{seen_key}'}},
                    'Keep_file': {'type': 'AppendToArrayVariable', 'runAfter': ok('Remember_slot'),
                                  'inputs': {'name': 'keep', 'value': "@items('For_each_file')"}}},
                'else': {'actions': {}}}}},
        'Add_PDF_heading': {'type': 'AppendToStringVariable', 'runAfter': ok('For_each_file'), 'inputs': {
            'name': 'html', 'value': (
                "@{concat('<h2 style=\"color:#007070\">Run sheet invoices: ', triggerOutputs()?['body/Title'], ' · ', "
                "formatDateTime(triggerOutputs()?['body/RunDate'], 'dd MMM yyyy'), '</h2><p>Driver: ', "
                "coalesce(triggerOutputs()?['body/DriverName'], ''), ' · Area: ', coalesce(triggerOutputs()?['body/Area'], ''), "
                "' · Stops: ', length(body('Get_items')?['value']), ' · Invoice photos: ', length(variables('keep')), '</p>')}")}},
        'For_each_invoice': {
            'type': 'Foreach', 'foreach': "@reverse(variables('keep'))", 'runAfter': ok('Add_PDF_heading'),
            'runtimeConfiguration': {'concurrency': {'repetitions': 1}},
            'actions': {
                'Get_invoice_content': sp('GetFileContent', {'dataset': site, 'id': "@items('For_each_invoice')?['{Identifier}']",
                                                             'inferContentType': True}, {}),
                'Add_invoice_page': {'type': 'AppendToStringVariable', 'runAfter': ok('Get_invoice_content'), 'inputs': {
                    'name': 'html', 'value': (
                        "@{concat('<div style=\"page-break-before:always\"><p style=\"font-size:14px; color:#1F2933\">', "
                        "items('For_each_invoice')?['Item'], '</p><img src=\"data:image/jpeg;base64,', "
                        "body('Get_invoice_content')?['$content'], '\" style=\"width:100%\"></div>')}")}}}},
        'Close_HTML': {'type': 'AppendToStringVariable', 'runAfter': ok('For_each_invoice'),
                       'inputs': {'name': 'html', 'value': '</body></html>'}},
        'Create_HTML': sp('CreateFile', {'dataset': site, 'folderPath': PDF_FOLDER,
                                         'name': f"@{{concat('Run_', {run_id}, '.html')}}",
                                         'body': "@variables('html')"}, ok('Close_HTML')),
        # the photo library's drive ID, then SharePoint's own file conversion (?format=pdf)
        'Get_site_libraries': http_libs,
        'Find_photo_library': {'type': 'Query', 'runAfter': ok('Get_site_libraries'),
                               'inputs': {'from': "@body('Get_site_libraries')?['value']",
                                          'where': f"@equals(item()?['name'], '{lib_q}')"}},
        'Convert_to_PDF': convert,
        'Save_PDF': sp('CreateFile', {
            'dataset': site, 'folderPath': PDF_FOLDER,
            'name': (f"@{{concat('RunSheet_', replace(coalesce(triggerOutputs()?['body/Title'], 'NoTruck'), ' ', ''), '_', "
                     f"formatDateTime(triggerOutputs()?['body/RunDate'], 'yyyyMMdd'), '_', {run_id}, '.pdf')}}"),
            'body': "@body('Convert_to_PDF')"}, ok('Convert_to_PDF')),
        'Delete_HTML': sp('DeleteFile', {'dataset': site, 'id': "@outputs('Create_HTML')?['body/Id']"}, ok('Save_PDF')),
    }

    email = cond['Send_an_email_(V2)']
    p = email['inputs']['parameters']
    marker = '<p>Waiting for Team Leader verification'
    link = ("<p><b>Invoices:</b> @{length(variables('keep'))} photos. "
            f"<a href=\"{site}@{{replace(outputs('Save_PDF')?['body/Path'], ' ', '%20')}}\">Open the invoices PDF</a>"
            f"@{{if({small}, ' (also attached)', ' (too large to attach)')}}.</p>\n")
    body = p['emailMessage/Body']
    p['emailMessage/Body'] = body.replace(marker, link + marker, 1) if marker in body else body + link
    p['emailMessage/Attachments'] = (f"@if({small}, createArray(addProperty(addProperty(json('{{}}'), 'Name', "
                                     "outputs('Save_PDF')?['body/Name']), 'ContentBytes', body('Convert_to_PDF')?['$content'])), "
                                     "createArray())")
    email['runAfter'] = ok('Delete_HTML')
    update['runAfter'] = ok('Send_an_email_(V2)')

    new_cond = {}
    for name, a in cond.items():
        new_cond[name] = a
        if name == 'Create_HTML_table':
            new_cond.update(pdf)
    new_cond['Update_item'] = update
    top['Condition']['actions'] = new_cond

    if FAILURE_EMAIL:
        top['Tell_owner_it_failed'] = {
            'type': 'OpenApiConnection', 'runAfter': {'Condition': ['Failed', 'TimedOut', 'Skipped']},
            'inputs': {'authentication': AUTH,
                       'host': {'apiId': O365_API, 'connectionName': 'shared_office365', 'operationId': 'SendEmailV2'},
                       'parameters': {'emailMessage/To': FAILURE_EMAIL,
                                      'emailMessage/Subject': f"@{{concat('Run sheet submission email failed for run ', {run_id})}}",
                                      'emailMessage/Body': ('<p>The Run Sheet - Submission email flow failed for run '
                                                            f'@{{{run_id}}}. Open the flow\'s run history to see which step.</p>'),
                                      'emailMessage/Importance': 'High'}}}
    df['actions'] = top

    # ---- new flow name (only SharePoint and Outlook connections: both already in the export)
    if 'shared_office365' not in props['connectionReferences']:
        fail('the export has no Office 365 Outlook connection: is this the Run Sheet - Submission email export?')
    props['displayName'] = FLOW_NAME
    res = manifest['resources']
    flow_res = next(k for k, v in res.items() if v.get('type') == 'Microsoft.Flow/flows')
    res[flow_res]['details']['displayName'] = FLOW_NAME
    res[flow_res]['suggestedCreationType'] = 'New'
    manifest['details']['displayName'] = FLOW_NAME

    files[defs[0]] = json.dumps(flow, ensure_ascii=False).encode('utf-8')
    files['manifest.json'] = json.dumps(manifest, ensure_ascii=False).encode('utf-8')
    files[flow_dir + '/apisMap.json'] = json.dumps(apis).encode('utf-8')
    files[flow_dir + '/connectionsMap.json'] = json.dumps(conns).encode('utf-8')

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{FLOW_NAME} - import package.zip')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    with open(out, 'wb') as fh:
        fh.write(buf.getvalue())
    print(f'wrote {out}')
    print(f'  waits up to {MAX_CHECKS} checks x {WAIT_MINUTES} min; attaches PDFs under {ATTACH_LIMIT_MB} MB')
    print(f'  photo library "{PHOTOS_LIBRARY}", HTML + PDFs in "{PDF_FOLDER}" (converted in SharePoint, no OneDrive)')
    print('  failure email: ' + ('on' if FAILURE_EMAIL else 'off (FAILURE_EMAIL is empty)'))


if __name__ == '__main__':
    main()
