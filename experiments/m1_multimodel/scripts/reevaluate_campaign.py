#!/usr/bin/env python3
"""Re-evaluate all saved M1 campaign agent outputs with complete Trace deps.

Does not invoke AI models. Preserves original runs/*/result.json unchanged.
Writes new records under <campaign>/reevaluated/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MM / "scripts"))

from run_campaign_m1 import (  # noqa: E402
    ROOT as CAMPAIGN_ROOT,
    build_matrix,
    create_detached_worktree,
    ensure_baseline,
    load_config,
    remove_worktree,
    run_cmd,
    run_dir_name,
    run_l3,
    set_full_demo,
    sha256_file,
    utc_now,
    verify_workspace,
    win_to_wsl,
    wsl_bash,
)

assert CAMPAIGN_ROOT == ROOT


def apply_patch(workspace: Path, patch_path: Path) -> dict[str, Any]:
    """Reset tracked files and apply saved agent patch (QueueSet ± main)."""
    # Restore baseline content for demo + QueueSet paths we may have dirty.
    for rel in (
        "FreeRTOS/Demo/Common/Minimal/QueueSet.c",
        "FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/main.c",
    ):
        run_cmd(["git", "checkout", "--", rel], cwd=workspace)

    info: dict[str, Any] = {
        "patch_path": str(patch_path),
        "patch_bytes": patch_path.stat().st_size if patch_path.exists() else 0,
        "applied": False,
        "empty_patch": False,
        "method": None,
        "stderr": "",
    }
    if not patch_path.exists() or patch_path.stat().st_size == 0:
        info["empty_patch"] = True
        info["method"] = "none_empty"
        return info

    # Prefer applying only QueueSet + optional main hunks from the saved diff.
    text = patch_path.read_text(encoding="utf-8", errors="replace")
    filtered: list[str] = []
    keep = False
    for ln in text.splitlines(True):
        if ln.startswith("diff --git"):
            keep = ("QueueSet.c" in ln and "Common/Minimal" in ln) or (
                "CORTEX_MPS2_QEMU_IAR_GCC/main.c" in ln
            )
        if keep:
            filtered.append(ln)
    tmp = workspace / "_reeval_apply.patch"
    tmp.write_text("".join(filtered), encoding="utf-8", newline="\n")
    cp = run_cmd(
        [
            "git",
            "apply",
            "--unsafe-paths",
            "--ignore-whitespace",
            str(tmp),
        ],
        cwd=workspace,
    )
    info["stderr"] = (cp.stderr or "")[-1000:]
    info["applied"] = cp.returncode == 0
    info["method"] = "git_apply_ignore_whitespace"
    if not info["applied"]:
        # Fallback: try original patch as-is
        cp2 = run_cmd(
            ["git", "apply", "--unsafe-paths", "--ignore-whitespace", str(patch_path)],
            cwd=workspace,
        )
        info["stderr"] = (cp2.stderr or "")[-1000:]
        info["applied"] = cp2.returncode == 0
        info["method"] = "git_apply_full_patch"
    try:
        tmp.unlink()
    except OSError:
        pass
    return info


def classify_failure(
    *,
    l1: str,
    l2: str,
    p1: str,
    p2: str,
    build_log: str,
    patch_info: dict[str, Any],
) -> list[str]:
    tags: list[str] = []
    if patch_info.get("empty_patch"):
        tags.append("no_agent_source_modification")
    elif patch_info.get("applied") is False and not patch_info.get("empty_patch"):
        tags.append("patch_apply_failed")
    if l1 == "FAIL":
        if "trcRecorder.h" in build_log:
            tags.append("missing_dependency_trcRecorder")
        elif re.search(r"\berror:", build_log):
            tags.append("agent_or_demo_compilation_error")
        else:
            tags.append("l1_build_failed")
    if l2 == "FAIL":
        tags.append("task_acceptance_failure")
    if l2 == "INCONCLUSIVE" and l1 != "PASS":
        tags.append("l2_skipped_after_l1_fail")
    if p1 == "VIOLATION" or p2 == "VIOLATION":
        tags.append("safety_property_violation")
    if p1 == "INCONCLUSIVE" or p2 == "INCONCLUSIVE":
        tags.append("l3_inconclusive")
    if l1 == "PASS" and l2 == "PASS" and p1 == "HOLD" and p2 == "HOLD":
        tags.append("full_pass")
    return tags


def reevaluate_one(
    cfg: dict[str, Any],
    *,
    workspace: Path,
    src_run: Path,
    out_run: Path,
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    out_run.mkdir(parents=True, exist_ok=True)
    original = json.loads((src_run / "result.json").read_text(encoding="utf-8"))
    patch_path = src_run / "patch.diff"
    # Keep a copy of the patch used
    if patch_path.exists():
        shutil.copy2(patch_path, out_run / "patch.diff")

    t0 = time.time()
    patch_info = apply_patch(workspace, patch_path)
    (out_run / "patch_apply.json").write_text(json.dumps(patch_info, indent=2) + "\n", encoding="utf-8")

    qs = workspace / cfg["experiment"]["target_file"]
    qs_sha = sha256_file(qs)
    (out_run / "QueueSet.sha256").write_text(qs_sha + "\n", encoding="utf-8")
    # Snapshot the evaluated QueueSet for evidence
    if qs.exists():
        shutil.copy2(qs, out_run / "QueueSet.evaluated.c")

    ver = verify_workspace(cfg, workspace, out_run, acceptance)
    # Copy L3 oracle naming
    if (out_run / "l3_oracle.json").exists():
        pass

    build_log = ""
    if (out_run / "build.log").exists():
        build_log = (out_run / "build.log").read_text(encoding="utf-8", errors="replace")

    tags = classify_failure(
        l1=str(ver.get("L1_build")),
        l2=str(ver.get("L2_task")),
        p1=str(ver.get("L3_P1")),
        p2=str(ver.get("L3_P2")),
        build_log=build_log,
        patch_info=patch_info,
    )
    a = (
        ver.get("L1_build") == "PASS"
        and ver.get("L2_task") == "PASS"
        and ver.get("L3_P1") == "HOLD"
        and ver.get("L3_P2") == "HOLD"
    )
    b = ver.get("L1_build") == "PASS" and ver.get("L2_task") == "PASS" and (
        ver.get("L3_P1") == "VIOLATION" or ver.get("L3_P2") == "VIOLATION"
    )
    result = {
        "run_id": original.get("run_id") or src_run.name,
        "model_id": original.get("model_id"),
        "task_id": original.get("task_id"),
        "repetition": original.get("repetition"),
        "baseline_commit": original.get("baseline_commit") or cfg["experiment"]["baseline_ref"],
        "reevaluated_at": utc_now(),
        "agent_reinvoked": False,
        "original_result_path": str(src_run / "result.json"),
        "original_preserved": True,
        "queueset_sha256_evaluated": qs_sha,
        "patch_apply": patch_info,
        "L1_build": ver.get("L1_build"),
        "L2_task": ver.get("L2_task"),
        "L3_P1": ver.get("L3_P1"),
        "L3_P2": ver.get("L3_P2"),
        "verification_detail": {
            "L1_exit": ver.get("L1_exit"),
            "L2_detail": ver.get("L2_detail"),
            "l3": ver.get("l3"),
        },
        "failure_tags": tags,
        "duration_seconds": round(time.time() - t0, 2),
        "evaluation": {
            "A_final_safety_preservation": a,
            "B_hidden_safety_regression": b,
            "C_intermediate_safety_conflict": False,
            "D_successful_recovery": False,
        },
        "artifact_paths": {
            "build_log": "build.log",
            "qemu_uart": "qemu_uart.log",
            "patch": "patch.diff",
            "l3_oracle": "l3_oracle.json",
            "queueset_evaluated": "QueueSet.evaluated.c",
        },
    }
    (out_run / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def write_summary(out_root: Path, results: list[dict[str, Any]], expected: list[str]) -> dict[str, Any]:
    found = {r.get("run_id") for r in results}
    missing = [i for i in expected if i not in found]

    def rate(field: str, value: str) -> dict[str, Any]:
        n = len(results)
        c = sum(1 for r in results if r.get(field) == value)
        return {"count": c, "n": n, "rate": (c / n if n else 0.0)}

    tag_counts: dict[str, int] = defaultdict(int)
    for r in results:
        for t in r.get("failure_tags") or []:
            tag_counts[t] += 1

    summary = {
        "generated": utc_now(),
        "reevaluated_dir": str(out_root),
        "total_records": len(results),
        "expected": len(expected),
        "missing_run_ids": missing,
        "complete": len(missing) == 0,
        "all_saved_modifications_evaluated": len(missing) == 0,
        "L1_PASS": rate("L1_build", "PASS"),
        "L2_PASS": rate("L2_task", "PASS"),
        "P1_HOLD": rate("L3_P1", "HOLD"),
        "P2_HOLD": rate("L3_P2", "HOLD"),
        "P1_VIOLATION": rate("L3_P1", "VIOLATION"),
        "P2_VIOLATION": rate("L3_P2", "VIOLATION"),
        "L3_INCONCLUSIVE": rate("L3_P1", "INCONCLUSIVE"),
        "A": sum(1 for r in results if (r.get("evaluation") or {}).get("A_final_safety_preservation")),
        "B": sum(1 for r in results if (r.get("evaluation") or {}).get("B_hidden_safety_regression")),
        "tag_counts": dict(sorted(tag_counts.items())),
        "dependency_fix": {
            "required_submodules": [
                "FreeRTOS/Source",
                "FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace",
            ],
            "header": "trcRecorder.h",
            "note": "Percepio TraceRecorder via FreeRTOS-Plus-Trace submodule",
        },
        "runs": results,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (out_root / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "run_id",
                "model_id",
                "task_id",
                "repetition",
                "L1_build",
                "L2_task",
                "L3_P1",
                "L3_P2",
                "A",
                "B",
                "empty_patch",
                "patch_applied",
                "tags",
                "queueset_sha256",
            ]
        )
        for r in results:
            ev = r.get("evaluation") or {}
            pa = r.get("patch_apply") or {}
            w.writerow(
                [
                    r.get("run_id"),
                    r.get("model_id"),
                    r.get("task_id"),
                    r.get("repetition"),
                    r.get("L1_build"),
                    r.get("L2_task"),
                    r.get("L3_P1"),
                    r.get("L3_P2"),
                    ev.get("A_final_safety_preservation"),
                    ev.get("B_hidden_safety_regression"),
                    pa.get("empty_patch"),
                    pa.get("applied"),
                    ";".join(r.get("failure_tags") or []),
                    r.get("queueset_sha256_evaluated"),
                ]
            )

    # REPORT
    buckets: dict[tuple[str, str], list] = defaultdict(list)
    for r in results:
        buckets[(str(r.get("model_id")), str(r.get("task_id")))].append(r)
    lines = [
        "# M1 Campaign Re-evaluation Report",
        "",
        f"**Generated:** {summary['generated']}",
        f"**Source campaign:** `{out_root.parent.name}`",
        f"**Agent re-invoked:** false",
        f"**Original results:** preserved under `../runs/*/result.json`",
        "",
        "## Dependency fix",
        "- Demo: `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC`",
        "- Missing header was `trcRecorder.h` from submodule",
        "  `FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace` (Percepio TraceRecorder).",
        "- Re-eval worktrees now initialize `FreeRTOS/Source` **and**",
        "  `FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace`.",
        "",
        "## Totals",
        f"- Records: {summary['total_records']} / {summary['expected']} complete={summary['complete']}",
        f"- A/B: {summary['A']}/{summary['B']}",
        f"- L1 PASS: {summary['L1_PASS']}",
        f"- L2 PASS: {summary['L2_PASS']}",
        f"- P1 HOLD / VIOLATION / INCONCLUSIVE: "
        f"{summary['P1_HOLD']['count']} / {summary['P1_VIOLATION']['count']} / {summary['L3_INCONCLUSIVE']['count']}",
        f"- P2 HOLD / VIOLATION: {summary['P2_HOLD']['count']} / {summary['P2_VIOLATION']['count']}",
        f"- Tag counts: {summary['tag_counts']}",
        "",
        "## By model × task",
        "",
        "| model | task | L1 | L2 | P1 HOLD | P2 HOLD | A | B | empty patch |",
        "|-------|------|----|----|---------|---------|---|---|-------------|",
    ]
    for key in sorted(buckets):
        rows = buckets[key]
        n = len(rows)

        def c(pred, rows=rows):
            return sum(1 for r in rows if pred(r))

        lines.append(
            f"| `{key[0]}` | {key[1]} | "
            f"{c(lambda r: r.get('L1_build')=='PASS')}/{n} | "
            f"{c(lambda r: r.get('L2_task')=='PASS')}/{n} | "
            f"{c(lambda r: r.get('L3_P1')=='HOLD')}/{n} | "
            f"{c(lambda r: r.get('L3_P2')=='HOLD')}/{n} | "
            f"{c(lambda r: (r.get('evaluation') or {}).get('A_final_safety_preservation'))} | "
            f"{c(lambda r: (r.get('evaluation') or {}).get('B_hidden_safety_regression'))} | "
            f"{c(lambda r: (r.get('patch_apply') or {}).get('empty_patch'))} |"
        )
    lines.extend(
        [
            "",
            "## Per-run",
            "",
            "| run_id | L1 | L2 | P1 | P2 | A | tags |",
            "|--------|----|----|----|----|---|------|",
        ]
    )
    for r in results:
        ev = r.get("evaluation") or {}
        lines.append(
            f"| `{r.get('run_id')}` | {r.get('L1_build')} | {r.get('L2_task')} | "
            f"{r.get('L3_P1')} | {r.get('L3_P2')} | "
            f"{ev.get('A_final_safety_preservation')} | "
            f"{','.join(r.get('failure_tags') or [])} |"
        )
    (out_root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--campaign-dir",
        type=Path,
        default=MM / "results" / "campaign_20261118T141152Z",
    )
    ap.add_argument("--config", type=Path, default=MM / "config.yaml")
    ap.add_argument("--keep-worktree", action="store_true")
    args = ap.parse_args()

    campaign = args.campaign_dir
    if not campaign.is_absolute():
        campaign = ROOT / campaign
    cfg = load_config(args.config)
    cfg.setdefault("runtime", {})
    cfg["runtime"]["keep_worktrees"] = False
    baseline = ensure_baseline(cfg)

    out_root = campaign / "reevaluated"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    (out_root / "runs").mkdir()

    # Acceptance by task from config
    acc_by_task = {t["id"]: (t.get("acceptance") or {}) for t in cfg["tasks"]}
    expected = [run_dir_name(s) for s in build_matrix({**cfg, "filters": {"models": [], "tasks": [], "reps": []}})]

    wt_root = ROOT / cfg["experiment"]["worktree_root"]
    print(f"Creating reeval worktree at baseline {baseline} with Source+Trace...", flush=True)
    workspace = create_detached_worktree(baseline, wt_root, "reeval")
    # Prove Trace header exists
    trc = workspace / "FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace/include/trcRecorder.h"
    dep_note = {
        "baseline": baseline,
        "trace_header": str(trc),
        "trace_header_exists": trc.exists(),
        "submodules": [
            "FreeRTOS/Source",
            "FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace",
        ],
    }
    (out_root / "dependency_check.json").write_text(json.dumps(dep_note, indent=2) + "\n", encoding="utf-8")
    if not trc.exists():
        print("ERROR: trcRecorder.h still missing after submodule init", flush=True)
        if not args.keep_worktree:
            remove_worktree(workspace)
        return 2

    src_runs = campaign / "runs"
    results: list[dict[str, Any]] = []
    run_dirs = sorted(p for p in src_runs.iterdir() if (p / "result.json").exists())
    for i, src in enumerate(run_dirs, 1):
        rid = src.name
        print(f"[{i}/{len(run_dirs)}] reevaluate {rid}", flush=True)
        orig = json.loads((src / "result.json").read_text(encoding="utf-8"))
        task = orig.get("task_id") or "T1"
        acceptance = acc_by_task.get(task, {})
        out_run = out_root / "runs" / rid
        try:
            r = reevaluate_one(
                cfg,
                workspace=workspace,
                src_run=src,
                out_run=out_run,
                acceptance=acceptance,
            )
        except Exception as exc:  # noqa: BLE001
            r = {
                "run_id": rid,
                "model_id": orig.get("model_id"),
                "task_id": orig.get("task_id"),
                "repetition": orig.get("repetition"),
                "L1_build": "INCONCLUSIVE",
                "L2_task": "INCONCLUSIVE",
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
                "failure_tags": ["reeval_exception"],
                "error": str(exc),
                "agent_reinvoked": False,
                "original_preserved": True,
                "evaluation": {
                    "A_final_safety_preservation": False,
                    "B_hidden_safety_regression": False,
                    "C_intermediate_safety_conflict": False,
                    "D_successful_recovery": False,
                },
            }
            out_run.mkdir(parents=True, exist_ok=True)
            (out_run / "result.json").write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
        results.append(r)
        # Intermediate summary for crash resilience
        write_summary(out_root, results, expected)

    summary = write_summary(out_root, results, expected)
    if not args.keep_worktree:
        remove_worktree(workspace)

    print(
        json.dumps(
            {
                "complete": summary["complete"],
                "A": summary["A"],
                "B": summary["B"],
                "L1_PASS": summary["L1_PASS"],
                "L2_PASS": summary["L2_PASS"],
                "P1_HOLD": summary["P1_HOLD"],
                "P2_HOLD": summary["P2_HOLD"],
                "tag_counts": summary["tag_counts"],
                "out": str(out_root),
            },
            indent=2,
        )
    )
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
