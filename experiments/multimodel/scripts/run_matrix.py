#!/usr/bin/env python3
"""Automated multi-model M2 experiment runner (DSN 2027).

Creates isolated Git worktrees from a frozen baseline, invokes Cursor Agent CLI
with --model per run, then executes L1/L2/L3 verification and records artifacts.

Dry-run mode expands the 27-run matrix and validates infrastructure without
invoking AI models.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[3]  # repo root
MM = Path(__file__).resolve().parents[1]  # experiments/multimodel


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    # Minimal YAML subset fallback (no PyYAML): only used if pyyaml missing.
    raise SystemExit(
        "PyYAML is required. Install with: python -m pip install pyyaml"
    )


def run_cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(
            args=args,
            returncode=127,
            stdout="",
            stderr=f"FileNotFoundError: {exc}",
        )


def wsl_bash(script: str, *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    # Pass script via stdin-less -c; escape carefully.
    return run_cmd(["wsl", "-e", "bash", "-lc", script], timeout=timeout)


def win_to_wsl(path: Path) -> str:
    p = str(path.resolve())
    if re.match(r"^[A-Za-z]:[\\/]", p):
        drive = p[0].lower()
        rest = p[2:].replace("\\", "/").lstrip("/")
        return f"/mnt/{drive}/{rest}"
    return p.replace("\\", "/")


def expand_prompt(prompt_path: Path) -> str:
    """Inline @prompts/foo.md includes (one level)."""
    text = prompt_path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^@(\S+)\s*$", line.strip())
        if m:
            inc = (prompt_path.parent / Path(m.group(1)).name)
            # prompts referenced as @prompts/common_constraints.md from same dir
            alt = MM / m.group(1)
            target = alt if alt.exists() else (prompt_path.parent / m.group(1))
            if not target.exists() and (prompt_path.parent / Path(m.group(1)).name).exists():
                target = prompt_path.parent / Path(m.group(1)).name
            if target.exists():
                out_lines.append(target.read_text(encoding="utf-8"))
                out_lines.append("")
            else:
                out_lines.append(f"[MISSING INCLUDE: {m.group(1)}]")
        else:
            out_lines.append(line)
    return "\n".join(out_lines).strip() + "\n"


@dataclass
class RunSpec:
    run_id: str
    model_id: str
    model_display: str
    cli_model_id: str
    task_id: str
    task_name: str
    rep: int
    prompt_file: str
    acceptance: dict[str, Any]


def build_matrix(cfg: dict[str, Any]) -> list[RunSpec]:
    filters = cfg.get("filters") or {}
    f_models = set(filters.get("models") or [])
    f_tasks = set(filters.get("tasks") or [])
    f_reps = set(filters.get("reps") or [])
    reps = int(cfg.get("repetitions", 1))
    specs: list[RunSpec] = []
    for model in cfg["models"]:
        if not model.get("enabled", True):
            continue
        if f_models and model["id"] not in f_models:
            continue
        for task in cfg["tasks"]:
            if not task.get("enabled", True):
                continue
            if f_tasks and task["id"] not in f_tasks:
                continue
            for rep in range(1, reps + 1):
                if f_reps and rep not in f_reps:
                    continue
                mid = model["id"]
                tid = task["id"]
                run_id = f"m2_{mid}_{tid}_r{rep}".replace("[", "").replace("]", "").replace("=", "-")
                # sanitize filesystem-ish
                run_id = re.sub(r"[^A-Za-z0-9._+-]+", "_", run_id)
                specs.append(
                    RunSpec(
                        run_id=run_id,
                        model_id=mid,
                        model_display=model.get("display_name", mid),
                        cli_model_id=model["cli_model_id"],
                        task_id=tid,
                        task_name=task["name"],
                        rep=rep,
                        prompt_file=task["prompt_file"],
                        acceptance=task.get("acceptance") or {},
                    )
                )
    return specs


def agent_status_blob() -> dict[str, Any]:
    script = (
        'export PATH="$HOME/.local/bin:$PATH"; '
        'echo BIN=$(command -v agent || echo MISSING); '
        'agent --version 2>&1; echo ---STATUS---; agent status 2>&1; '
        'echo ---MODELS---; agent models 2>&1; echo ---LIST---; agent --list-models 2>&1'
    )
    cp = wsl_bash(script, timeout=60)
    out = (cp.stdout or "") + (cp.stderr or "")
    logged_in = "Not logged in" not in out and "Authentication required" not in out
    # Heuristic: if models section has lines that look like model ids after MODELS
    return {
        "exit_code": cp.returncode,
        "raw": out,
        "agent_present": "BIN=/home/" in out or "BIN=/usr/" in out or "agent" in out,
        "logged_in": logged_in and "Authentication required" not in out.split("---MODELS---")[0],
        "models_raw": out.split("---MODELS---")[-1] if "---MODELS---" in out else out,
    }


def refresh_models(cfg_path: Path, cfg: dict[str, Any]) -> Path:
    st = agent_status_blob()
    out_path = MM / "results" / "cli_models_snapshot.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": utc_now(),
        "agent_status": {k: st[k] for k in ("exit_code", "agent_present", "logged_in")},
        "raw": st["raw"],
        "note": (
            "Paste/confirm cli_model_id values in config.yaml against this snapshot. "
            "Do not invent IDs."
        ),
        "config_candidates": [
            {
                "id": m["id"],
                "cli_model_id": m["cli_model_id"],
                "cli_model_id_alt": m.get("cli_model_id_alt"),
                "validated_from_cli": m.get("validated_from_cli", False),
            }
            for m in cfg.get("models", [])
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def ensure_baseline(cfg: dict[str, Any]) -> str:
    ref = cfg["experiment"]["baseline_ref"]
    cp = run_cmd(["git", "rev-parse", "--verify", ref], cwd=ROOT)
    if cp.returncode != 0:
        raise SystemExit(f"baseline_ref not found: {ref}\n{cp.stderr}")
    return cp.stdout.strip()


def short_slot(run_index: int) -> str:
    """Short filesystem slot to avoid Windows MAX_PATH on nested FreeRTOS demos."""
    return f"r{run_index:02d}"


def make_exp_branch(run_id: str, slot: str) -> str:
    branch = f"exp/{slot}-{run_id[:40]}"
    return re.sub(r"[^A-Za-z0-9._/-]+", "-", branch)[:80]


def create_worktree(
    run_id: str,
    baseline: str,
    wt_root: Path,
    *,
    slot: str,
) -> tuple[Path, str]:
    wt_root.mkdir(parents=True, exist_ok=True)
    path = wt_root / slot
    branch = make_exp_branch(run_id, slot)
    if path.exists():
        # Prefer git worktree remove; fall back to rmtree.
        run_cmd(
            ["git", "-c", "core.longpaths=true", "worktree", "remove", "--force", str(path)],
            cwd=ROOT,
        )
        shutil.rmtree(path, ignore_errors=True)
    run_cmd(["git", "branch", "-D", branch], cwd=ROOT)
    # Per-invocation longpaths only (does not rewrite user git config).
    cp = run_cmd(
        [
            "git",
            "-c",
            "core.longpaths=true",
            "worktree",
            "add",
            "-B",
            branch,
            str(path),
            baseline,
        ],
        cwd=ROOT,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"worktree add failed: {cp.stderr or cp.stdout}")
    # Init FreeRTOS/Source inside worktree only (do not touch primary dirty submodules).
    run_cmd(
        [
            "git",
            "-c",
            "core.longpaths=true",
            "submodule",
            "update",
            "--init",
            "--depth",
            "1",
            "FreeRTOS/Source",
        ],
        cwd=path,
        timeout=600,
    )
    return path, branch


def remove_worktree(path: Path, branch_hint: str | None = None) -> None:
    run_cmd(
        ["git", "-c", "core.longpaths=true", "worktree", "remove", "--force", str(path)],
        cwd=ROOT,
    )
    if branch_hint:
        run_cmd(["git", "branch", "-D", branch_hint], cwd=ROOT)
    run_cmd(["git", "worktree", "prune"], cwd=ROOT)


def build_agent_command(
    cfg: dict[str, Any],
    *,
    workspace: Path,
    model: str,
    prompt: str,
) -> list[str]:
    ag = cfg["agent"]
    # Write prompt to a temp file inside the run dir to avoid shell quoting hell.
    # Caller creates prompt file and passes path embedded in prompt string? Better:
    # pass prompt via file read in WSL.
    cmd = [ag.get("command", "agent")]
    if ag.get("print", True):
        cmd.append("-p")
    if ag.get("force", True):
        cmd.append("--force")
    if ag.get("trust", True):
        cmd.append("--trust")
    if ag.get("sandbox"):
        cmd.extend(["--sandbox", str(ag["sandbox"])])
    if ag.get("output_format"):
        cmd.extend(["--output-format", str(ag["output_format"])])
    cmd.extend(["--model", model])
    cmd.extend(["--workspace", win_to_wsl(workspace)])
    # Prompt appended by caller as final arg after writing to file.
    cmd.append(prompt)
    return cmd


def invoke_agent(
    cfg: dict[str, Any],
    *,
    workspace: Path,
    model: str,
    prompt_text: str,
    log_path: Path,
) -> dict[str, Any]:
    prompt_file = log_path.parent / "prompt_expanded.md"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    wsl_ws = win_to_wsl(workspace)
    wsl_prompt = win_to_wsl(prompt_file)
    wsl_log = win_to_wsl(log_path)
    timeout = int(cfg["agent"].get("timeout_secs") or 0) or None
    # Read prompt file content into agent argv via $(cat ...).
    script = f'''
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
PROMPT=$(cat {shlex.quote(wsl_prompt)})
agent -p --force --trust --sandbox disabled \\
  --output-format stream-json \\
  --model {shlex.quote(model)} \\
  --workspace {shlex.quote(wsl_ws)} \\
  "$PROMPT" > {shlex.quote(wsl_log)} 2>&1
'''
    started = time.time()
    cp = wsl_bash(script, timeout=timeout)
    elapsed = time.time() - started
    return {
        "exit_code": cp.returncode,
        "elapsed_secs": round(elapsed, 2),
        "log": str(log_path),
        "stdout_tail": (cp.stdout or "")[-2000:],
        "stderr_tail": (cp.stderr or "")[-2000:],
    }


def parse_agent_corrections(log_path: Path) -> list[dict[str, Any]]:
    """Extract coarse intermediate error/correction signals from stream-json/text."""
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    events: list[dict[str, Any]] = []
    # stream-json: one JSON object per line
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            blob = json.dumps(obj).lower()
            if any(k in blob for k in ("error", "fail", "assert", "denied", "correction")):
                events.append({"line": i, "kind": "stream_signal", "snippet": line[:500]})
        else:
            low = line.lower()
            if any(k in low for k in ("error:", "failed", "make:", "undefined", "fault")):
                events.append({"line": i, "kind": "text_signal", "snippet": line[:500]})
    return events[:200]


def capture_diff(workspace: Path, baseline: str, out_diff: Path, out_stat: Path) -> dict[str, Any]:
    cp = run_cmd(["git", "diff", "--stat", baseline], cwd=workspace)
    out_stat.write_text(cp.stdout or "", encoding="utf-8")
    cp2 = run_cmd(["git", "diff", baseline], cwd=workspace)
    out_diff.write_text(cp2.stdout or "", encoding="utf-8")
    target = workspace / "FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c"
    sha = ""
    if target.exists():
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "diff_bytes": len(cp2.stdout or ""),
        "stat": (cp.stdout or "").strip(),
        "mpu_demo_sha256": sha,
    }


def run_verification(
    cfg: dict[str, Any],
    *,
    workspace: Path,
    run_dir: Path,
    acceptance: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    ver = cfg.get("verification") or {}
    demo = workspace / cfg["experiment"]["mpu_demo_path"]
    result: dict[str, Any] = {
        "L1": {"status": "SKIP"},
        "L2": {"status": "SKIP"},
        "L3": {"status": "SKIP"},
    }
    # L1 build (prefer WSL on this Windows host — make/qemu live there)
    if ver.get("run_l1_build", True):
        build_log = run_dir / "L1_build.txt"
        use_wsl = bool(cfg.get("agent", {}).get("invoke_via_wsl")) and shutil.which("wsl")
        if use_wsl:
            wdemo = win_to_wsl(demo)
            cp = wsl_bash(f"cd {shlex.quote(wdemo)} && make DEBUG=1", timeout=600)
        else:
            cp = run_cmd(["make", "DEBUG=1"], cwd=demo, timeout=600)
            if cp.returncode != 0 and shutil.which("wsl"):
                wdemo = win_to_wsl(demo)
                cp = wsl_bash(f"cd {shlex.quote(wdemo)} && make DEBUG=1", timeout=600)
        build_log.write_text((cp.stdout or "") + (cp.stderr or ""), encoding="utf-8")
        result["L1"] = {
            "status": "PASS" if cp.returncode == 0 else "FAIL",
            "exit_code": cp.returncode,
            "log": str(build_log),
        }

    uart_log = run_dir / "positive.uart.log"
    axf = demo / "output" / "RTOSDemo.axf"
    if not axf.exists():
        # Some Makefiles write RTOSDemo.axf at demo root / build folder.
        candidates = list(demo.rglob("RTOSDemo.axf"))
        axf = candidates[0] if candidates else axf

    # L2: QEMU + acceptance strings
    if ver.get("run_l2_acceptance", True) and result["L1"]["status"] == "PASS" and axf.exists():
        tmo = int(ver.get("qemu_timeout_secs") or 8)
        waxf = win_to_wsl(axf)
        wlog = win_to_wsl(uart_log)
        qscript = f'''
set +e
timeout {tmo}s qemu-system-arm -machine mps2-an385 -cpu cortex-m3 \
  -kernel {shlex.quote(waxf)} -serial stdio -monitor none \
  -semihosting -semihosting-config enable=on,target=native -nographic \
  > {shlex.quote(wlog)} 2>&1
echo EXIT:$? >> {shlex.quote(wlog)}
'''
        wsl_bash(qscript, timeout=tmo + 30)
        uart = uart_log.read_text(encoding="utf-8", errors="replace") if uart_log.exists() else ""
        must = acceptance.get("uart_must_contain") or []
        must_not = acceptance.get("uart_must_not_contain") or []
        missing = [s for s in must if s not in uart]
        forbidden = [s for s in must_not if s in uart]
        ok = not missing and not forbidden
        result["L2"] = {
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
            "forbidden_hits": forbidden,
            "uart_log": str(uart_log),
        }
    elif ver.get("run_l2_acceptance", True):
        result["L2"] = {"status": "FAIL", "reason": "no axf or L1 failed"}

    # L3: host oracle on UART (pilot mode) — existing M2 script.
    if ver.get("run_l3_oracle", True) and uart_log.exists():
        oracle = ROOT / ver["l3_oracle"]
        out_json = run_dir / "l3_positive.json"
        pilot = task_id.lower()  # T1 -> t1
        if oracle.exists():
            cp = run_cmd(
                [
                    sys.executable,
                    str(oracle),
                    "--mode",
                    "pilot",
                    "--pilot",
                    pilot,
                    "--control",
                    "pos",
                    "--log",
                    str(uart_log),
                    "--out",
                    str(out_json),
                    "--l1",
                    "PASS" if result["L1"]["status"] == "PASS" else "FAIL",
                    "--source-note",
                    f"multimodel worktree {workspace.name}",
                ],
                cwd=ROOT,
            )
            payload: dict[str, Any] = {}
            if out_json.exists():
                try:
                    payload = json.loads(out_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {}
            result["L3"] = {
                "status": payload.get("L3_verdict", "FAIL" if cp.returncode != 0 else "UNKNOWN"),
                "L2_verdict": payload.get("L2_verdict"),
                "json": str(out_json),
                "oracle_exit": cp.returncode,
                "stderr_tail": (cp.stderr or "")[-1000:],
            }
        else:
            uart = uart_log.read_text(encoding="utf-8", errors="replace")
            ok = (
                "SP1 PASS" in uart
                and "SP2 PASS" in uart
                and "SP1 FAIL" not in uart
                and "SP2 FAIL" not in uart
            )
            result["L3"] = {
                "status": "PASS" if ok else "FAIL",
                "note": "lightweight UART L3 (oracle script missing)",
            }
    return result


def execute_run(
    cfg: dict[str, Any],
    spec: RunSpec,
    *,
    dry_run: bool,
    baseline: str,
    run_index: int,
) -> dict[str, Any]:
    exp = cfg["experiment"]
    results_root = ROOT / exp["results_root"]
    wt_root = ROOT / exp["worktree_root"]
    slot = short_slot(run_index)
    run_dir = results_root / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] = {
        "run_id": spec.run_id,
        "slot": slot,
        "model_id": spec.model_id,
        "model_display": spec.model_display,
        "cli_model_id": spec.cli_model_id,
        "task_id": spec.task_id,
        "task_name": spec.task_name,
        "rep": spec.rep,
        "baseline_ref": baseline,
        "started_at": utc_now(),
        "dry_run": dry_run,
    }

    prompt_path = MM / spec.prompt_file
    prompt_text = expand_prompt(prompt_path)
    (run_dir / "prompt_expanded.md").write_text(prompt_text, encoding="utf-8")

    if dry_run:
        # Validate worktree creation once-ish: create and remove for this run.
        wt, branch = create_worktree(spec.run_id, baseline, wt_root, slot=slot)
        target = wt / exp["target_file"]
        meta["worktree"] = str(wt)
        meta["branch"] = branch
        meta["target_exists"] = target.exists()
        meta["agent_command_preview"] = [
            "agent",
            "-p",
            "--force",
            "--trust",
            "--sandbox",
            "disabled",
            "--output-format",
            "stream-json",
            "--model",
            spec.cli_model_id,
            "--workspace",
            win_to_wsl(wt),
            "<prompt_expanded.md>",
        ]
        # Do not invoke agent.
        meta["agent"] = {"skipped": True, "reason": "dry_run"}
        meta["verification"] = {"skipped": True, "reason": "dry_run"}
        meta["diff"] = {"skipped": True}
        remove_worktree(wt, branch)
        meta["worktree_removed"] = True
        meta["finished_at"] = utc_now()
        meta["status"] = "DRY_RUN_OK" if meta.get("target_exists") else "DRY_RUN_FAIL"
        (run_dir / "result.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return meta

    # Live run
    wt, branch = create_worktree(spec.run_id, baseline, wt_root, slot=slot)
    meta["worktree"] = str(wt)
    meta["branch"] = branch
    agent_log = run_dir / "agent.stream.jsonl"
    agent_info = invoke_agent(
        cfg, workspace=wt, model=spec.cli_model_id, prompt_text=prompt_text, log_path=agent_log
    )
    meta["agent"] = agent_info
    meta["corrections"] = parse_agent_corrections(agent_log)
    meta["diff"] = capture_diff(
        wt, baseline, run_dir / "source.diff", run_dir / "source.diffstat.txt"
    )
    meta["verification"] = run_verification(
        cfg,
        workspace=wt,
        run_dir=run_dir,
        acceptance=spec.acceptance,
        task_id=spec.task_id,
    )
    if not cfg.get("runtime", {}).get("keep_worktrees", True):
        remove_worktree(wt, branch)
        meta["worktree_removed"] = True
    meta["finished_at"] = utc_now()
    l1 = meta["verification"].get("L1", {}).get("status")
    l2 = meta["verification"].get("L2", {}).get("status")
    l3 = meta["verification"].get("L3", {}).get("status")
    meta["status"] = "PASS" if {l1, l2, l3} <= {"PASS"} else "FAIL"
    (run_dir / "result.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description="DSN2027 M2 multi-model experiment runner")
    ap.add_argument(
        "--config",
        default=str(MM / "config.yaml"),
        help="Path to config.yaml",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate matrix; do not invoke AI")
    ap.add_argument(
        "--refresh-models",
        action="store_true",
        help="Capture agent models/status snapshot (requires login for full list)",
    )
    ap.add_argument("--limit", type=int, default=0, help="Limit number of runs (0=all)")
    ap.add_argument(
        "--sample-worktree-only",
        action="store_true",
        help="With --dry-run: create/remove a single sample worktree instead of all 27",
    )
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)

    if args.refresh_models:
        path = refresh_models(cfg_path, cfg)
        print(f"Wrote {path}")
        return 0

    dry = bool(args.dry_run or cfg.get("runtime", {}).get("dry_run"))
    baseline = ensure_baseline(cfg)
    specs = build_matrix(cfg)
    if args.limit and args.limit > 0:
        specs = specs[: args.limit]

    results_root = ROOT / cfg["experiment"]["results_root"]
    results_root.mkdir(parents=True, exist_ok=True)
    campaign_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_dir = results_root / ("dryrun_" + campaign_id if dry else "campaign_" + campaign_id)
    campaign_dir.mkdir(parents=True, exist_ok=True)

    # Point results into campaign folder by temporarily overriding results_root
    cfg = json.loads(json.dumps(cfg))  # deep copy via json
    rel = campaign_dir.relative_to(ROOT).as_posix()
    cfg["experiment"]["results_root"] = rel

    agent_info = agent_status_blob()
    plan = {
        "campaign_id": campaign_id,
        "dry_run": dry,
        "baseline_ref": baseline,
        "run_count": len(specs),
        "expected_full_matrix": 27,
        "agent": {
            "present": agent_info.get("agent_present"),
            "logged_in": agent_info.get("logged_in"),
            "version_snip": (agent_info.get("raw") or "")[:300],
        },
        "runs": [asdict(s) for s in specs],
        "model_validation_note": (
            "cli_model_id values are provisional until agent login + `agent models`. "
            "See config.yaml header."
        ),
    }
    (campaign_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (campaign_dir / "agent_status.txt").write_text(agent_info.get("raw") or "", encoding="utf-8")

    results: list[dict[str, Any]] = []
    if dry and args.sample_worktree_only and specs:
        # Only exercise infrastructure on the first run spec.
        print(f"Dry-run sample worktree for {specs[0].run_id} ...")
        results.append(
            execute_run(cfg, specs[0], dry_run=True, baseline=baseline, run_index=1)
        )
        # Still record the full planned matrix without creating 27 worktrees.
        for idx, s in enumerate(specs[1:], start=2):
            results.append(
                {
                    "run_id": s.run_id,
                    "slot": short_slot(idx),
                    "status": "DRY_RUN_PLANNED",
                    "cli_model_id": s.cli_model_id,
                    "task_id": s.task_id,
                    "rep": s.rep,
                    "note": "planned only (--sample-worktree-only)",
                }
            )
    else:
        for i, spec in enumerate(specs, 1):
            print(f"[{i}/{len(specs)}] {spec.run_id} dry_run={dry}")
            try:
                results.append(
                    execute_run(
                        cfg, spec, dry_run=dry, baseline=baseline, run_index=i
                    )
                )
            except Exception as exc:  # noqa: BLE001
                err = {
                    "run_id": spec.run_id,
                    "status": "ERROR",
                    "error": str(exc),
                    "finished_at": utc_now(),
                }
                results.append(err)
                rd = (ROOT / cfg["experiment"]["results_root"] / spec.run_id)
                rd.mkdir(parents=True, exist_ok=True)
                (rd / "result.json").write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")

    summary = {
        "campaign_id": campaign_id,
        "dry_run": dry,
        "baseline_ref": baseline,
        "total": len(results),
        "by_status": {},
        "results": results,
        "agent_logged_in": agent_info.get("logged_in"),
        "finished_at": utc_now(),
    }
    for r in results:
        st = r.get("status", "UNKNOWN")
        summary["by_status"][st] = summary["by_status"].get(st, 0) + 1

    (campaign_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"campaign_dir": str(campaign_dir), "by_status": summary["by_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
