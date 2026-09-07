"""Record one model-selected command. The arm is inferred from the current directory.

Use: rtk run 'ABSOLUTE_VENV_PYTHON ABSOLUTE_OBSERVE_PATH -- git status'
All native child commands also use the documented `rtk run` raw escape hatch.
"""
from pathlib import Path
import datetime
import fcntl
import json
import os
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
cwd = Path.cwd()
run_id = cwd.name
arm = run_id.split('_r')[0]
assert cwd.parent == ROOT / 'work' / 'agents' and arm in ('native', 'rtk', 'concise')
args = sys.argv[1:]
if args and args[0] == '--':
    args = args[1:]
assert args
venv = ROOT / 'work' / 'venv'
env = os.environ | {'PATH': str(venv / 'bin') + os.pathsep + os.environ['PATH'],
    'RTK_DB_PATH': str(cwd / 'observations' / 'tracking.db'), 'RTK_TEE_DIR': 'observations/tee',
    'NO_COLOR': '1', 'TERM': 'dumb', 'GIT_PAGER': 'cat', 'PAGER': 'cat', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
    'TIKTOKEN_CACHE_DIR': str(ROOT / 'work' / 'tokenizer-cache')}
if arm == 'rtk' and args[0] != 'rtk':
    if args[0] == 'cat':
        actual = ['rtk', 'read', *args[1:]]
    elif args[0] in ('git', 'rg', 'ls', 'pytest', 'cargo', 'find', 'wc'):
        actual = ['rtk', *args]
    else:
        actual = ['rtk', 'run', shlex.join(args)]
else:
    actual = args if args[0] == 'rtk' else ['rtk', 'run', shlex.join(args)]
start = time.perf_counter()
p = subprocess.run(actual, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
elapsed = time.perf_counter() - start
observations = cwd / 'observations'
observations.mkdir(exist_ok=True)
with (observations / 'records.jsonl').open('a+') as record_file:
    fcntl.flock(record_file, fcntl.LOCK_EX)
    record_file.seek(0)
    seq = len(record_file.readlines()) + 1
    output = p.stdout + p.stderr
    (observations / f'{seq:03}.txt').write_text(output)
    import tiktoken
    enc = tiktoken.get_encoding('o200k_base')
    record = {'seq': seq, 'arm': arm, 'run_id': run_id, 'requested_argv': args, 'executed_argv': actual,
        'requested_command_tokens': len(enc.encode(shlex.join(args))),
        'executed_command_tokens': len(enc.encode(shlex.join(actual))),
        'output_tokens': len(enc.encode(output)), 'output_bytes': len(output.encode()),
        'returncode': p.returncode, 'elapsed_ms': round(elapsed * 1000, 3),
        'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    record_file.write(json.dumps(record) + '\n')
    record_file.flush()
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)
