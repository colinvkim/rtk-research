# GPT-5.6 study · July 9, 2026

[Read the report](REPORT.md).

Eight command cases compare ordinary commands, task-specific concise native commands, and RTK 0.43.0. The research checks token counts, exit codes, and information retention. The concise commands were hand-selected; this was not an isolated agent experiment.

Files:

- `REPORT.md`: original findings and limitations.
- `harness/benchmark_rtk.py`: original benchmark script, preserved unchanged.
- `fixtures/`: the synthetic JSON, search, and pytest inputs.
- `metadata.json`: study facts and evidence availability.

The report contains the historical measurements. Separate saved JSON output and complete raw captures were not found in the supplied study directory, so this archive does not manufacture them or substitute a new run.

To rerun the original harness, recreate its expected layout under a fresh study workspace: `work/benchmark_rtk.py`, `work/benchmark-fixture/`, `work/bench-venv/`, `work/rtk-src/`, and `work/rtk-home/`. It requires RTK 0.43.0, tiktoken 0.13.0, pytest, Git, ripgrep, and jq. The script expects the RTK repository to contain commit `bb01d6c` and derives other cases from that checkout's current history and files. Its original execution-time source revision was not recorded in the report, so exact historical reproduction is not guaranteed. Results are printed as JSON to stdout.
