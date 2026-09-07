from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
OUT = ROOT / 'outputs/rtk-experiment'
sys.path.insert(0, str(WORK))
from benchmark import BASE_ENV, ENC, measure

results = json.loads((OUT / 'results.json').read_text())
manual_path = WORK / 'manual-grades.json'
manual_grades = json.loads(manual_path.read_text()) if manual_path.exists() else {}
correction_path = WORK / 'stream-corrections.json'
corrections = json.loads(correction_path.read_text()) if correction_path.exists() else {}
summary = {'commands': {}, 'agents': {}, 'runs': []}
for enc in ('o200k_base', 'cl100k_base'):
    totals = {a: sum(c['arms'][a]['tokens'][enc] for c in results) for a in ('native', 'rtk', 'concise')}
    summary['commands'][enc] = totals | {a + '_reduction_pct': 100 * (1 - totals[a]/totals['native']) for a in ('rtk', 'concise')}
summary['commands']['bytes4'] = {a: sum(c['arms'][a]['rtk_estimate'] for c in results) for a in ('native', 'rtk', 'concise')}
summary['commands']['required_evidence_lost'] = [c['id'] for c in results if any(v and not c['arms']['rtk']['evidence'][p] for p,v in c['arms']['native']['evidence'].items())]
summary['commands']['overhead_ms'] = {c['id']: c['arms']['rtk']['elapsed_median_ms'] - c['arms']['native']['elapsed_median_ms'] for c in results}

for p in sorted((WORK / 'agents').iterdir()):
    records_file = p / 'observations/records.jsonl'
    answer_file = p / 'answer.json'
    if not records_file.exists() or not answer_file.exists():
        raise RuntimeError(f'Unfinished trial: {p.name}')
    records = [json.loads(x) for x in records_file.read_text().splitlines()]
    answer = json.loads(answer_file.read_text())
    # This checks coverage of the required facts; semantic correctness was also
    # manually assessed against the source and test outputs by the parent agent.
    content = json.dumps(answer).lower()
    fact_coverage = {
        'test_counts_and_causes': all(s in json.dumps(answer.get('q1', {})).lower() for s in ('160', '2', 'int', '30', '31', 'us-east-1', 'eu-west-1')),
        'warning_deadline': all(s in json.dumps(answer.get('q2', {})).lower() for s in ('3.2', 'adapter_v2')),
        'commit_requirements': all(s in json.dumps(answer.get('q3', {})).lower() for s in ('17', 'snap-2026-08-31')),
        'boolean_change': all(s in json.dumps(answer.get('q4', {})).lower() for s in ('require_verified_consent', 'true', 'false')),
        'route_access': all(s in json.dumps(answer.get('q5', {})).lower() for s in ('anonymous', 'false')),
        'deployment_exception': all(s in json.dumps(answer.get('q6', {})).lower() for s in ('worker-15', 'schema version 17 missing')),
    }
    grade = manual_grades.get(p.name, {})
    score = grade.get('questions_correct') if grade.get('answer_sha256') == hashlib.sha256(answer_file.read_bytes()).hexdigest() else None
    row = {'run': p.name, 'arm': p.name.split('_r')[0], 'questions_correct_manual': score,
        'fact_coverage': fact_coverage, 'calls': len(records),
        'tool_output_tokens': sum(r['output_tokens'] for r in records),
        'tool_output_excluding_task': sum(r['output_tokens'] for r in records if r['requested_argv'] != ['cat', 'TASKS.md']),
        'native_command_tokens': sum(r['requested_command_tokens'] for r in records),
        'explicit_raw_bypass_calls': sum(r['requested_argv'][:2] == ['rtk', 'proxy'] for r in records),
        'child_command_wall_ms': sum(r['elapsed_ms'] for r in records)}
    row['command_plus_output_tokens'] = row['native_command_tokens'] + row['tool_output_tokens']
    correction = corrections.get(p.name, {})
    row['observed_output_tokens'] = row['tool_output_tokens'] + correction.get('net_output_token_adjustment', 0)
    row['additional_unrecorded_attempts'] = correction.get('additional_attempts_not_recorded', 0)
    row['observed_output_plus_command_tokens'] = row['native_command_tokens'] + row['observed_output_tokens']
    summary['runs'].append(row)
    dest = OUT / 'agent-trials' / p.name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(answer_file, dest / 'answer.json')
    shutil.copy2(p / 'TASKS.md', dest / 'TASKS.md')
    shutil.copy2(records_file, dest / 'records.jsonl')
    for obs in (p / 'observations').glob('*.txt'):
        shutil.copy2(obs, dest / obs.name)

