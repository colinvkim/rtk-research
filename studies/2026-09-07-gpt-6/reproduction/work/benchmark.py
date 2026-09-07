"""Reproducible command-output experiment. Run after setup_experiment.py.
The native controls use `rtk run`, which performs no filtering or tracking.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import platform
import random
import shlex
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
OUT = ROOT / 'outputs' / 'rtk-experiment'
OUT.mkdir(parents=True, exist_ok=True)
os.environ['TIKTOKEN_CACHE_DIR'] = str(WORK / 'tokenizer-cache')
import tiktoken
ENC = {name: tiktoken.get_encoding(name) for name in ('o200k_base', 'cl100k_base')}
BASE_ENV = os.environ | {'PATH': str(WORK / 'venv/bin') + os.pathsep + os.environ['PATH'],
    'RTK_DB_PATH': str(WORK / 'bench-tracking.db'), 'NO_COLOR': '1', 'TERM': 'dumb',
    'GIT_PAGER': 'cat', 'PAGER': 'cat', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
    'PYTHONDONTWRITEBYTECODE': '1', 'CARGO_TERM_COLOR': 'never', 'RUST_BACKTRACE': '0',
    'LC_ALL': 'C', 'TZ': 'UTC'}

def measure(command, cwd, env):
    start = time.perf_counter()
    p = subprocess.run(['rtk', 'run', command], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    elapsed = (time.perf_counter() - start) * 1000
    text = p.stdout + p.stderr
    return {'stdout': p.stdout, 'stderr': p.stderr, 'returncode': p.returncode,
            'elapsed_ms': elapsed, 'bytes': len(text.encode()), 'rtk_estimate': math.ceil(len(text.encode()) / 4),
            'tokens': {k: len(e.encode(text, disallowed_special=())) for k, e in ENC.items()},
            'command_tokens': {k: len(e.encode(command, disallowed_special=())) for k, e in ENC.items()},
            'sha256': hashlib.sha256(text.encode()).hexdigest()}

def case(id, task, native, rtk, concise, probes=(), group='routine', cwd='fixture', expected_exit=0):
    return dict(id=id, task=task, group=group, cwd=cwd, commands=dict(native=native, rtk=rtk, concise=concise),
                evidence_probes=list(probes), expected_exit=expected_exit)

CASES = [
    case('cargo_pass', 'Did the 100 selected tests pass?', 'cargo test --offline check_', 'rtk cargo test --offline check_', 'cargo test --offline -q check_', ['100 passed'], cwd='fixture/rust'),
    case('cargo_fail', 'Name the failing test and show the actual and expected values.', 'cargo test --offline', 'rtk cargo test --offline', 'cargo test --offline -q', ['failing_sum', 'left: 4', 'right: 5'], cwd='fixture/rust', expected_exit=101),
    case('pytest_pass', 'Did all 160 parametrized tests pass?', 'pytest tests/test_pass.py', 'rtk pytest tests/test_pass.py', 'pytest -q tests/test_pass.py', ['160 passed']),
    case('pytest_fail', 'Diagnose both failed assertions.', 'pytest tests/test_failure.py', 'rtk pytest tests/test_failure.py', 'pytest -q --tb=short tests/test_failure.py', ['test_invoice_cents', 'test_order_region', 'eu-west-1', '31.0'], expected_exit=1),
    case('pytest_warning', 'Identify any migration warning, deadline and replacement.', 'pytest tests/test_legacy.py', 'rtk pytest tests/test_legacy.py', 'pytest -q tests/test_legacy.py', ['LEGACY_ADAPTER_DEADLINE', '3.2', 'adapter_v2']),
    case('pytest_skip', 'Why was the integration test skipped?', 'pytest -rs tests/test_skipped.py', 'rtk pytest -rs tests/test_skipped.py', 'pytest -q -rs tests/test_skipped.py', ['INTEGRATION_BLOCKER', 'schema 17']),
    case('git_status', 'Identify changed files and staged/unstaged state.', 'git status', 'rtk git status', 'git status --short', ['mixed.txt', 'staged.txt', 'removed.txt', 'new.txt']),
    case('git_diff_small', 'Review the changed consent branch.', 'git diff -- policy.py', 'rtk git diff -- policy.py', 'git diff -U1 -- policy.py', ['if not verified', '+        return True']),
    case('git_diff_large', 'Identify all changed boolean settings.', 'git diff -- settings.py', 'rtk git diff -- settings.py', "git diff -U0 -- settings.py | rg '^[+-][A-Z_]+ = (True|False)'", ['-REQUIRE_VERIFIED_CONSENT = True', '+REQUIRE_VERIFIED_CONSENT = False'], group='boundary'),
    case('git_log_body', 'What are the latest commit deployment and rollback requirements?', 'git log -1', 'rtk git log -1', 'git log -1 --format=%B', ['DEPLOYMENT_PRECONDITION', 'schema must be 17', 'snap-2026-08-31']),
    case('rg_many', 'Who can access /admin/archive?', "rg -n allow_policy routes.py", "rtk rg -n allow_policy routes.py", "rg -n /admin/archive routes.py", ['anonymous'], group='boundary'),
    case('rg_long', 'Does /admin/export require authentication?', 'rg -n /admin/export long_routes.py', 'rtk rg -n /admin/export long_routes.py', "rg -n -o 'requires_auth=[^)]+' long_routes.py", ['requires_auth=False'], group='boundary'),
    case('read_default', 'Inspect the implementation and its retention covenant.', 'cat policy.py', 'rtk read policy.py', 'cat policy.py', ['RC-17', 'if not verified', 'return True']),
    case('read_minimal', 'Inspect the implementation and its retention covenant.', 'cat policy.py', 'rtk read -l minimal policy.py', 'cat policy.py', ['RC-17', 'if not verified', 'return True'], group='opt-in'),
    case('json_array', 'List every deployment that is not ready and its reason.', 'cat deployments.json', 'rtk json deployments.json', "jq -c '.deployments[] | select(.ready == false) | {name, reason}' deployments.json", ['worker-15', 'schema version 17 missing'], group='boundary'),
    case('log_ids', 'Which request failed last, and did failover follow it?', 'cat events.log', 'rtk log events.log', "rg 'ERROR|failover' events.log", ['9002', '12:01:05', 'failover complete'], group='boundary'),
    case('source_rg', 'Locate the real token estimator implementation.', 'rg -n estimate_tokens src/core/tracking.rs', 'rtk rg -n estimate_tokens src/core/tracking.rs', "rg -n -A3 '^pub fn estimate_tokens' src/core/tracking.rs", ['text.len() as f64 / 4.0'], cwd='rtk-source'),
    case('source_read', 'What is the implementation condition for returning raw output?', 'cat src/core/guard.rs', 'rtk read src/core/guard.rs', "rg -n -A7 '^pub fn never_worse' src/core/guard.rs", ['estimate_tokens(filtered) > estimate_tokens(raw)'], cwd='rtk-source'),
]

# Two executable programs with different behavior and identical text after indentation removal.
(WORK / 'fixture/indent_a.py').write_text('def allowed(x):\n    if x:\n        return True\n    return False\n')
(WORK / 'fixture/indent_b.py').write_text('def allowed(x):\n    if x:\n        return True\n        return False\n')

def main():
    (OUT / 'specification.json').write_text(json.dumps(CASES, indent=2) + '\n')
    # Build once without network; all measured cargo invocations have warm compiled artifacts.
    warm = measure('cargo test --offline --no-run', WORK / 'fixture/rust', BASE_ENV)
    if warm['returncode']:
        raise RuntimeError(warm)
    repetitions = 5
    rng = random.Random(20260907)
    results = []
    for spec in CASES:
        cwd = WORK / spec['cwd']
        env = BASE_ENV | {'RTK_TEE_DIR': f'.rtk/tee/{spec["id"]}'}
        records = {arm: [] for arm in spec['commands']}
        for rep in range(repetitions):
            arms = list(spec['commands'])
            rng.shuffle(arms)
            for arm in arms:
                records[arm].append(measure(spec['commands'][arm], cwd, env))
        result = spec.copy()
        result['arms'] = {}
        for arm, samples in records.items():
            first = samples[0]
            content = first['stdout'] + first['stderr']
            capture = OUT / 'captures' / spec['id']
            capture.mkdir(parents=True, exist_ok=True)
            (capture / f'{arm}.stdout.txt').write_text(first['stdout'])
            (capture / f'{arm}.stderr.txt').write_text(first['stderr'])
            summary = {k: v for k, v in first.items() if k not in ('stdout', 'stderr', 'elapsed_ms')}
            summary['elapsed_median_ms'] = statistics.median(x['elapsed_ms'] for x in samples)
            summary['elapsed_samples_ms'] = [x['elapsed_ms'] for x in samples]
            summary['token_samples_o200k'] = [x['tokens']['o200k_base'] for x in samples]
            summary['evidence'] = {probe: probe in content for probe in spec['evidence_probes']}
            summary['exit_samples'] = [x['returncode'] for x in samples]
            summary['mentions_recovery'] = 'tee/' in content or '[full output:' in content or 'rtk proxy' in content
            result['arms'][arm] = summary
        results.append(result)
        counts = {arm: v['tokens']['o200k_base'] for arm, v in result['arms'].items()}
        print(spec['id'], counts, flush=True)
    collision = {}
    for name in ('indent_a', 'indent_b'):
        collision[name] = {}
        for arm, command in [('native', f"rg -n . {name}.py"), ('rtk', f"rtk rg -n . {name}.py")]:
            m = measure(command, WORK / 'fixture', BASE_ENV)
            collision[name][arm] = m['stdout']
        ns = {}
        exec((WORK / f'fixture/{name}.py').read_text(), ns)
        collision[name]['allowed_false_result'] = ns['allowed'](False)
    (OUT / 'indentation-collision.json').write_text(json.dumps(collision, indent=2) + '\n')
    (OUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    rows = []
    for result in results:
        for arm, a in result['arms'].items():
            rows.append(dict(case=result['id'], group=result['group'], arm=arm, command=result['commands'][arm],
                bytes=a['bytes'], rtk_estimate=a['rtk_estimate'], o200k_tokens=a['tokens']['o200k_base'],
                cl100k_tokens=a['tokens']['cl100k_base'], command_o200k_tokens=a['command_tokens']['o200k_base'],
                median_ms=round(a['elapsed_median_ms'], 3), exit_code=a['returncode'],
                missing_probes='; '.join(k for k,v in a['evidence'].items() if not v), recovery_hint=a['mentions_recovery']))
    with (OUT / 'results.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    meta = {'date': '2026-09-07', 'platform': platform.platform(), 'python': sys.version,
        'tiktoken_version': tiktoken.__version__, 'repetitions': repetitions, 'random_seed': 20260907,
        'source_commit': measure('git rev-parse HEAD', WORK / 'rtk-source', BASE_ENV)['stdout'].strip(),
        'rtk_version': measure('rtk --version', WORK, BASE_ENV)['stdout'].strip(),
        'tokenizer_note': 'o200k_base primary; cl100k_base sensitivity. No verified public GPT-6 Astra tokenizer mapping.',
        'method': 'All subprocesses captured fully, without tool output caps. Native via rtk run raw escape hatch. Both stdout and stderr counted. Timings include common outer rtk run overhead; cargo warmed. Existing user RTK default config, tracking redirected and tee path isolated. Exact billing and reasoning tokens not measured.'}
    (OUT / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')

if __name__ == '__main__':
    main()
