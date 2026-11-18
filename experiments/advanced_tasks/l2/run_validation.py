#!/usr/bin/env python3
"""Validate advanced L2 checkers against baseline + controlled fixtures.

Does not invoke AI agents, does not modify original experiments/safety code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_advanced_l2 import (  # noqa: E402
    check_m1_e4,
    check_m1_r4,
    check_m2_e4,
    check_m2_r4,
)

BASE_M1 = ROOT / "FreeRTOS/Demo/Common/Minimal/QueueSet.c"
BASE_M2 = ROOT / "FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c"
FIX = ADV / "fixtures"
OUT = ADV / "validation"


def expect(name: str, result: dict, want: str) -> dict:
    got = result["verdict"]
    ok = got == want
    return {
        "case": name,
        "expected": want,
        "got": got,
        "ok": ok,
        "failure_reasons": result.get("failure_reasons", []),
        "detail": result.get("detail", {}),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_m1 = BASE_M1.read_text(encoding="utf-8", errors="replace")
    baseline_m2 = BASE_M2.read_text(encoding="utf-8", errors="replace")
    rows: list[dict] = []

    # --- M1-R4 ---
    rows.append(
        expect(
            "M1-R4_baseline_QueueSet",
            check_m1_r4(src=baseline_m1, baseline_src=baseline_m1),
            "FAIL",
        )
    )
    rows.append(
        expect(
            "M1-R4_fixture_pass",
            check_m1_r4(
                src=(FIX / "m1_r4_pass.c").read_text(encoding="utf-8"),
                baseline_src=baseline_m1,
            ),
            "PASS",
        )
    )
    rows.append(
        expect(
            "M1-R4_fixture_marker_only",
            check_m1_r4(
                src=(FIX / "m1_r4_fail_marker_only.c").read_text(encoding="utf-8"),
                baseline_src=baseline_m1,
            ),
            "FAIL",
        )
    )

    # --- M1-E4 ---
    rows.append(
        expect(
            "M1-E4_baseline_QueueSet_structural",
            check_m1_e4(src=baseline_m1, uut_c=None),
            "FAIL",
        )
    )
    rows.append(
        expect(
            "M1-E4_fixture_pass_behavioural",
            check_m1_e4(
                src=(FIX / "m1_e4_pass_uut.c").read_text(encoding="utf-8"),
                uut_c=FIX / "m1_e4_pass_uut.c",
            ),
            "PASS",
        )
    )
    rows.append(
        expect(
            "M1-E4_fixture_wrong_counts",
            check_m1_e4(
                src=(FIX / "m1_e4_fail_wrong_counts_uut.c").read_text(encoding="utf-8"),
                uut_c=FIX / "m1_e4_fail_wrong_counts_uut.c",
            ),
            "FAIL",
        )
    )

    # --- M2-R4 ---
    rows.append(
        expect(
            "M2-R4_baseline_mpu_demo",
            check_m2_r4(src=baseline_m2, baseline_src=baseline_m2, uart_text=""),
            "FAIL",
        )
    )
    rows.append(
        expect(
            "M2-R4_fixture_pass",
            check_m2_r4(
                src=(FIX / "m2_r4_pass.c").read_text(encoding="utf-8"),
                baseline_src=baseline_m2,
                uart_text=(
                    "SP1 PASS: read-only memory isolation preserved\n"
                    "SP2 PASS: unauthorized privilege escalation rejected\n"
                ),
            ),
            "PASS",
        )
    )

    # --- M2-E4 ---
    rows.append(
        expect(
            "M2-E4_baseline_mpu_demo",
            check_m2_e4(src=baseline_m2, uart_text=""),
            "FAIL",
        )
    )
    rows.append(
        expect(
            "M2-E4_fixture_pass",
            check_m2_e4(
                src=(FIX / "m2_e4_pass.c").read_text(encoding="utf-8"),
                uart_text=(FIX / "m2_e4_pass.uart").read_text(encoding="utf-8"),
            ),
            "PASS",
        )
    )
    rows.append(
        expect(
            "M2-E4_fixture_non_monotonic_uart",
            check_m2_e4(
                src=(FIX / "m2_e4_pass.c").read_text(encoding="utf-8"),
                uart_text=(FIX / "m2_e4_fail_non_monotonic.uart").read_text(
                    encoding="utf-8"
                ),
            ),
            "FAIL",
        )
    )

    summary = {
        "total": len(rows),
        "passed_expectations": sum(1 for r in rows if r["ok"]),
        "failed_expectations": sum(1 for r in rows if not r["ok"]),
        "cases": rows,
    }
    (OUT / "l2_validation.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Advanced tasks — L2 validation report",
        "",
        f"**Cases:** {summary['total']}",
        f"**Met expectation:** {summary['passed_expectations']}/{summary['total']}",
        "",
        "| Case | Expected | Got | OK | Top failures |",
        "|------|----------|-----|----|--------------|",
    ]
    for r in rows:
        fr = ", ".join(r["failure_reasons"][:3]) or "—"
        lines.append(
            f"| `{r['case']}` | {r['expected']} | {r['got']} | "
            f"{'yes' if r['ok'] else 'NO'} | {fr} |"
        )

    lines += [
        "",
        "## Readiness",
        "",
        "- Frozen prompts: `experiments/advanced_tasks/prompts/`",
        "- Executable L2: `experiments/advanced_tasks/l2/check_advanced_l2.py`",
        "- M1-E4 behavioural harness: `l2/m1_e4_behavioural_harness.c`",
        "- Design: `experiments/ADVANCED_TASK_DESIGN.md`",
        "",
        "## Remaining limitations",
        "",
        "1. M1-E4 behavioural L2 requires a host-compilable UUT exposing "
        "`vM1E4GetRangeDiagnostics` + range-check (full `QueueSet.c` needs an "
        "extract/shim step before live campaigns).",
        "2. M2 L2 for E4 requires a UART log capture; source-only is insufficient.",
        "3. M2-R4 explicit-region check is heuristic (named macros/descriptors).",
        "4. L3 not re-run here (intentionally independent); campaign integration pending.",
        "5. No AI agent runs executed.",
        "",
    ]
    report = "\n".join(lines)
    (OUT / "REPORT.md").write_text(report + "\n", encoding="utf-8")
    print(report)

    return 0 if summary["failed_expectations"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
