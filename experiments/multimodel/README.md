# Multi-model experiment runner (DSN 2027 / M2)

Fully automated matrix over **M2** (MPU), safety properties **SP1/SP2**, tasks
**T1/T2/T3**, three models × three repetitions (= **27 runs**).

Each live run: frozen baseline worktree → fresh Cursor Agent CLI session with
`--model` → L1 build / L2 UART acceptance / independent L3 host oracle →
diffs, logs, `result.json`.

## Prerequisites

1. Cursor Agent CLI in WSL:
   ```bash
   curl https://cursor.com/install -fsS | bash
   export PATH="$HOME/.local/bin:$PATH"
   agent --version
   agent login          # required before live runs / agent models
   agent models         # confirm cli_model_id values in config.yaml
   ```
2. Python 3 + PyYAML (`pip install pyyaml`)
3. QEMU + ARM GCC available inside WSL for L1/L2 (same toolchain as M2 pilots)

## Configure

Edit [`config.yaml`](config.yaml):

- `models[].cli_model_id` — exact Agent CLI `--model` string
- `tasks` / `repetitions` / `filters`
- `experiment.baseline_ref` — frozen commit (default: SP1/SP2 harness tip)

## Dry run (no AI)

```powershell
.\experiments\multimodel\scripts\launch.ps1 -DryRun -SampleWorktreeOnly
```

Or:

```powershell
python experiments\multimodel\scripts\run_matrix.py --dry-run --sample-worktree-only
```

## Launch full 27-run campaign (after login + model validation)

```powershell
.\experiments\multimodel\scripts\launch.ps1
```

Optional smoke:

```powershell
.\experiments\multimodel\scripts\launch.ps1 -Limit 1
```

Refresh model snapshot:

```powershell
.\experiments\multimodel\scripts\launch.ps1 -RefreshModels
```

## Layout

| Path | Role |
|------|------|
| `config.yaml` | Models, tasks, reps, baseline, agent flags |
| `prompts/` | T1/T2/T3 prompts + shared constraints |
| `scripts/run_matrix.py` | Orchestrator |
| `results/dryrun_*/` | Dry-run plan + sample validation |
| `results/campaign_*/` | Live artifacts per `run_id` |
| `worktrees/` | Isolated Git worktrees (gitignored) |

## Safety / preservation

- Does not modify existing M1/M2 verification trees as part of setup beyond this folder
- Worktrees start from `baseline_ref` only; primary dirty submodules untouched
- No commit/push from the runner
