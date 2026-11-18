#!/usr/bin/env python3
"""End-to-end dry-run for advanced tasks — no Cursor CLI / paid models."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expand_prompt(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines(True):
        if line.startswith("@") and line.strip().endswith(".md"):
            inc = path.parent / line.strip()[1:]
            lines.append(inc.read_text(encoding="utf-8"))
            if not lines[-1].endswith("\n"):
                lines.append("\n")
        else:
            lines.append(line)
    return "".join(lines)


def run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ADV / "results" / f"dryrun_{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    cfg_m1 = yaml.safe_load((ADV / "config_m1.yaml").read_text(encoding="utf-8"))
    cfg_m2 = yaml.safe_load((ADV / "config_m2.yaml").read_text(encoding="utf-8"))
    shutil.copy2(ADV / "config_m1.yaml", out / "config_m1.yaml")
    shutil.copy2(ADV / "config_m2.yaml", out / "config_m2.yaml")
    shutil.copytree(ADV / "prompts", out / "prompts", dirs_exist_ok=True)

    prompt_hashes = {}
    for cfg, label in ((cfg_m1, "m1"), (cfg_m2, "m2")):
        for t in cfg["tasks"]:
            if not t.get("enabled", True):
                continue
            p = ADV / t["prompt_file"]
            expanded = expand_prompt(p)
            prompt_hashes[t["id"]] = sha256_text(expanded)
            (out / f"prompt_{t['id']}_expanded.md").write_text(expanded, encoding="utf-8")

    # Generate fixtures + run integrated validation
    gen = run([sys.executable, str(ADV / "scripts/generate_variants.py")])
    integ = run([sys.executable, str(ADV / "scripts/run_integrated_validation.py")], timeout=900)

    integ_latest = ADV / "validation/integrated/latest.json"
    integ_summary = (
        json.loads(integ_latest.read_text(encoding="utf-8")) if integ_latest.exists() else {}
    )

    # Baseline advanced L2 must fail
    sys.path.insert(0, str(ADV / "l2"))
    from check_advanced_l2 import check_m1_e4, check_m1_r4, check_m2_e4, check_m2_r4

    qs = (ROOT / "FreeRTOS/Demo/Common/Minimal/QueueSet.c").read_text(encoding="utf-8")
    mpu = (ROOT / "FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c").read_text(
        encoding="utf-8"
    )
    baseline_l2 = {
        "M1-R4": check_m1_r4(src=qs, baseline_src=qs)["verdict"],
        "M1-E4": check_m1_e4(src=qs, uut_c=None)["verdict"],
        "M2-R4": check_m2_r4(src=mpu, baseline_src=mpu, uart_text="")["verdict"],
        "M2-E4": check_m2_e4(src=mpu, uart_text="")["verdict"],
    }

    plan = {
        "dry_run": True,
        "stamp": stamp,
        "invoke_ai_models": False,
        "agent_invocations": 0,
        "models": [],
        "tasks_m1": [t["id"] for t in cfg_m1["tasks"]],
        "tasks_m2": [t["id"] for t in cfg_m2["tasks"]],
        "prompt_hashes": prompt_hashes,
        "generate_variants_exit": gen.returncode,
        "integrated_validation_exit": integ.returncode,
        "integrated_met": integ_summary.get("met"),
        "integrated_total": integ_summary.get("total"),
        "baseline_advanced_l2": baseline_l2,
        "baseline_all_l2_fail": all(v == "FAIL" for v in baseline_l2.values()),
        "out_dir": str(out),
    }
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (out / "integrated_stdout.txt").write_text(
        (integ.stdout or "") + "\n" + (integ.stderr or ""), encoding="utf-8"
    )

    report = [
        "# Advanced tasks — end-to-end dry-run",
        "",
        f"**Stamp:** `{stamp}`",
        "**AI models / Cursor CLI agents:** not invoked",
        f"**Integrated validation:** {integ_summary.get('met')}/{integ_summary.get('total')} expectations met (exit {integ.returncode})",
        f"**Baseline advanced L2 all FAIL:** {plan['baseline_all_l2_fail']} (`{baseline_l2}`)",
        "",
        "## Prompt hashes",
        "",
    ]
    for k, v in prompt_hashes.items():
        report.append(f"- `{k}`: `{v}`")
    report += [
        "",
        f"Artifacts: `{out.as_posix()}`",
        "",
    ]
    text = "\n".join(report)
    (out / "DRY_RUN_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (ADV / "validation/DRY_RUN_REPORT.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if integ.returncode == 0 and plan["baseline_all_l2_fail"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
