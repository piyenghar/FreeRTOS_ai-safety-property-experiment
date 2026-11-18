#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "results" / "campaign_20261118T110107Z" / "runs"


def show(run: str, lines: list[int]) -> None:
    p = ROOT / run / "agent_trace.jsonl"
    rows = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for ln in lines:
        if ln < 1 or ln > len(rows):
            print(run, "line", ln, "OOB")
            continue
        o = json.loads(rows[ln - 1])
        tc = o.get("tool_call") or {}
        shell = tc.get("shellToolCall") or {}
        args = shell.get("args") or {}
        cmd = (args.get("command") or "")[:700]
        res = shell.get("result") or {}
        blob = json.dumps(res)
        m = re.search(r'"exitCode"\s*:\s*(-?\d+)', blob)
        # Prefer interleavedOutput / stdout fields if present as plain strings
        out = ""
        for key in ("interleavedOutput", "stdout", "stderr"):
            if isinstance(res, dict) and key in res and isinstance(res[key], str):
                out = res[key]
                break
            # nested success/failure shapes
            for nest in (res.get("success"), res.get("failure"), res.get("result")):
                if isinstance(nest, dict) and key in nest and isinstance(nest[key], str):
                    out = nest[key]
                    break
        if not out:
            sm = re.search(r'"(?:stdout|interleavedOutput)"\s*:\s*"((?:\\.|[^"\\])*)"', blob)
            if sm:
                out = bytes(sm.group(1), "utf-8").decode("unicode_escape")
        print("====", run, "line", ln, "type", o.get("type"), o.get("subtype"))
        print("CMD:", cmd)
        print("EXIT:", m.group(1) if m else None)
        print("OUT:", (out or "")[:900])
        print()


show("claude-opus-5-5-medium_T2_r2", [210, 213, 214, 230, 250])
show("claude-opus-5-5-medium_T3_r1", [80, 82, 83, 95, 110])
show("claude-opus-5-5-medium_T3_r2", [100, 105, 106, 120, 140])
show("gpt-5.6-sol-medium_T2_r1", [650, 657, 658, 670])
show("gpt-5.6-sol-medium_T2_r2", [1245, 1253, 1254, 1265])
