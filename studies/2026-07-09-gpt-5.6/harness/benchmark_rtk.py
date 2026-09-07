#!/usr/bin/env python3
"""Reproducible RTK output benchmark using the GPT-5 tokenizer family."""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import tiktoken


ROOT = Path(__file__).resolve().parent.parent
RTK_REPO = ROOT / "work" / "rtk-src"
FIXTURE = ROOT / "work" / "benchmark-fixture"
VENV_BIN = ROOT / "work" / "bench-venv" / "bin"
RTK_HOME = ROOT / "work" / "rtk-home"
RTK = shutil.which("rtk")
ENCODING = tiktoken.encoding_for_model("gpt-5")


@dataclass(frozen=True)
class Case:
    name: str
    goal: str
    cwd: Path
    ordinary: list[str]
    concise: list[str]
    filtered: list[str]
    markers: tuple[str, ...] = ()


def raw(*args: str) -> list[str]:
    return [RTK, "proxy", *args]


def filtered(*args: str) -> list[str]:
    return [RTK, *args]


def run(command: list[str], cwd: Path) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(RTK_HOME),
            "PATH": f"{VENV_BIN}:{env['PATH']}",
            "NO_COLOR": "1",
            "TERM": "dumb",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - started) * 1000
    # Both streams are returned to an agent by its shell tool, so count both.
    output = proc.stdout + proc.stderr
    return {
        "command": command,
        "exit_code": proc.returncode,
        "elapsed_ms": round(elapsed_ms, 2),
        "characters": len(output),
        "tokens": len(ENCODING.encode(output)),
        # RTK's Rust `text.len()` counts UTF-8 bytes, then divides by four.
        "rtk_estimated_tokens": (len(output.encode("utf-8")) + 3) // 4,
        "output": output,
    }


def savings(before: int, after: int) -> float:
    return round((1 - after / before) * 100, 1) if before else 0.0


