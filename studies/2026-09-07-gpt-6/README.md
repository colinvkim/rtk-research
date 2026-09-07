# GPT-6 Astra study · September 7, 2026

[Read the report](REPORT.md).

Eighteen command cases compare ordinary commands, RTK 0.48.0, and hand-selected concise native commands. Nine fresh GPT-6 Astra agents then investigate the same six questions: three runs each with ordinary native commands, RTK, or an explicit concision instruction.

The study directory preserves the saved evidence bundle:

- `results.csv` and `results.json`: command measurements and evidence checks.
- `agent-results.csv` and `summary.json`: agent results and aggregate calculations.
- `captures/`: the first complete stdout and stderr from each command condition.
- `agent-trials/`: instructions, answers, commands, and recorded output.
- `recovery/`: additional reads used to check recovery costs.
- `metadata.json`, grading records, and recording corrections: measurement provenance.
- `reproduction/`: scripts and instructions for rerunning the command benchmark and agent trials.

The checksum manifest verifies this sanitized publication copy. Historical measurements are retained, with separate published-text counts where redaction changed the input. See [publication notes](../../PUBLICATION.md) and the report for limitations.
