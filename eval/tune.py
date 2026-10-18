"""Freeze severity cutoff using only four development cases, never frozen answers."""
import json
from pathlib import Path
import re
from datetime import datetime,timezone

import sys
if __package__ in {None, ''}:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.tools import ToolRuntime
from llm import digest

ROOT=Path(__file__).resolve().parents[1]


def tune():
    frozen=ROOT/'eval/config_frozen.json'
    if frozen.exists():raise RuntimeError('Configuration already frozen; do not retune for this evaluation')
    cases=[json.loads(line) for line in (ROOT/'cases/dev_cases.jsonl').read_text().splitlines()]
    assert len(cases)==4
    expectations={c['input']['service']:re.search(r'severity_expectation=(elevated|normal)',c['notes'])[1] for c in cases}
    result=ToolRuntime().criticality(list(expectations))
    rows=result['services']
    low=[r['score'] for r in rows if expectations[r['service'].removeprefix('service-')]=='normal']
    high=[r['score'] for r in rows if expectations[r['service'].removeprefix('service-')]=='elevated']
    if not low or not high or max(low)>=min(high):raise RuntimeError('Dev rubric is not separable; needs author review')
    cutoff=(max(low)+min(high))/2
    config_path=ROOT/'app/config.json';config=json.loads(config_path.read_text());config['pagerank_severity_cutoff']=cutoff
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    manifest={'config_sha256':digest(config),'dev_sha256':digest(cases),'cutoff':cutoff,
              'frozen_at':datetime.now(timezone.utc).isoformat(),'method':'midpoint between maximum normal and minimum elevated development score',
              'algorithm':result['algorithm'],'dev_scores':rows}
    frozen.write_text(json.dumps(manifest,indent=2)+'\n')
    lines=['# Development-only severity tuning','',f'Chosen pagerank_severity_cutoff: **{cutoff:.17g}**.',
      '', 'Only four cases/dev_cases.jsonl inputs and their explicit synthetic severity rubric were used. No frozen answers/outcomes or evaluation failures were used to choose the cutoff. These primary input services are absent from the frozen primary inputs; they can still be dependency neighbors in the same synthetic graph.',
      '', '| Dev service | Expected severity | PageRank |','| --- | --- | ---: |']
    for r in sorted(rows,key=lambda r:r['service']):
      service=r['service'].removeprefix('service-');lines.append(f'| {service} | {expectations[service]} | {r["score"]:.17g} |')
    lines+=['',f'Cutoff is the midpoint of maximum normal {max(low):.17g} and minimum elevated {min(high):.17g}, maximizing the separating margin for this dev rubric (4/4 dev severity classifications).',
      '', 'This separates DNS/image delivery infrastructure from ETL/ML batch work on the synthetic graph. It is not a production severity calibration. It does not change ACT/READ confidence thresholds or grant authorization. No LLM was needed to fit this one scalar.',
      '', f'Config frozen SHA-256: `{manifest["config_sha256"]}`. The eval runner refuses config/dev changes and records case/prompt/model hashes before the one frozen evaluation. Timing measurements are independent of severity fitting.']
    (ROOT/'docs/tuning.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'chosen_cutoff':cutoff,'dev_accuracy':'4/4','config_sha256':manifest['config_sha256']}))


if __name__=='__main__':tune()
