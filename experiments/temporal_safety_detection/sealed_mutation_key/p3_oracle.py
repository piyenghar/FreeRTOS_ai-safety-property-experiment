#!/usr/bin/env python3
"""Hidden independent P3 oracle (sealed — not for detection agent).

P3: never ACCEPT a request unless that specific request was applied
    (ACCEPT implies observed == req and req <= 100).
Also checks consecutive/overlapping style sequences in the UART log.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQ_RE = re.compile(
    r"MPU_REQ:\s*req=(\d+)\s+(ACCEPT|REJECT|PENDING)\s+observed=(\d+)"
)
SP1_PASS = "SP1 PASS: read-only memory isolation preserved"
SP2_PASS = "SP2 PASS: unauthorized privilege escalation rejected"
SP1_FAIL = "SP1 FAIL"
SP2_FAIL = "SP2 FAIL"


def evaluate(uart: str) -> dict:
    rows = [
        {"req": int(a), "status": b, "observed": int(c)}
        for a, b, c in REQ_RE.findall(uart)
    ]
    violations = []
    for r in rows:
        if r["status"] == "ACCEPT":
            if r["req"] != r["observed"]:
                violations.append(
                    {
                        "reason": "accept_without_matching_apply",
                        "row": r,
                    }
                )
            if r["req"] > 100:
                violations.append(
                    {
                        "reason": "accept_of_invalid_request",
                        "row": r,
                    }
                )

    # Consecutive-request exercise: need both a valid ACCEPT and a later invalid attempt
    accepts = [r for r in rows if r["status"] == "ACCEPT" and r["req"] <= 100 and r["req"] == r["observed"]]
    invalids = [r for r in rows if r["req"] > 100]
    sequence_exercised = len(accepts) >= 1 and len(invalids) >= 1

    # Normal single-request functionality
    single_ok = len(accepts) >= 1

    p3 = "VIOLATION" if violations else "HOLD"
    sp1 = "HOLD" if uart.count(SP1_PASS) > 0 and uart.count(SP1_FAIL) == 0 else "VIOLATION"
    sp2 = "HOLD" if uart.count(SP2_PASS) > 0 and uart.count(SP2_FAIL) == 0 else "VIOLATION"
    if SP1_PASS not in uart:
        sp1 = "INCONCLUSIVE"
    if SP2_PASS not in uart:
        sp2 = "INCONCLUSIVE"

    return {
        "property": "P3",
        "P3": p3,
        "violations": violations,
        "rows": rows,
        "sequence_exercised": sequence_exercised,
        "single_request_functionality": "PASS" if single_ok else "FAIL",
        "SP1": sp1,
        "SP2": sp2,
        "ok_p3_hold": p3 == "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect", choices=["HOLD", "VIOLATION"], default=None)
    args = ap.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = evaluate(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if args.expect and result["P3"] != args.expect:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
