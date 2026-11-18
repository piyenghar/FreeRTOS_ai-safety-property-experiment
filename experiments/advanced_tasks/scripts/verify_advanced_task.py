#!/usr/bin/env python3
"""Verify one advanced task (L2 + L3) for a workspace target file.

Intended campaign hook. Does not invoke AI models.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADV / "l2"))
from check_advanced_l2 import check_m1_r4, check_m2_e4, check_m2_r4  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True, choices=["M1-R4", "M1-E4", "M2-R4", "M2-E4"])
    ap.add_argument("--src", type=Path, required=True, help="QueueSet.c or mpu_demo.c")
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--uart", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    src = args.src.read_text(encoding="utf-8", errors="replace")
    baseline = args.baseline.read_text(encoding="utf-8", errors="replace")
    uart = args.uart.read_text(encoding="utf-8", errors="replace") if args.uart else ""

    if args.task == "M1-R4":
        l2 = check_m1_r4(src=src, baseline_src=baseline)
    elif args.task == "M1-E4":
        cp = subprocess.run(
            [
                sys.executable,
                str(ADV / "scripts/run_m1_e4_l2_against_queueset.py"),
                "--queueset",
                str(args.src),
                "--out-dir",
                str(args.out_dir / "m1_e4_l2"),
            ],
            text=True,
            capture_output=True,
        )
        jpath = args.out_dir / "m1_e4_l2/m1_e4_l2.json"
        l2 = json.loads(jpath.read_text(encoding="utf-8")) if jpath.exists() else {
            "verdict": "FAIL",
            "failure_reasons": ["m1_e4_runner_failed"],
            "stderr": (cp.stderr or "")[-1000:],
        }
    elif args.task == "M2-R4":
        l2 = check_m2_r4(src=src, baseline_src=baseline, uart_text=uart)
    else:
        l2 = check_m2_e4(src=src, uart_text=uart)

    l3: dict = {}
    if args.task.startswith("M1"):
        cp = subprocess.run(
            [
                sys.executable,
                str(ROOT / "experiments/m1_multimodel/scripts/run_l3_against_queueset.py"),
                "--queueset",
                str(args.src),
                "--out-dir",
                str(args.out_dir / "l3"),
            ],
            text=True,
            capture_output=True,
        )
        sp = args.out_dir / "l3/l3_oracle.json"
        l3 = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {"ok": False}
    elif args.uart and args.uart.exists() and uart.strip():
        outj = args.out_dir / "l3_oracle.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "experiments/verification/M2/scripts/l3_pilot_oracle.py"),
                "--mode",
                "pilot",
                "--pilot",
                "t2",
                "--control",
                "pos",
                "--log",
                str(args.uart),
                "--out",
                str(outj),
                "--l1",
                "PASS",
                "--source-note",
                f"verify_advanced_task:{args.task}",
            ],
            text=True,
            capture_output=True,
        )
        l3 = json.loads(outj.read_text(encoding="utf-8")) if outj.exists() else {}

    payload = {
        "task": args.task,
        "L2": l2,
        "L3": l3,
        "src": str(args.src.resolve()),
    }
    (args.out_dir / "verify.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if l2.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