def main() -> None:
    cases = [
        Case(
            "git_log",
            "scan the latest 20 commit subjects",
            RTK_REPO,
            raw("git", "log", "-n", "20"),
            raw("git", "log", "--oneline", "-n", "20"),
            filtered("git", "log", "-n", "20"),
        ),
        Case(
            "git_show",
            "understand how checkout support was implemented",
            RTK_REPO,
            raw("git", "show", "--no-color", "--format=fuller", "bb01d6c"),
            raw("git", "show", "--stat", "--oneline", "--no-color", "bb01d6c"),
            filtered("git", "show", "bb01d6c"),
            (
                "fn checkout_new_branch_arg",
                "fn checkout_branch_arg",
                "git_checkout_dirty_tree_error_keeps_file_list",
            ),
        ),
        Case(
            "directory_listing",
            "inventory source files under src/cmds",
            RTK_REPO,
            raw("find", "src/cmds", "-type", "f"),
            raw("rg", "--files", "src/cmds"),
            filtered("find", "src/cmds", "-type", "f"),
            ("gh_cmd.rs", "pytest_cmd.rs", "cargo_cmd.rs", "json_cmd.rs"),
        ),
        Case(
            "code_search",
            "locate files containing unwrap calls",
            RTK_REPO,
            raw("rg", "-n", "unwrap", "src"),
            raw("rg", "-l", "unwrap", "src"),
            filtered("rg", "-n", "unwrap", "src"),
        ),
        Case(
            "json",
            "inspect JSON while retaining exact values",
            FIXTURE,
            raw("jq", ".", "adversarial.json"),
            raw("jq", "-c", ".", "adversarial.json"),
            filtered("json", "adversarial.json"),
            ("CRITICAL_REGION_us-west-2", "payments-production"),
        ),
        Case(
            "long_search_line",
            "extract the complete API_ENDPOINT value",
            FIXTURE,
            raw("rg", "-n", "NEEDLE", "adversarial.txt"),
            raw("rg", "-n", "^API_ENDPOINT=", "adversarial.txt"),
            filtered("rg", "-n", "^API_ENDPOINT=", "adversarial.txt"),
            ("CRITICAL_REGION_us-west-2",),
        ),
        Case(
            "pytest_pass",
            "verify a passing parametrized test group",
            FIXTURE,
            raw("pytest", "test_sample.py::test_bulk_success"),
            raw("pytest", "-q", "--tb=short", "test_sample.py::test_bulk_success"),
            filtered("pytest", "test_sample.py::test_bulk_success"),
            ("60 passed",),
        ),
        Case(
            "pytest_fail",
            "diagnose three independent test failures",
            FIXTURE,
            raw("pytest"),
            raw("pytest", "-q", "--tb=short"),
            filtered("pytest"),
            (
                "req-causal-marker-7391",
                "NoneType",
                "viewer",
                "admin",
                "db-primary.internal:5432",
                "db-replica.internal:5432",
                "legacy_mode expires on 2026-09-01",
            ),
        ),
    ]

    report = {
        "rtk_version": subprocess.run(
            [RTK, "--version"], text=True, capture_output=True
        ).stdout.strip(),
        "tokenizer": ENCODING.name,
        "cases": [],
    }

    for case in cases:
        variants = {
            "ordinary": run(case.ordinary, case.cwd),
            "concise": run(case.concise, case.cwd),
            "rtk": run(case.filtered, case.cwd),
        }
        ordinary_tokens = variants["ordinary"]["tokens"]
        concise_tokens = variants["concise"]["tokens"]
        rtk_tokens = variants["rtk"]["tokens"]
        case_result = {
            "name": case.name,
            "goal": case.goal,
            "tokens": {key: value["tokens"] for key, value in variants.items()},
            "characters": {key: value["characters"] for key, value in variants.items()},
            "rtk_estimated_tokens": {
                key: value["rtk_estimated_tokens"] for key, value in variants.items()
            },
            "exit_codes": {key: value["exit_code"] for key, value in variants.items()},
            "elapsed_ms": {key: value["elapsed_ms"] for key, value in variants.items()},
            "savings_vs_ordinary_pct": {
                "concise": savings(ordinary_tokens, concise_tokens),
                "rtk": savings(ordinary_tokens, rtk_tokens),
            },
            "rtk_vs_concise_pct": savings(concise_tokens, rtk_tokens),
            "marker_retention": {
                variant: {
                    marker: marker in result["output"] for marker in case.markers
                }
                for variant, result in variants.items()
            },
            "commands": {
                key: value["command"] for key, value in variants.items()
            },
        }

        if case.name == "git_log":
            expected = subprocess.run(
                [RTK, "proxy", "git", "log", "--format=%s", "-n", "20"],
                cwd=case.cwd,
                env={**os.environ, "NO_COLOR": "1"},
                text=True,
                capture_output=True,
            ).stdout.splitlines()
            case_result["subject_retention"] = {
                variant: {
                    "retained": sum(subject in result["output"] for subject in expected),
                    "expected": len(expected),
                }
                for variant, result in variants.items()
            }

        if case.name == "code_search":
            expected_paths = {
                line.split(":", 1)[0]
                for line in variants["ordinary"]["output"].splitlines()
                if ":" in line
            }
            case_result["matching_file_retention"] = {
                variant: {
                    "retained": sum(path in result["output"] for path in expected_paths),
                    "expected": len(expected_paths),
                }
                for variant, result in variants.items()
            }
        report["cases"].append(case_result)

        if os.environ.get("RTK_BENCH_FULL") and case.name in {
            "json",
            "long_search_line",
            "pytest_fail",
        }:
            case_result["outputs"] = {
                key: value["output"] for key, value in variants.items()
            }

    totals = {
        variant: sum(case["tokens"][variant] for case in report["cases"])
        for variant in ("ordinary", "concise", "rtk")
    }
    report["totals"] = totals
    estimated_totals = {
        variant: sum(
            case["rtk_estimated_tokens"][variant] for case in report["cases"]
        )
        for variant in ("ordinary", "concise", "rtk")
    }
    report["rtk_estimated_totals"] = estimated_totals
    report["total_savings_vs_ordinary_pct"] = {
        "concise": savings(totals["ordinary"], totals["concise"]),
        "rtk": savings(totals["ordinary"], totals["rtk"]),
    }
    report["total_rtk_vs_concise_pct"] = savings(totals["concise"], totals["rtk"])
    report["estimated_total_savings_vs_ordinary_pct"] = {
        "concise": savings(estimated_totals["ordinary"], estimated_totals["concise"]),
        "rtk": savings(estimated_totals["ordinary"], estimated_totals["rtk"]),
    }
    report["median_savings_vs_ordinary_pct"] = {
        variant: round(
            statistics.median(
                case["savings_vs_ordinary_pct"][variant] for case in report["cases"]
            ),
            1,
        )
        for variant in ("concise", "rtk")
    }
    report["median_rtk_vs_concise_pct"] = round(
        statistics.median(case["rtk_vs_concise_pct"] for case in report["cases"]),
        1,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
