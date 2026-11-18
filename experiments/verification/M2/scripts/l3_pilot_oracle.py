#!/usr/bin/env python3
"""Host-side SP1/SP2 (+ pilot L2) oracle for M2 verification UART logs.

Verification-only tool: lives under experiments/verification/M2/scripts.
Does not modify FreeRTOS demo or pilot sources.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SP1_PASS = "SP1 PASS: read-only memory isolation preserved"
SP1_FAIL = "SP1 FAIL: read-only memory isolation violated"
SP2_PASS = "SP2 PASS: unauthorized privilege escalation rejected"
SP2_FAIL = "SP2 FAIL: privilege containment violated"

L3_SP1_HOLD = "L3_SP1_ORACLE: HOLD"
L3_SP1_VIOL = "L3_SP1_ORACLE: VIOLATION_DETECTED"
L3_SP2_HOLD = "L3_SP2_ORACLE: HOLD"
L3_SP2_VIOL = "L3_SP2_ORACLE: VIOLATION_DETECTED"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def count_sub(text: str, needle: str) -> int:
    return text.count(needle)


def evaluate_standalone(text: str, prop: str, control: str) -> dict:
    if prop == "sp1":
        holds = count_sub(text, L3_SP1_HOLD)
        viols = count_sub(text, L3_SP1_VIOL)
    else:
        holds = count_sub(text, L3_SP2_HOLD)
        viols = count_sub(text, L3_SP2_VIOL)

    if control == "pos":
        verdict = "PASS" if holds > 0 and viols == 0 else "FAIL"
        expect = "HOLD"
    else:
        verdict = "PASS" if viols > 0 and holds == 0 else "FAIL"
        expect = "VIOLATION_DETECTED"

    return {
        "kind": "standalone_oracle_firmware",
        "property": prop,
        "control": control,
        "expect": expect,
        "hold_count": holds,
        "violation_count": viols,
        "verdict": verdict,
    }


def evaluate_pilot_uart(text: str, pilot: str, control: str) -> dict:
    sp1_pass = count_sub(text, SP1_PASS)
    sp1_fail = count_sub(text, SP1_FAIL)
    sp2_pass = count_sub(text, SP2_PASS)
    sp2_fail = count_sub(text, SP2_FAIL)
    t1 = count_sub(text, "T1_LOG: MPU test cycle completed")
    t3_cycles = [int(x) for x in re.findall(r"T3_CYCLE:\s*(\d+)", text)]

    # L3: independent host rules on pilot UART evidence.
    # Positive: require PASS evidence and zero FAIL lines for each property.
    # Negative (weakened RO region): require SP1 FAIL (or zero SP1 PASS).
    if control == "pos":
        l3_sp1 = "HOLD" if sp1_pass > 0 and sp1_fail == 0 else "VIOLATION_DETECTED"
        l3_sp2 = "HOLD" if sp2_pass > 0 and sp2_fail == 0 else "VIOLATION_DETECTED"
        l3_ok = l3_sp1 == "HOLD" and l3_sp2 == "HOLD"
    else:
        # Pilot-derived SP1 negative control: isolation must appear violated.
        l3_sp1 = (
            "VIOLATION_DETECTED"
            if (sp1_fail > 0 or sp1_pass == 0)
            else "HOLD"
        )
        l3_sp2 = "NOT_EVALUATED_IN_SP1_NEG"
        l3_ok = l3_sp1 == "VIOLATION_DETECTED"

    # L2: pilot-specific acceptance (positive runs only).
    if control != "pos":
        l2 = {"applicable": False, "verdict": "N/A"}
    elif pilot == "t1":
        l2 = {
            "applicable": True,
            "criterion": "T1_LOG present each observed cycle family",
            "t1_log_count": t1,
            "verdict": "PASS" if t1 > 0 else "FAIL",
        }
    elif pilot == "t2":
        l2 = {
            "applicable": True,
            "criterion": "behaviour-preserving: SP1/SP2 PASS with no FAIL",
            "verdict": "PASS"
            if sp1_pass > 0 and sp2_pass > 0 and sp1_fail == 0 and sp2_fail == 0
            else "FAIL",
        }
    elif pilot == "t3":
        mono = t3_cycles == list(range(1, len(t3_cycles) + 1)) if t3_cycles else False
        l2 = {
            "applicable": True,
            "criterion": "T3_CYCLE increments from 1",
            "t3_cycles": t3_cycles,
            "verdict": "PASS" if mono and len(t3_cycles) >= 1 else "FAIL",
        }
    else:
        l2 = {"applicable": False, "verdict": "FAIL", "error": f"unknown pilot {pilot}"}

    return {
        "kind": "pilot_mpu_demo_uart",
        "pilot": pilot,
        "control": control,
        "counts": {
            "sp1_pass": sp1_pass,
            "sp1_fail": sp1_fail,
            "sp2_pass": sp2_pass,
            "sp2_fail": sp2_fail,
            "t1_log": t1,
            "t3_cycles": t3_cycles,
        },
        "L3_SP1": l3_sp1,
        "L3_SP2": l3_sp2,
        "L3_verdict": "PASS" if l3_ok else "FAIL",
        "L2": l2,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["standalone", "pilot"], required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--control", choices=["pos", "neg"], required=True)
    ap.add_argument("--property", choices=["sp1", "sp2"])
    ap.add_argument("--pilot", choices=["t1", "t2", "t3"])
    ap.add_argument("--l1", choices=["PASS", "FAIL"], default="PASS")
    ap.add_argument("--mpu-demo-sha256", default="")
    ap.add_argument("--source-note", default="")
    args = ap.parse_args()

    text = read_text(args.log)
    if args.mode == "standalone":
        if not args.property:
            print("--property required for standalone mode", file=sys.stderr)
            return 2
        body = evaluate_standalone(text, args.property, args.control)
    else:
        if not args.pilot:
            print("--pilot required for pilot mode", file=sys.stderr)
            return 2
        body = evaluate_pilot_uart(text, args.pilot, args.control)

    result = {
        "L1_build": args.l1,
        "source_note": args.source_note,
        "mpu_demo_sha256": args.mpu_demo_sha256,
        "uart_log": str(args.log),
        **body,
    }
    if args.mode == "pilot" and args.control == "pos":
        result["L2_verdict"] = body["L2"].get("verdict", "FAIL")
    elif args.mode == "pilot":
        result["L2_verdict"] = "N/A"
    else:
        result["L2_verdict"] = "N/A"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
