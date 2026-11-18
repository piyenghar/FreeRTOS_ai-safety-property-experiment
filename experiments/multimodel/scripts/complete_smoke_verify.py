#!/usr/bin/env python3
"""Complete L1/L2/L3 for an existing smoke worktree without re-invoking the agent."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_matrix import (  # noqa: E402
    capture_diff,
    expand_prompt,
    load_config,
    parse_agent_corrections,
    run_verification,
    utc_now,
    MM,
)

CAMPAIGN = ROOT / "experiments/multimodel/results/campaign_20261118T104835Z"
RUN_ID = "m2_claude-opus-5-5-medium_T1_r1"
WT = ROOT / "experiments/multimodel/wt/r01"
RUN_DIR = CAMPAIGN / RUN_ID
BASELINE = "8c62b75701d9757dff84de4ed1ec3b1a63d5d400"


def main() -> int:
    cfg = load_config(MM / "config.yaml")
    agent_log = RUN_DIR / "agent.stream.jsonl"
    prompt_path = MM / "prompts/t1_logging.md"
    acceptance = cfg["tasks"][0]["acceptance"]

    meta = {
        "run_id": RUN_ID,
        "slot": "r01",
        "model_id": "claude-opus-5-5-medium",
        "model_display": "Claude Opus 5.5 Medium",
        "cli_model_id": "claude-opus-5-5-medium",
        "task_id": "T1",
        "task_name": "logging",
        "rep": 1,
        "baseline_ref": BASELINE,
        "worktree": str(WT),
        "branch": "exp/r01-m2_claude-opus-5-5-medium_T1_r1",
        "dry_run": False,
        "note": "Verification completed after agent phase; L1 initially failed on native Windows make (FileNotFound).",
        "agent": {
            "log": str(agent_log),
            "reused_existing_agent_output": True,
        },
        "corrections": parse_agent_corrections(agent_log),
        "diff": capture_diff(
            WT, BASELINE, RUN_DIR / "source.diff", RUN_DIR / "source.diffstat.txt"
        ),
        "verification": run_verification(
            cfg,
            workspace=WT,
            run_dir=RUN_DIR,
            acceptance=acceptance,
            task_id="T1",
        ),
        "prompt_sha_note": "see prompt_expanded.md",
        "finished_at": utc_now(),
    }
    l1 = meta["verification"]["L1"].get("status")
    l2 = meta["verification"]["L2"].get("status")
    l3 = meta["verification"]["L3"].get("status")
    meta["status"] = "PASS" if {l1, l2, l3} <= {"PASS"} else "FAIL"
    (RUN_DIR / "result.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    summary = {
        "campaign_id": "20261118T104835Z",
        "dry_run": False,
        "baseline_ref": BASELINE,
        "total": 1,
        "by_status": {meta["status"]: 1},
        "results": [meta],
        "agent_logged_in": True,
        "finished_at": utc_now(),
        "smoke": True,
        "remaining_26_not_executed": True,
    }
    (CAMPAIGN / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": meta["status"], "L1": l1, "L2": l2, "L3": l3}, indent=2))
    return 0 if meta["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
