# Reproduce the command benchmark

Run from this reproduction/ directory in a fresh checkout of this bundle. Requirements: rtk 0.48.0, Python 3.14, uv, cargo, git, rg, jq. The original run used macOS and the existing default rtk settings; configuration and platform changes can change results. Use isolated RTK_DB_PATH and RTK_TEE_DIR as the scripts do. The fixture is synthetic and creates only a local Git repository.

All shell examples start with rtk. Commands that download dependencies require network access.

```sh
rtk run 'uv venv --python 3.14 work/venv'
rtk run 'uv pip install --python work/venv/bin/python tiktoken==0.14.0 pytest==9.1.1'
rtk run 'git clone --branch v0.48.0 --depth 1 https://github.com/rtk-ai/rtk.git work/rtk-source'
rtk run 'env TIKTOKEN_CACHE_DIR=work/tokenizer-cache work/venv/bin/python -c "import tiktoken; tiktoken.get_encoding("o200k_base"); tiktoken.get_encoding("cl100k_base")"'
rtk run 'work/venv/bin/python work/setup_experiment.py'
rtk run 'work/venv/bin/python work/benchmark.py'
```

The source commit must resolve to fde0a8f185945556f51718de0f4c430bb62b3df6. Outputs appear under outputs/rtk-experiment/. Run setup in a fresh directory; it is not designed to reset a modified prior fixture. It invokes Git commits with a fixed experiment identity and disables hooks/signing in that fixture only. No external messages or repository pushes occur.

For agent trials, use fresh agents with the instructions in ../agent-trials/ relative to this directory. Replace the absolute workspace paths with this reproduction root and use the same model/reasoning settings. The gateway infers native, rtk, or concise from its current fixture directory. It records each command and its entire stdout/stderr. Do not rerun the same agent with prior trial context. Three repetitions per arm were used in the original run; replicate fixture directories from a fresh setup before agents run. Analyze with analyze_experiment.py only after all trials have answer.json. For semantic grades, manually review each new answer and provide work/manual-grades.json with per-run questions_correct and answer_sha256 fields. Without a matching manual review, the analyzer reports a null manual score; its fact-coverage check alone is not a semantic grader. The original manual grades are retained as evidence, not automatically assigned to future answers. Model choices are stochastic, and exact replication requires the same model deployment, tool definitions, and runtime. The recorded observations can be audited without launching models.