for arm in ('native', 'rtk', 'concise'):
    rows = [r for r in summary['runs'] if r['arm'] == arm]
    summary['agents'][arm] = {'n': len(rows), 'output_tokens': [r['observed_output_tokens'] for r in rows],
        'median_output_tokens': statistics.median(r['observed_output_tokens'] for r in rows),
        'mean_output_tokens': statistics.mean(r['observed_output_tokens'] for r in rows),
        'sum_output_tokens': sum(r['observed_output_tokens'] for r in rows),
        'median_output_plus_command': statistics.median(r['observed_output_plus_command_tokens'] for r in rows),
        'calls': [r['calls'] for r in rows], 'correct_questions_per_run': [r['questions_correct_manual'] for r in rows]}

recovery_commands = {
    'pytest_warning': 'pytest -q tests/test_legacy.py',
    'pytest_skip': 'pytest -q -rs tests/test_skipped.py',
    'git_diff_large_full': 'git diff -- settings.py',
    'git_diff_large_targeted': "git diff -U0 -- settings.py | rg '^[+-][A-Z_]+ = (True|False)'",
    'rg_many_targeted': 'rg -n /admin/archive routes.py',
    'json_array_targeted': "jq -c '.deployments[] | select(.ready == false) | {name, reason}' deployments.json",
    'log_ids_targeted': "rg 'ERROR|failover' events.log",
}
tee = sorted((WORK / 'fixture/.rtk/tee/pytest_fail').glob('*.log'))[0]
recovery_commands['pytest_fail_tee'] = 'cat ' + str(tee.relative_to(WORK / 'fixture'))
rgtee = sorted((WORK / 'fixture/.rtk/tee/rg_many').glob('*.log'))[0]
recovery_commands['rg_many_tail'] = 'tail -n +26 ' + str(rgtee.relative_to(WORK / 'fixture'))
recovery = {}
for key, cmd in recovery_commands.items():
    m = measure(cmd, WORK / 'fixture', BASE_ENV)
    recovery[key] = {k:v for k,v in m.items() if k not in ('stdout','stderr')}
    recovery[key]['command'] = cmd
    recovery[key]['contains_region'] = 'eu-west-1' in m['stdout']
    d = OUT / 'recovery'
    d.mkdir(exist_ok=True)
    (d / (key + '.txt')).write_text(m['stdout'] + m['stderr'])
summary['recovery'] = recovery

db = sqlite3.connect(WORK / 'bench-tracking.db')
tables = db.execute('select name, sql from sqlite_master where type = ?', ('table',)).fetchall()
(OUT / 'tracking-schema.json').write_text(json.dumps(tables, indent=2) + '\n')
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
with (OUT / 'agent-results.csv').open('w') as f:
    cols = [k for k in summary['runs'][0] if k != 'fact_coverage']
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
    w.writeheader()
    w.writerows(summary['runs'])
print(json.dumps(summary['agents'], indent=2))
print('Lost task evidence:', summary['commands']['required_evidence_lost'])
print('Recovery tokens:', {k:v['tokens']['o200k_base'] for k,v in recovery.items()})
print('Coverage:', {r['run']:all(r['fact_coverage'].values()) for r in summary['runs']})
