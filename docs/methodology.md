# Methodology and evidence notes

This repository groups studies by date and model context. Keep each study's RTK version, workload, commands, results, and limitations together. Add a new dated study when methods or versions change.

Measure command-output reduction separately from task completion. Useful records include stdout and stderr, the tokenizer and version, exit codes, required information retained or omitted, command choices, and recovery reads. Label hand-selected commands separately from commands chosen autonomously by agents. Record exact model identifiers and reasoning settings when available.

Report both case-level results and the calculation behind aggregates. A ratio of summed token counts can be dominated by one large output. A median of per-case percentages answers a different question. Neither is an estimate of savings across all coding work without an appropriate workload sample.

The July study used `o200k_base` via tiktoken 0.13.0's GPT-5 mapping. The September study used tiktoken 0.14.0 with `o200k_base` as its primary encoding and `cl100k_base` as a sensitivity check. These are exact counts for the named encodings, not verified GPT-5.6 or GPT-6 billing counts. RTK's bytes-divided-by-four estimate is tracked separately.

The July study compares eight sets of hand-selected commands and checks information retention. It does not contain isolated model trials. The September study adds three agent runs per condition on the same six-question fixture, with manual grading. Different RTK versions, workloads, methods, and agent sampling prevent interpreting the two studies as a controlled model-generation comparison.

The reports retain their original findings, with publication redaction documented separately. The July archive includes its report, original harness, and three synthetic fixture files; its historical command-output JSON was not found in the supplied directory. The September archive includes its full saved evidence bundle, with token counts, captures, prompts, answers, timing samples, grading records, recording corrections, and reproduction scripts.

The July report's opening paragraph calls the 78.3% aggregate a byte-weighted total. Its results table instead supports a ratio of summed `o200k_base` token counts: 47,170 ordinary tokens and 10,214 RTK tokens. The report separately gives 79.5% for the bytes/4 estimate. Read the 78.3% figure as the token-weighted aggregate.

Personal filesystem paths in published prompts and outputs have been replaced with placeholders. Historical measurements and published-text counts are distinguished, and hashes verify the sanitized files. See [publication notes](../PUBLICATION.md).
