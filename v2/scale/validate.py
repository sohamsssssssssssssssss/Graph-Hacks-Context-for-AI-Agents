"""Postprocess/check stored artifacts only. Never executes benchmark queries."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from v2.scale.benchmark import HERE, ROOT, report


def main():
    manifest=json.loads((HERE/'manifest.json').read_text())
    for name in ['SPEC.md','queries.py','inputs.json']:
        assert (HERE/name).read_bytes()==subprocess.check_output(['git','show','scale-v1:v2/scale/'+name],cwd=ROOT)
    validated={}
    for size in ['10k','100k']:
        checks_path=HERE/(size+'_correctness.json')
        checks=json.loads(checks_path.read_text()) if checks_path.exists() else []
        assert all(r['match'] and r['sqlite']==r['falkordb'] for r in checks)
        path=HERE/(size+'_timings.jsonl')
        rows=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        keys={(r['query'],r['input'],r['repeat'],r['mode'],r['engine']) for r in rows}
        assert len(keys)==len(rows),'duplicate timing samples'
        assert len(rows)<=6400 and all(r['ms']>=0 for r in rows)
        assert all(0<=r['input']<20 and 0<=r['repeat']<20 for r in rows)
        counts=Counter((r['query'],r['mode'],r['engine']) for r in rows)
        if len(rows)==6400:assert all(v==400 for v in counts.values()) and len(counts)==16
        if rows:assert len(checks)==80,'timing began before complete correctness check'
        for name,expected in manifest['sizes'][size]['data_sha256'].items():
            assert hashlib.sha256((HERE/'data'/size/name).read_bytes()).hexdigest()==expected
        validated[size]={'exact_correctness_checks':len(checks),'mismatches':0,'timing_samples':len(rows),
                         'planned_timing_samples':6400,'unique_samples':len(keys),
                         'samples_per_group':{'/'.join(k):v for k,v in sorted(counts.items())}}
    expected_tags={'cases-v1':'6d29174a33068d0236495d86ca324eba666af617',
                   'attacks-v1':'1e49743c6c0edc68876e1e544a2fde2f80bb470c',
                   'real-v1':'ffee6d95ca08c5d1f24f4a447bf40ed12004d088',
                   'real-agent-v1':'fbb88e2c7ad7894bcffb206b97abec0c1af86301'}
    for tag,sha in expected_tags.items():
        assert subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()==sha,tag
    for name,sha in json.loads((HERE/'environment.json').read_text())['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    events=[json.loads(line) for line in (HERE/'journal.jsonl').read_text().splitlines()]
    validated['infrastructure_resumes']=sum(e['event']=='infrastructure_resume' for e in events)
    (HERE/'validation.json').write_text(json.dumps(validated,indent=2)+'\n')
    # Re-render arithmetic and explanatory notes from stored samples, not a rerun.
    report(manifest)
    print(json.dumps(validated,indent=2))


if __name__=='__main__':main()
