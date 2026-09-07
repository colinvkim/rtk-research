# Does rtk actually save tokens?

Experiment date: 2026-07-09

## Verdict

Yes—rtk is a real and often substantial output compressor. Across eight cases, rtk reduced actual GPT-family tokens by a median of **70.2%** relative to ordinary commands. The byte-weighted total was **78.3%**, broadly consistent with the project's advertised 60–90% range.

But it is not lossless compression. In tasks requiring exact values, exhaustive results, or complete causal context, rtk omitted information that the task needed. The good news is that omissions were usually signposted (`+66 more files`, `...`, or a saved-full-output hint), and failed-command output was recoverable from a tee log.

A task-aware concise-command baseline was extremely competitive. It reduced ordinary output by a median of **59.4%**, versus rtk's 70.2%. Across all tokens it did better—94.2% versus 78.3%—but that total is dominated by one huge search, and one tiny result (`git show --stat`) was too terse to satisfy its task. The practical winner is a hybrid: let the model choose narrow native flags first, then use rtk for inherently noisy output.

## What rtk claims and how it works

rtk is a command-aware proxy. It runs the underlying tool, then filters with command-specific strategies: grouping, truncation, deduplication, and boilerplate removal. The project advertises 60–90% output-token savings and says it supports more than 100 command forms. It also preserves child exit codes, falls back to raw output when parsing fails, and can save full failed output for recovery. See the [project README](https://github.com/rtk-ai/rtk), [architecture](https://github.com/rtk-ai/rtk/blob/develop/docs/contributing/ARCHITECTURE.md), and [coverage guide](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/resources/what-rtk-covers.md).

The current release was [v0.43.0, published 2026-06-28](https://github.com/rtk-ai/rtk/releases/tag/v0.43.0), which is the installed binary tested here. Its release notes include a “never-worse output guard.” That guard prevents filtered output from being larger than raw output; it does not guarantee semantic completeness.

rtk's analytics estimate tokens as UTF-8 bytes divided by four. The project itself describes that as a heuristic and recommends a real tokenizer for precise counts in its [gain guide](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/analytics/gain.md#how-token-estimation-works).

## Method

Each task had three variants:

1. **Ordinary** — the obvious unoptimized command.
2. **Concise** — a task-aware native command a capable current agent could choose.
3. **rtk** — the ordinary intent routed through rtk 0.43.0.

I counted combined stdout and stderr because both reach an agent's context. Counts use `tiktoken` 0.13.0's GPT-5 mapping, `o200k_base`. This is a better proxy than bytes/4, though it is not a published guarantee that every GPT-5.6-family endpoint uses precisely the same tokenizer.

The workload used the live rtk repository plus synthetic JSON and pytest fixtures containing sentinel details. All variants' exit codes were checked; rtk preserved the underlying success/failure status in every case.

## Results

| Task | Ordinary | Concise | rtk | rtk saved vs ordinary | Initial-output fidelity |
|---|---:|---:|---:|---:|---|
| Scan 20 Git subjects | 2,863 | 373 | 978 | 65.8% | All retained; rtk also kept author/relative time |
| Understand a 321-line Git change | 4,159 | 96 | 3,469 | 16.6% | rtk partial; concise stat was inadequate |
| Inventory 86 source files | 831 | 831 | 196 | 76.4% | rtk omitted 36 filenames |
| Locate files among 1,545 search matches | 38,161 | 708 | 5,219 | 86.3% | concise retained 82/82 paths; rtk retained 16/82 |
| Inspect exact JSON values | 99 | 80 | 56 | 43.4% | rtk truncated a decisive string suffix |
| Extract one long search value | 72 | 64 | 64 | 11.1% | all retained the complete value |
| Confirm 60 passing tests | 101 | 17 | 7 | 93.1% | all retained `60 passed` |
| Diagnose 3 failing tests | 884 | 570 | 225 | 74.5% | rtk omitted several causal details; full log recoverable |
| **Total** | **47,170** | **2,739** | **10,214** | **78.3%** | search-heavy total |

Median savings versus ordinary output:

- Task-aware concise commands: **59.4%**
- rtk: **70.2%**

Median rtk saving relative to the concise baseline: **15.0%**. That median hides a split result: rtk won clearly on test summaries, JSON length, and directory orientation; native task-aware flags won decisively on Git history and file-location search; the exact-value grep tied.

## What got obscured

### Exhaustive search and inventory

`rtk rg -n unwrap src` reported `1545 matches in 82 files`, but displayed results from only 16 files and ended with `+66 more files`. The task-aware `rg -l unwrap src` used 708 tokens and retained all 82 paths. Here the model's understanding of the goal beat generic post-processing by both fidelity and size.

Likewise, `rtk find` compressed 86 filenames to a 196-token tree, but ended at `+36 more`; sentinel files such as `pytest_cmd.rs`, `cargo_cmd.rs`, and `json_cmd.rs` disappeared. This is good orientation output, but not an inventory.

### Exact JSON values

rtk reduced a long `deployment_target` value to:

```text
deployment_target: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx..."
```

The omitted suffix was `CRITICAL_REGION_us-west-2`. Compact `jq -c` retained it and cost only 24 more tokens than rtk. If values—not merely schema—matter, rtk's JSON filter is unsafe as the only read.

### Failure diagnosis

The filtered pytest output preserved all three failing test names, locations, the first exception type, and one string comparison. It omitted:

- the chained exception's request ID;
- the expected/actual role and scope values;
- the deprecation warning and its deadline.

rtk printed a path to its saved full pytest log. I verified that the log contained every omitted sentinel, so the loss was recoverable without rerunning the tests. Recovery still costs a second tool call and more context, and it only helps if the agent notices and follows the hint.

### Large diffs

For a 321-line commit, rtk retained much of the implementation and two of three probed code landmarks, then truncated 77 lines from a large function. It ended with a full-diff recovery command. This was much more informative than `git show --stat`, but only 16.6% smaller than raw output.

## Are rtk's token numbers credible?

Broadly, but they are estimates.

Across this workload, bytes/4 estimated 41,208 ordinary tokens and 8,459 rtk tokens, implying 79.5% savings. Actual `o200k_base` counts were 47,170 and 10,214, implying 78.3% savings. Thus:

- the aggregate savings percentage was overstated by **1.2 percentage points**;
- absolute ordinary tokens were underestimated by **12.6%**;
- absolute filtered tokens were underestimated by **17.2%**.

The headline percentage survived independent tokenization, but `rtk gain` should be treated as trend telemetry rather than billing-grade measurement.

## Have newer LLMs made rtk unnecessary?

Not entirely, but they reduce its marginal value.

The concise baseline shows what task-aware command selection can accomplish: `git log --oneline`, `rg -l`, `pytest -q --tb=short`, and `jq -c` often eliminate noise before it exists. This is safer than generating a broad result and asking a generic filter to guess what matters. The concise baseline satisfied seven of eight task definitions; its failure was intentionally illustrative—`git show --stat` was tiny because it threw away the implementation the task asked about.

This run does **not** establish a historical learning curve across model generations. It tests a capable current agent's hand-selected commands, not a randomized, blinded comparison of GPT-5.6 against older models. What it does establish is that rtk should be compared with task-aware commands, not only with naive defaults; against that stronger baseline, the advantage is smaller and highly workload-dependent.

## Recommended operating policy

Use rtk by default for:

- passing-test summaries;
- noisy build/install progress;
- repetitive logs;
- Git push/pull success chatter;
- first-pass repository orientation.

Prefer native concise commands or passthrough for:

- exhaustive searches and file inventories;
- exact JSON/API values;
- full diffs and generated artifacts;
- debugging where chained exceptions, locals, warnings, or ordering matter;
- any output that is itself the deliverable.

Teach the agent a simple escalation rule: when rtk prints `+N more`, an ellipsis, `[full output: ...]`, or `[full diff: ...]`, and the task asks for exactness or completeness, read the full result immediately.

## Limitations

This is an eight-case local benchmark on macOS, one real Rust repository, and synthetic pytest/JSON adversarial fixtures. It does not cover Docker, Kubernetes, cloud CLIs, JavaScript package managers, or long-running builds. The totals are not a population estimate, and the code-search case dominates the weighted aggregate. End-to-end task correctness and the token cost of recovery calls were evaluated qualitatively, not through a large model-scored trial.

The project's own changelog shows why continued adversarial testing matters: recent versions fixed dropped AWS values, truncated Helm output, incomplete .NET failures, Git status/exit-code issues, and curl binary corruption. See the [changelog](https://github.com/rtk-ai/rtk/blob/develop/CHANGELOG.md) and [v0.43.0 release notes](https://github.com/rtk-ai/rtk/releases/tag/v0.43.0).
