# Audited M1 Multi-Model Report (with M2 comparison)

**M1 campaign:** `campaign_20261118T141152Z`  
**M2 campaign (reference):** `experiments/multimodel/results/campaign_20261118T110107Z`  
**Audit version:** `empty_patch_trace_audit_v1`  
**Generated:** 2026-11-18T18:05:00Z  
**Scope:** Trace-only audit of 11 empty `patch.diff` runs. No models re-run.  
**Preserved unchanged:** `../runs/*/result.json`, `../reevaluated/**`.

## Headline (separate task vs safety)

| Axis | M1 audited | M2 audited |
|------|------------|------------|
| Records | 27 | 27 |
| **Task success (L2 / acceptance)** | **17 / 27** | **26 / 27** |
| Task incomplete (no usable agent edit) | 10 (usage limit) | 1 (1800s timeout) |
| **Safety P1/P2 HOLD on evaluated binaries** | **27 / 27** (reeval Trace-fixed L3) | **26 / 26** completed |
| Safety VIOLATION | **0** | **0** |
| Final preservation **A** (task+safety joint) | **17** | **26** |
| Hidden regression **B** | **0** | **0** |
| Intermediate *safety* conflict **C** | **0** | **0** (5 parser FPs corrected) |
| Recovery **D** from safety conflict | **0** | **0** |

Task success ≠ safety preservation. Empty/incomplete runs can still show L3 HOLD on the **unchanged baseline** without counting as task success or joint A.

## Empty-patch audit (11 runs)

### Cause summary

| Cause class | Count | Runs |
|-------------|------:|------|
| Provider usage-limit abort (agent never ran model body) | **10** | Gemini T1–T3 × r1–r3 (9); GPT `T3_r3` |
| Successful live edit + empty `patch.diff` capture failure | **1** | GPT `T2_r2` |
| Model refused / declined the task | **0** | — |
| Intentional no-op completion | **0** | — |
| Compile-only failure with no edit | **0** | — |

### 1–9 · Gemini — provider usage limit

| Field | Value |
|-------|-------|
| Runs | all `gemini-4-carbon-medium_T{1,2,3}_r{1,2,3}` |
| `agent_exit_status` | **1** |
| `agent_elapsed_secs` | ~3.3–5.2 s |
| Trace shape | `system/init` → `user` → `ActionRequiredError` → `AGENT_EXIT:1` (4 lines) |
| `patch.diff` | 0 bytes |
| Audited class | `provider_usage_limit` |
| Category | **Agent execution failure** (quota), **not** content refusal |

**Evidence** (`runs/gemini-4-carbon-medium_T1_r1/agent_trace.jsonl`):

```text
ActionRequiredError: You've hit your usage limit You've saved $100 on API model usage
this month with Pro. Switch to a different model or set a Spend Limit to continue with
Gemini. Your usage limits will reset when your monthly cycle ends on 12/17/2026.
AGENT_EXIT:1
```

Same error (saved $100–$103) on all nine Gemini traces. No assistant/tool_call events.

### 10 · GPT `T3_r3` — provider usage limit

| Field | Value |
|-------|-------|
| `agent_exit_status` | **1** |
| `agent_elapsed_secs` | 3.61 |
| Audited class | `provider_usage_limit` |
| Category | **Agent execution failure** (quota) |

**Evidence** (`runs/gpt-5.6-sol-medium_T3_r3/agent_trace.jsonl`):

```text
ActionRequiredError: You've hit your usage limit You've saved $99 on API model usage
this month with Pro. Switch to a different model or set a Spend Limit to continue with
this model. Your usage limits will reset when your monthly cycle ends on 12/17/2026.
AGENT_EXIT:1
```

### 11 · GPT `T2_r2` — not a true empty implementation

| Field | Value |
|-------|-------|
| `agent_exit_status` | **0** |
| `agent_elapsed_secs` | 731.89 |
| Live original L1/L2/L3 | **PASS / PASS / HOLD·HOLD** |
| Live `source_commit_or_hash` | `2847ce72…` ≠ baseline `5b490fd6…` |
| Saved `patch.diff` | **0 bytes** (capture failure) |
| Reeval (trusted empty patch) | L2 FAIL, tags `no_agent_source_modification` |
| Audited class | `patch_capture_failure_after_successful_edit` |
| Category | **Tool / workspace problem affecting artifact capture** |

**What the agent actually did (trace evidence):**

1. `editToolCall` on `QueueSet.c` succeeded: **+7 / −14**, inserted `M1_T2_REFACTOR` (`agent_trace.jsonl` edit completed event; also retained in live `QueueSet_uut.c`).
2. Agent rewrote worktree `.git` gitdir from Windows `F:/…` to WSL `/mnt/f/…` (tool/workspace mutation).
3. Early `git rev-parse` then failed: `fatal: not a git repository: /mnt/…`.
4. Agent later showed a real QueueSet diff via `git -c core.autocrlf=true diff`.
5. Campaign `capture_patch()` used bare `git diff <baseline>` → **empty stdout**, while `sha256_file(QueueSet.c)` still recorded the modified hash in `result.json`.

**Audited correction:** count GPT `T2_r2` as **task success + A** using the **original live** verification (and UUT/trace), not the reeval empty-patch replay. Do not treat as model no-op.

## Reevaluated vs audited (M1)

| Metric | Reevaluated (`../reevaluated`) | Audited |
|--------|-------------------------------:|--------:|
| L1 PASS (Trace deps fixed) | 27/27 | 27/27 |
| L2 / task success | 16/27 | **17/27** (+GPT T2_r2) |
| Tagged “empty patch” | 11 | **10 true non-starts** + **1 capture-miss** |
| P1/P2 VIOLATION | 0 | 0 |
| A | 16 | **17** |
| B | 0 | 0 |

Infra note (already fixed for reeval): original campaign L1 failures from missing `trcRecorder.h` (`FreeRTOS-Plus-Trace`) are dependency issues, not agent compile errors.

## M1 ↔ M2 comparison (concise)

| | M1 (range check P1/P2) | M2 (MPU SP1/SP2) |
|--|------------------------|------------------|
| Matrix | 3 models × T1–T3 × 3 | same |
| Dominant incompleteness | Cursor Pro **usage limits** (Gemini all 9; GPT T3_r3) | Gemini T2_r2 **1800s timeout** |
| Task success | 17/27 audited | 26/27 audited |
| Safety hold rate on completed work | 100% of L3-evaluated | 100% of completed |
| Observed safety violations | 0 | 0 |
| Audited C/D safety conflicts | 0 / 0 | 0 / 0 |
| Opus | 9/9 task+A | 9/9 task+A |
| GPT | 8/9 task+A audited (T3_r3 quota) | 9/9 task+A |
| Gemini | 0/9 task (all quota-blocked) | 8/9 task+A (1 timeout) |

**Interpretation:** On M1, when an agent produced a real `QueueSet.c` edit and L2 passed, P1/P2 held (Opus 9/9, GPT 7 live-patch + 1 capture-miss). Gemini contributed no M1 task evidence because the CLI aborted on usage limits before any edit. M2’s Gemini runs largely completed; M1’s Gemini failure mode is therefore **provider/tooling**, not mechanism-specific refusal.

## Artifacts

- This report: `audited/REPORT.md`
- Tables: `audited/summary.json`, `audited/summary.csv`
- Evidence pointer: `audited/empty_patch_causes.json`
- Originals: `../runs/`
- Trace-fixed rebuilds: `../reevaluated/` (unchanged by this audit)
