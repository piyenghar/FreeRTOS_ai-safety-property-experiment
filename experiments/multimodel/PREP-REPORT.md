# Multi-model runner preparation report

**Date:** 2026-11-18  
**Scope:** M2 / SP1 / SP2 / T1–T3 / 3 models × 3 reps (= 27)  
**Status:** Infrastructure ready; **dry-run OK**; live 27-run campaign **not** executed.

## 1. Cursor Agent CLI

| Check | Result |
|-------|--------|
| Native Windows `agent` / `cursor-agent` | Not on PATH |
| Windows installer (`irm … win32=true`) | Blocked: needs Git Bash for private worker |
| WSL install (`curl https://cursor.com/install`) | **OK** |
| Binary | `/home/drpadmaiyenghar/.local/bin/agent` |
| Version | `2026.11.17-f532c45` |
| Auth | **Not logged in** |
| `agent models` / `--list-models` | **Authentication required** |

Authenticate before live runs:

```bash
wsl -e bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agent login; agent models'
```

Or set `CURSOR_API_KEY` / pass `--api-key`.

## 2. Available / candidate model IDs

**Live CLI catalog:** unavailable until login (see `results/cli_models_snapshot.json`).

Evidence used for **provisional** `cli_model_id` values (marked `validated_from_cli: false`):

| Display name | Provisional CLI `--model` | Alternate | Evidence |
|--------------|---------------------------|-----------|----------|
| Claude Opus 5.5 Medium | `claude-opus-5-5[effort=medium]` | `claude-opus-5-5-medium` | Package string `claude-opus-5-5`; `agent --help` bracket effort form; Cursor session catalog `claude-opus-5-5-medium` |
| GPT-5.6 Sol Medium | `gpt-5.6-sol[effort=medium]` | `gpt-5.6-sol-medium` | Docs family GPT-5.6 Sol; session catalog `gpt-5.6-sol-medium`; **not** yet returned by `agent models` |
| Gemini 4 Carbon Medium | `gemini-4-carbon[effort=medium]` | `gemini-4-carbon-medium` | Docs page `gemini-4-carbon`; session catalog `gemini-4-carbon-medium`; **not** yet returned by `agent models` |

**Do not treat provisional IDs as confirmed.** After login:

```powershell
.\experiments\multimodel\scripts\launch.ps1 -RefreshModels
```

Update `config.yaml` `cli_model_id` and set `validated_from_cli: true`.

## 3. Runner architecture

```
experiments/multimodel/
  config.yaml                 # models × tasks × reps, baseline, agent flags
  prompts/{common,t1,t2,t3}*  # frozen task prompts + SP1/SP2 constraints
  scripts/run_matrix.py       # orchestrator
  scripts/launch.ps1|.sh      # entrypoints
  results/                    # dryrun_*/campaign_*/ + cli_models_snapshot.json
  wt/rXX/                     # short-slot isolated worktrees (gitignored)
```

Per live run:

1. Git worktree from frozen baseline `8c62b7570` (SP1/SP2 harness tip)
2. `git submodule update --init FreeRTOS/Source` **inside worktree only**
3. Fresh `agent -p --force --trust --model <id> --workspace <wt>`
4. Capture stream-json log + correction signals
5. Diff `mpu_demo.c` vs baseline
6. L1 `make DEBUG=1` → L2 QEMU UART acceptance → L3 `l3_pilot_oracle.py`

## 4. Launch commands

Dry-run (done):

```powershell
python experiments\multimodel\scripts\run_matrix.py --dry-run --sample-worktree-only
# or: .\experiments\multimodel\scripts\launch.ps1 -DryRun -SampleWorktreeOnly
```

Full campaign (after login + model validation) — **not run yet**:

```powershell
.\experiments\multimodel\scripts\launch.ps1
```

Smoke one live run:

```powershell
.\experiments\multimodel\scripts\launch.ps1 -Limit 1
```

## 5. Dry-run results

Campaign: `experiments/multimodel/results/dryrun_20261118T103329Z`

| Metric | Value |
|--------|-------|
| Planned runs | **27** |
| Sample worktree | **DRY_RUN_OK** (`mpu_demo.c` present at baseline) |
| Remaining | **26 × DRY_RUN_PLANNED** (no extra worktrees) |
| Agent invoked | **No** |
| Baseline | `8c62b75701d9757dff84de4ed1ec3b1a63d5d400` |

Note: first dry-run attempt failed on Windows `Filename too long`; fixed via short slots `wt/rXX` + per-command `git -c core.longpaths=true` (no global git config change).

## 6. Limitations (auth / access / billing)

1. **CLI not authenticated** — cannot list or invoke models until `agent login` or API key.
2. **Model IDs provisional** — must be confirmed against `agent models` for this account/team.
3. **Plan / Max Mode** — Opus 5.5 / GPT-5.6 Sol docs note Max Mode on legacy request-based plans; Gemini 4 Carbon is third-party / Other Models pool (prepaid credit on X Subscription).
4. **Native Windows agent install incomplete** — automation uses **WSL** agent.
5. **QEMU/ARM GCC** must be available in WSL for live L1/L2 (same as M2 pilots).
6. Existing dirty FreeRTOS-Plus submodules and M1/M2 artifacts were **not** altered by this prep (only added `experiments/multimodel/`).

## 7. Preservation / git

- No commit / no push
- QueueSet.c and M2 verification scripts unchanged
- Primary dirty submodules left as-is
