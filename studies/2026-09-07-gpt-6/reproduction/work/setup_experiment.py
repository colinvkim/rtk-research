from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
FIX = WORK / 'fixture'
FIX.mkdir(exist_ok=True)

def write(name, content):
    p = FIX / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip('\n'))

def run(cmd, cwd=FIX):
    env = os.environ | {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
                        'GIT_AUTHOR_DATE': '2026-09-01T12:00:00Z', 'GIT_COMMITTER_DATE': '2026-09-01T12:00:00Z'}
    p = subprocess.run(['rtk', 'run', cmd], cwd=cwd, env=env, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((cmd, p.stdout, p.stderr))
    return p.stdout

write('.gitignore', '''
__pycache__/
.pytest_cache/
target/
.rtk/
observations/
answer.json
TASKS.md
''')
write('pytest.ini', '''
[pytest]
filterwarnings = default
addopts = -p no:cacheprovider
''')
write('tests/test_pass.py', '''
import pytest

@pytest.mark.parametrize("value", range(160))
def test_identity(value):
    assert value == value
''')
write('tests/test_legacy.py', '''
import warnings

def test_legacy_adapter():
    warnings.warn("LEGACY_ADAPTER_DEADLINE: legacy adapter is removed in release 3.2; use adapter_v2", DeprecationWarning)
    assert True
''')
write('tests/test_failure.py', '''
def invoice_total(prices):
    return sum(int(price) for price in prices)

def test_invoice_cents():
    assert invoice_total([10.75, 20.25]) == 31.0

def test_order_region():
    actual = {"order_id": "ORD-7721", "region": "us-east-1", "state": "ready"}
    expected = {"order_id": "ORD-7721", "region": "eu-west-1", "state": "ready"}
    assert actual == expected
''')
write('tests/test_skipped.py', '''
import pytest

@pytest.mark.skip(reason="INTEGRATION_BLOCKER: staging database schema 17 is required")
def test_schema_compatibility():
    assert True
''')
write('policy.py', '''
def may_delete_archive(role, verified):
    # Retention covenant RC-17 requires both operator role and verified consent.
    if role != "operator":
        return False
    if not verified:
        return False
    return True
''')
write('routes.py', ''.join(f'allow_policy("/public/route-{i:02}", roles=["reader"])\n' for i in range(40)) + 'allow_policy("/admin/archive", roles=["anonymous"])\n')
write('long_routes.py', 'route("/admin/export", description="' + 'A routine diagnostic endpoint with documented ownership. ' * 15 + '", requires_auth=False)\n')
write('deployments.json', json.dumps({'deployments': [{'name': f'worker-{i:02}', 'region': 'eu-west-1', 'ready': True} for i in range(15)] + [{'name': 'worker-15', 'region': 'eu-west-1', 'ready': False, 'reason': 'schema version 17 missing'}]}, indent=2) + '\n')
write('events.log', ''.join(f'2026-09-01T12:00:{i:02} INFO health check passed\n' for i in range(30)) + '2026-09-01T12:01:00 ERROR request 7001 failed on /api/orders\n2026-09-01T12:01:03 ERROR request 9002 failed on /api/orders\n2026-09-01T12:01:05 INFO failover complete\n')
write('settings.py', ''.join(f'THRESHOLD_{i:03} = {i}\n' for i in range(90)) + 'REQUIRE_VERIFIED_CONSENT = True\n')
write('staged.txt', 'baseline\n')
write('mixed.txt', 'baseline\n')
write('removed.txt', 'baseline\n')
write('bin/deploy.sh', '#!/bin/sh\nexit 0\n')
(FIX / 'bin/deploy.sh').chmod(0o755)
write('bin/helpers.sh', 'deployment helpers\n')
write('rust/Cargo.toml', '''
[package]
name = "rtk-output-experiment"
version = "0.1.0"
edition = "2021"
''')
write('rust/src/lib.rs', '#[cfg(test)]\nmod tests {\n' + ''.join(f'    #[test]\n    fn check_{i:03}() {{ assert_eq!({i}, {i}); }}\n' for i in range(100)) + '    #[test]\n    fn failing_sum() { assert_eq!(2 + 2, 5, "CALCULATION_SENTINEL"); }\n}\n')
if not (FIX / '.git').exists():
    run('git init -q -b feat/rtk-experiment')
    run('git config user.name "RTK Experiment"')
    run('git config user.email "experiment@example.invalid"')
    run('git config core.hooksPath /dev/null')
    run('git config commit.gpgsign false')
    run('git config color.ui false')
    run('git add .')
    run('git commit -q -m "feat: establish experiment fixture"')
    write('release.txt', 'release 3.2\n')
    run('git add release.txt')
    run('git commit -q -m "feat: prepare adapter release" -m "Migrate the adapter before deploying.\n\nDEPLOYMENT_PRECONDITION: database schema must be 17.\nROLLBACK_REQUIREMENT: restore snapshot snap-2026-08-31 before downgrade."')

write('staged.txt', 'staged change\n')
write('mixed.txt', 'staged phase\n')
run('git add staged.txt mixed.txt')
write('mixed.txt', 'unstaged phase\n')
(FIX / 'removed.txt').unlink(missing_ok=True)
write('new.txt', 'untracked\n')
write('policy.py', '''
def may_delete_archive(role, verified):
    # Retention covenant RC-17 requires both operator role and verified consent.
    if role != "operator":
        return False
    if not verified:
        return True
    return True
''')
write('settings.py', ''.join(f'THRESHOLD_{i:03} = {i+1}\n' for i in range(90)) + 'REQUIRE_VERIFIED_CONSENT = False\n')

tasks = '''You are investigating a small Python service before deployment. Answer the following six questions accurately, using commands and files in this directory. Do not edit application code or tests. There is no network requirement.

1. Run tests/test_pass.py and tests/test_failure.py. Report the passing and failing test counts and the root cause of each failed test.
2. Run tests/test_legacy.py. Does its output identify a migration deadline? State the release and replacement adapter, or explicitly state that none was reported.
3. Inspect the latest commit message. State its deployment precondition and rollback requirement.
4. Inspect uncommitted changes to settings.py. Identify every change to a boolean setting and its security implication.
5. Inspect the route definitions. Which roles may access /admin/archive, and does /admin/export require authentication?
6. Inspect deployments.json. List every deployment that is not ready and the stated reason.

Return a JSON answer with keys q1 through q6, and a short explanation of any additional reads you needed after incomplete output. Save the same JSON in answer.json using apply_patch. Do not count information as absent merely because an output was truncated. You may use whichever command flags and follow-up reads you judge appropriate.
'''
for arm in ('native', 'rtk', 'concise'):
    dest = WORK / 'agents' / arm
    if not dest.exists():
        shutil.copytree(FIX, dest, ignore=shutil.ignore_patterns('target', '__pycache__', '.pytest_cache'))
    (dest / 'TASKS.md').write_text(tasks)
    (dest / 'observations').mkdir(exist_ok=True)

manifest = {str(p.relative_to(FIX)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIX.rglob('*')) if p.is_file() and '.git' not in p.parts}
(WORK / 'fixture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'fixture': str(FIX), 'files': len(manifest), 'agent_arms': ['native', 'rtk', 'concise']}, indent=2))
