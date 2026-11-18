#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "results" / "campaign_20261118T110107Z" / "runs"
for run in ["claude-opus-5-5-medium_T3_r1", "claude-opus-5-5-medium_T3_r2"]:
    p = ROOT / run / "agent_trace.jsonl"
    rows = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print("====", run, "nlines", len(rows))
    for i, line in enumerate(rows, 1):
        if "shellToolCall" not in line or "completed" not in line:
            continue
        o = json.loads(line)
        cmd = (
            ((o.get("tool_call") or {}).get("shellToolCall") or {})
            .get("args", {})
            .get("command", "")
        )
        if any(k in cmd for k in ("make", "qemu", "cd ")):
            print(i, cmd[:200].replace("\n", " "))
