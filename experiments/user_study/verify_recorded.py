"""Verify author-run correctness evidence, not participant study outcomes."""
import json
import sys
from pathlib import Path
from model import expected,check_evidence
from study import read_csv

root=Path(__file__).with_name('results')/(sys.argv[1] if len(sys.argv)>1 else '2026-11-15')
record=json.loads((root/'native-checks.json').read_text(encoding='utf-8'))
assert record['passed'] and not record['changed_inputs']
short=record.get('protocol')=='35-minute'
cases=[('sweep-starter','visible'),('sweep','visible'),('sweep','first'),('adapt','visible'),('adapt','first'),('adapt','cap')]
if not short:cases += [('files-starter','visible'),('files','visible'),('files','extra')]
required={f'{tool}-{pack}-{task}-{variant}' for tool in ('knime','waffle') for pack in ('A','B') for task,variant in cases}
assert {r['id'] for r in record['runs']}==required
ids=set()
for r in record['runs']:
    assert r['id'] not in ids
    ids.add(r['id'])
    want=expected(root/'data'/r['pack']/r['case'],r['task'],r['target'])
    assert r['passed'] and not r['error']
    assert check_evidence(want,r['visits'],r['results'],r['exit_code']),r['id']
    raw=root/'raw'/r['id']
    assert int((raw/'exit-code.txt').read_text())==r['exit_code']
    for field in ('visits','results'):
        rows=read_csv(raw/(field+'.csv'),r['task'].startswith('files'))
        if r['task'].startswith('files'):
            rows.sort(key=lambda row:row['filename'])
        assert rows==r[field],(r['id'],field)
print(f'{len(ids)} recorded native checks match the independent reference.')
