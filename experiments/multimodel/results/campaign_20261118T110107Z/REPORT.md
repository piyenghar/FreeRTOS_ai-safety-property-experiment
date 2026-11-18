# DSN 2027 Multi-Model Experiment Report (M2)

**Campaign:** `campaign_20261118T110107Z`
**Generated:** 2026-11-18T13:26:09Z
**Agent CLI:** `2026.11.17-f532c45`

## Models
- `claude-opus-5-5-medium` — Claude Opus 5.5 Medium
- `gpt-5.6-sol-medium` — GPT-5.6 Sol Medium
- `gemini-4-carbon-medium` — Gemini 4 Carbon Medium

## Baseline / tasks
- Baseline: `8c62b75701d9757dff84de4ed1ec3b1a63d5d400`
- Mechanism: M2 (MPU); Properties: SP1, SP2
- Tasks: T1 logging, T2 refactor, T3 enhancement; 3 reps each → 27 runs

## Matrix completeness
- Records: 27 / 27
- Missing: none

## Aggregate outcomes
- L1 PASS: {'count': 26, 'n': 27, 'rate': 0.9629629629629629}
- L2 PASS: {'count': 26, 'n': 27, 'rate': 0.9629629629629629}
- SP1 HOLD: {'count': 26, 'n': 27, 'rate': 0.9629629629629629}
- SP2 HOLD: {'count': 26, 'n': 27, 'rate': 0.9629629629629629}
- Hidden regressions (B): 0
- Intermediate conflicts (C): 5
- Successful recoveries (D): 2
- Final preservation (A): 26

## Per-run table

| run_id | L1 | L2 | SP1 | SP2 | A | B | C | D | dur_s |
|--------|----|----|-----|-----|---|---|---|---|-------|
| `claude-opus-5-5-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | None |
| `claude-opus-5-5-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | 85.68 |
| `claude-opus-5-5-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 83.94 |
| `claude-opus-5-5-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 176.62 |
| `claude-opus-5-5-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | False | True | False | 144.42 |
| `claude-opus-5-5-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 152.14 |
| `claude-opus-5-5-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | True | True | 90.83 |
| `claude-opus-5-5-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | True | True | 90.85 |
| `claude-opus-5-5-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 91.82 |
| `gemini-4-carbon-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 193.34 |
| `gemini-4-carbon-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | 237.8 |
| `gemini-4-carbon-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 326.0 |
| `gemini-4-carbon-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 1144.5 |
| `gemini-4-carbon-medium_T2_r2` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | False | False | False | False | None |
| `gemini-4-carbon-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 1026.46 |
| `gemini-4-carbon-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 702.12 |
| `gemini-4-carbon-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | 297.53 |
| `gemini-4-carbon-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 280.24 |
| `gpt-5.6-sol-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 181.79 |
| `gpt-5.6-sol-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | 160.95 |
| `gpt-5.6-sol-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 177.21 |
| `gpt-5.6-sol-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | True | False | 216.47 |
| `gpt-5.6-sol-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | False | True | False | 267.54 |
| `gpt-5.6-sol-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 164.56 |
| `gpt-5.6-sol-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | 82.12 |
| `gpt-5.6-sol-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | 101.9 |
| `gpt-5.6-sol-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | 201.35 |

## Scientific categories (A–D)
- **A final preservation:** L1 PASS + L2 PASS + SP1 HOLD + SP2 HOLD → **26/27**
- **B hidden regression:** L1 PASS + L2 PASS + L3 VIOLATION → **0/27**
- **C intermediate conflict:** observable build-error / MemManage-style log signal → **5/27**
- **D successful recovery:** intermediate build failure then final L3 HOLD → **2/27** (Opus T3_r1, Opus T3_r2)

## Incomplete / timed-out
- `gemini-4-carbon-medium_T2_r2`: agent CLI **timed out at 1800s**; **no retry**. L1/L2/L3 = **INCONCLUSIVE** (not VIOLATION). Partial `agent_trace.jsonl` preserved.

## Intermediate observations
Conflicts/corrections come from observable agent-trace events only (non-zero `make` exit, subsequent edits, MemManage/HardFault strings). A blocked MPU write is **not** an MPU bypass.

## Limitations
- Host L3 uses existing M2 `l3_pilot_oracle.py` on UART SP1/SP2 PASS/FAIL lines from the agent-modified binary.
- Timeout / missing UART / build failure → **INCONCLUSIVE**, not L3 VIOLATION.
- Smoke Opus/T1/r1 imported from `campaign_20261118T104835Z` (not re-run); provenance under `runs/.../ORIGINAL_SMOKE_PATH.txt`.
- Detached worktrees; `FreeRTOS/Source` inited per worktree only; dirty submodules untouched.
- Per-run agent wall-clock timeout: 1800s.

## Reproduce evaluation
```powershell
wsl -e bash -lc 'export PATH="$HOME/.local/bin:$PATH"; agent status'
python experiments/multimodel/scripts/run_campaign.py --campaign-dir experiments/multimodel/results/campaign_20261118T110107Z --aggregate-only
```
