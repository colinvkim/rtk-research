# Does rtk help GPT-6 Astra? A reproducible pilot

> Publication copy: Personal paths are redacted. Measurements describe the original run; see [publication notes](../../PUBLICATION.md) for published-text counts and updated hashes.

RTK reduces command output substantially, but smaller first responses do not guarantee less reading to finish a task. In this experiment, rtk 0.48.0 reduced the summed output of 18 selected command cases by **61.6%**. In nine isolated Astra investigations, however, the rtk group read **13.4% more command-output tokens on average** than ordinary native commands after follow-up reads. Native commands with an explicit concision instruction used **26.4% less**. All nine runs answered all six questions correctly.

These are measurements of command text using a public tokenizer, not provider billing, model reasoning tokens, or an estimate of savings across all development work. The fixture deliberately contains information-loss traps. The results support selective use of rtk; they do not establish that rtk generally increases costs or that newer models have made it unnecessary.

**What was tested.** The installed binary was rtk 0.48.0, with source pinned to [release commit fde0a8f](https://github.com/rtk-ai/rtk/commit/fde0a8f185945556f51718de0f4c430bb62b3df6). The experiment ran on macOS with Python 3.14.6, pytest 9.1.1, cargo 1.97.1, and ripgrep 15.2.0. Existing rtk settings matched default limits: 25 search results per file, 200 overall, and raw-output recovery primarily on failure. Telemetry was already disabled. Tracking and recovery files were redirected into the experiment. No user project or global rtk configuration was changed.

RTK's [documentation](https://github.com/rtk-ai/rtk/blob/fde0a8f185945556f51718de0f4c430bb62b3df6/docs/guide/resources/savings-explained.md) describes output compression, and its [counter implementation](https://github.com/rtk-ai/rtk/blob/fde0a8f185945556f51718de0f4c430bb62b3df6/src/core/tracking.rs) estimates tokens as ceiling(bytes / 4). I instead counted all captured stdout and stderr with tiktoken 0.14.0: `o200k_base` as the primary encoding and `cl100k_base` as a sensitivity check. The installed [tiktoken model map](https://github.com/openai/tiktoken/blob/main/tiktoken/model.py) did not contain a verified GPT-6 Astra mapping. These counts are therefore exact for the named encodings and proxies for Astra's context consumption.

**Command experiment.** Each case had three arms: an ordinary native command, its rtk counterpart, and a hand-selected native command tailored to the stated question. Sixteen cases used a small generated development repository; two searched/read unmodified rtk release source. Cargo and pytest tests actually ran. This is a deterministic fixture study, not a random sample of real projects.

Every arm ran five times, with arm order shuffled within each case using seed 20260907. Cargo was compiled once before measurement and ran offline. Complete output was captured to files before tool-output limits could truncate it. Token tables use the first complete capture; all five timing/token samples are retained. Native commands used rtk's documented `run` escape hatch, which does no filtering or tracking. That preserved the user's instruction to prefix shell calls with rtk. Both arms share this outer harness cost; the rtk arm adds its actual filter invocation.

| Question / command case | Native tokens | RTK tokens | Task-specific native tokens | Evidence check |
|---|---:|---:|---:|---|
| Cargo: 100 passing tests | 994 | 21 | 50 | Checked evidence preserved |
| Cargo: one failing test | 1,109 | 136 | 169 | Checked evidence preserved |
| Pytest: 160 passing tests | 122 | 7 | 29 | Checked evidence preserved |
| Pytest: two failed assertions | 405 | 146 | 249 | Required evidence omitted |
| Pytest: migration warning | 248 | 7 | 156 | Required evidence omitted |
| Pytest: skip reason | 144 | 15 | 52 | Required evidence omitted |
| Git status | 156 | 49 | 41 | Checked evidence preserved |
| Small code diff | 87 | 81 | 76 | Checked evidence preserved |
| Large diff, boolean change | 1,868 | 1,072 | 22 | Required evidence omitted |
| Latest commit requirements | 105 | 63 | 45 | Checked evidence preserved |
| Search: 41 matches | 612 | 419 | 12 | Required evidence omitted |
| Search: one long line | 134 | 134 | 6 | Checked evidence preserved |
| Read: default | 48 | 48 | 48 | Checked evidence preserved |
| Read: opt-in minimal | 48 | 31 | 48 | Required evidence omitted |
| JSON: late array exception | 485 | 36 | 15 | Required evidence omitted |
| Logs: last request and timing | 573 | 67 | 63 | Required evidence omitted |
| Real rtk source: search | 302 | 302 | 54 | Both broad searches miss the formula; targeted query finds it |
| Real rtk source: read | 361 | 361 | 66 | Checked evidence preserved |
| **Sum of selected cases** | **7,801** | **2,995** | **1,201** | Selection-specific; not a task-success score |

RTK reduced this aggregate by 61.6%; the hand-selected native commands reduced it by 84.6%. The second tokenizer gave 61.6% and 84.7%, respectively. These are ratios of sums, not averages of individual percentages. The concise arm is an achievable command-selection baseline, not a claim that Astra will reliably choose every optimal command. For example, a generic query for changed boolean assignments reduced the large diff from 1,868 tokens to 22; the actual agents generally read a larger diff.

The clear compression wins were repetitive test results: 100 passing Cargo tests fell from 994 to 21 tokens, and a failing Cargo run fell from 1,109 to 136 while preserving the tested diagnostic. Native quiet mode already reduced these to 50 and 169. RTK therefore still offered incremental savings of 58% and 20%, respectively, over those concise native commands.

**Information that was lost.** Eight cases omitted at least one predeclared evidence item visible in the native output. This includes one explicitly opt-in `read -l minimal` case. It is a list of demonstrated failure modes, not an estimated 8/18 probability of harm in normal work.

- A passing pytest run emitted a warning naming release 3.2 and `adapter_v2`. RTK returned only `Pytest: 1 passed`, with no warning or recovery hint. Native `pytest -q` retained the warning.
- Pytest's region assertion lost the actual/expected region details. The raw recovery log contained them, so rerunning the test was unnecessary if the agent used that log. RTK keeps only a few relevant lines per failure.
- An explicitly requested pytest skip report lost the schema-17 skip reason, although the skipped count survived.
- A 91-setting diff showed the old consent requirement but truncated the added `REQUIRE_VERIFIED_CONSENT = False`. It did disclose truncation and offered `--no-compact`.
- A 41-match search stopped after the first 25 matches and omitted the anonymous admin route. It disclosed 16 more matches and supplied a usable recovery command.
- `rtk json` summarized a 16-element array using the first element and a count. The only unready deployment was the last element and disappeared. A native `jq` predicate found it in 15 tokens.
- `rtk log` merged failures for request IDs 7001 and 9002, retained the first representative, and collapsed the failover event into an info count. It could not answer which request failed last or establish the requested sequence.
- Opt-in minimal file reading removed the retention-covenant comment; default reading kept it.

There were meaningful negative results too. Default `rtk read` was byte-for-byte complete for the inspected files. A single long search line and both Python-indentation controls were preserved. All tested latest-commit requirements survived. The compact-search path only activated after capping in this version. It would be inaccurate to describe current rtk as always stripping source bodies, search indentation, or commit bodies. All 270 measured command executions preserved their expected exit codes; native/rtk comparisons agreed, including Cargo's failure status 101. The broad search for the real token estimator missed its formula in both native and rtk output; the task-specific context query found it. Concise command selection can improve information quality as well as size.

**Recovery changes the arithmetic.** Full-diff recovery cost 1,072 + 1,868 = 2,940 tokens, versus 1,868 for reading the native diff once. Targeted recovery could instead add only 22 tokens. Search-tail recovery cost 419 + 285 = 704 tokens, versus 612 for the native search once; an initially targeted search needed 12. Reading the pytest recovery log cost 146 + 203 = 349, still below the original 405-token default run but above the 249-token quiet/short native run. Recovery is often useful and can preserve net savings, but its cost must be included. A recovery log contains the output of the command rtk actually executed, which may already have quiet or short-traceback flags.

**Astra experiment.** Nine fresh `gpt-6-astra` agents ran at high reasoning effort, three per arm. Each received the same six questions and identical application/test inputs, plus a recording gateway. Agents had no inherited conversation and were instructed not to inspect other trials. Ordinary native and rtk agents chose commands normally; the third group additionally received an instruction to minimize output with task-specific flags, queries, and ranges. The rtk group knew the raw escape hatch. All groups were told not to interpret a truncated result as proof of absence.

The six questions covered failing tests, a migration warning, commit requirements, changed boolean settings, route authorization, and an unready deployment. Agents chose their own commands and follow-up reads. The gateway filtered supported argv commands in the rtk arm and passed native commands through in the other arms. Shell-wrapped commands and unsupported tools were passthrough. This is a documented gateway experiment, not a test of every rtk integration or automatic shell rewrite.

| Agent condition | Mean output tokens | Median | Range | Command calls | Correctness |
|---|---:|---:|---:|---:|---|
| Ordinary native | 4,903 | 4,321 | 4,235–6,153 | 9–10 | 6/6 in all 3 runs |
| RTK enabled | 5,561 | 5,761 | 5,084–5,838 | 11–13 | 6/6 in all 3 runs |
| Native, explicitly concise | 3,607 | 3,406 | 3,198–4,216 | 9–13 | 6/6 in all 3 runs |

The ordinary-native totals were 4,321 / 6,153 / 4,235; rtk totals were 5,761 / 5,838 / 5,084; concise-native totals were 4,216 / 3,198 / 3,406. All include the same 245-token task-file read. These are three repetitions of one six-question fixture, not 54 independent tasks. The ranges overlap, and one ordinary-native run read more than every rtk run. There is no meaningful population-level significance claim from this sample.

An audit found two shell-wrapper recording gaps in the concise group. A malformed pipe prevented 105 tokens of recorded search output from reaching the agent and instead displayed a 32-token shell diagnostic. A separate glob error occurred before the gateway ran and displayed an 85-token diagnostic. The table incorporates both corrections, changing that group's total by only 12 tokens. Exact diagnostics and agent-confirmed circumstances are preserved in `stream-corrections.json`; original gateway records are unchanged. The command-call column counts gateway invocations, with one additional failed pre-gateway attempt in the second concise run. Thus the report separates what the gateway captured from the corrected output displayed to agents.

All rtk agents recovered the omitted warning and the truncated diff. Some reread more than necessary, including a commit body whose required facts were already present; some reran tests instead of reading the supplied recovery log. Native agents also made inefficient choices, and the explicitly concise agents did not consistently choose the hand-optimized baseline. The measured difference reflects both filtering and the agents' adaptive command choices. Adding the recorded native command strings to the output count leaves the group ordering unchanged. Wrapper scaffolding, tool envelopes, initial instruction length, final answers, reasoning tokens, cache effects, and replay of prior context were not included, so these totals must not be called full-session token usage or billing.

Correctness was assessed against the authored fixture and actual test results, with a deterministic coverage check and manual semantic review. All required facts were correct. The grader was the same parent agent that designed the fixture; it was not blinded. These tasks specifically asked for the information at risk, making recovery more likely than in an open-ended review where an omitted warning might go unnoticed. No production code-fix success or broader reliability was measured.

**What this answers.** RTK works as an output reducer, and concise native commands do not make every filter redundant. It also removes information that can be necessary. Astra was capable of recovering that information in this pilot, sometimes consuming more command output than it would have read without filtering. An explicit concision instruction helped on average here, but the experiment did not compare older models, so it cannot establish that models have learned this behavior over time.

My practical recommendation is to keep rtk available for repetitive routine output, especially successful test runs, and use complete failure/warning output plus targeted native queries when exact values, completeness, or chronology drive the decision. The useful objective is correct task completion with fewer total tokens and retries, rather than the largest reduction on the first command response. Within an always-prefix-rtk workflow, `rtk run` and `rtk proxy` provide the raw path.

RTK typically added roughly 2–5 ms in these warm local command measurements; Git status and diff added about 12 ms because these paths do additional work. Those timings are process measurements, not model latency. The bytes/4 counter also should not be treated as exact token savings: in the failed-pytest case its byte-based reduction was 72.1%, while o200k token reduction was 64.0%, an 8.2 percentage-point difference. Applying the same estimator to two strings guarantees a byte ratio, not an invariant token ratio. RTK's documentation correctly distinguishes output reduction from session cost; its assertion that the percentage remains reliable needs that byte-ratio qualification.

**Files and reproduction.** `results.csv`, `results.json`, and `specification.json` retain all command cases, exact commands, checks, exit codes, timings, and both tokenizers. `captures/` has the first full stdout/stderr for every arm. `agent-trials/` contains tasks, dispatched instruction text, answers, and recorded command observations. `recovery/` contains actual recovery reads. `summary.json` and `agent-results.csv` expose the arithmetic. `manual-grades.json` ties manual scores to answer hashes; `stream-corrections.json` documents the two accounting corrections. `reproduction/` contains scripts and pinned dependency instructions. Timing, temporary recovery filenames, relative dates, and stochastic agent choices will vary on rerun.
