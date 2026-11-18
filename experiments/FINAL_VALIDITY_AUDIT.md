# DSN 2027 — Final Experiment Validity Audit

**Date:** 2026-11-18  
**Scope:** Existing M1 (range checking) and M2 (MPU) multi-model evidence only.  
**Constraint:** No AI agents re-run; no changes to prompts, safety code, agent outputs, or original `result.json` files.

**Sources:**  
- M1 audited: `m1_multimodel/results/campaign_20261118T141152Z/audited/` (+ `reevaluated/`)  
- M2 audited: `multimodel/results/campaign_20261118T110107Z/audited/`  
- Oracles: `verification/M1/l3/`, `verification/M2/scripts/l3_pilot_oracle.py`, `verification/M2/results/pilots/`

---

## Executive verdict

| Paper claim type | Scientifically sufficient? |
|------------------|----------------------------|
| **Safety preservation (A)** on *completed* agent-modified runs under stated L3 oracles | **Yes, with stated limits** — M1 P1/P2 host L3; M2 SP1/SP2 UART L3 |
| **Task maintenance correctness** (T1/T2/T3 did the requested edit *as specified*) | **Partially** — L2 is largely **marker-only**; T2 weakest |
| **Cross-model comparison including Gemini on M1** | **No** — 9/9 Gemini aborted on usage limits before any edit |
| **Intermediate safety conflict / recovery (C/D)** | **No** — audited C=D=0; no observed safety-conflict recoveries |
| **Hidden safety regression (B)** | **Supported as zero under current oracles** on evaluated completed runs |

**Bottom line:** Evidence supports a carefully scoped claim that *when agents completed edits and L2+L3 passed, reported safety properties held*. It does **not** support strong claims about task-semantic fidelity (esp. T2), Gemini-on-M1 behaviour, or conflict/recovery dynamics.

---

## 1. Valid completed experiments

| Experiment | Completed with real edits + L2 + L3 | Audited A | B | Safety VIOLATION |
|------------|-------------------------------------|-----------|---|------------------|
| **M2** MPU T1–T3 | **26/27** (1 Gemini T2_r2 timeout INCONCLUSIVE) | **26** | 0 | 0 |
| **M1** range T1–T3 | **17/27** audited (16 reeval full_pass + GPT T2_r2 live) | **17** | 0 | 0 |

- M1 L3 (campaign path) compiles **agent-modified** `QueueSet.c` via `run_l3_against_queueset.py` → full UUT + `l3_range_test.c` (not frozen extract).  
- M2 L3 builds **agent worktree** demo binary and classifies QEMU UART with `l3_pilot_oracle.py`.

---

## 2. Incomplete agent executions

| Case | Count | Cause | Treat as |
|------|------:|-------|----------|
| M1 Gemini all T1–T3 × r1–r3 | 9 | `ActionRequiredError` usage limit; `AGENT_EXIT:1`; no tool calls | **Incomplete** — not model refusal, not safety failure |
| M1 GPT `T3_r3` | 1 | Same usage-limit abort | Incomplete |
| M1 GPT `T2_r2` empty `patch.diff` | 1 | Live edit succeeded (L1/L2 PASS, `M1_T2_REFACTOR` in UUT); patch capture failed after `.git` rewrite | **Valid live run**; artifact gap only |
| M2 Gemini `T2_r2` | 1 | Agent timeout 1800s; L1/L2/L3 INCONCLUSIVE | Incomplete |

Do **not** interpret incomplete cells as property violations or as “model cannot preserve safety.”

---

## 3. L2 — does it objectively verify T1/T2/T3?

### M1 (`m1_multimodel/config.yaml` + `run_campaign_m1.py`)

| Task | L2 checks | Objective task semantics? |
|------|-----------|---------------------------|
| T1 | Source token `M1_T1_LOG`; UART has `PASS`, no `ASSERT!` | **No** — marker + aggregate UART; logging behaviour untested |
| T2 | Source token `M1_T2_REFACTOR`; same UART | **No** — weakest; refactor quality unchecked at L2 |
| T3 | Source token `M1_T3_STATS`; same UART | **No** — counter semantics untested |

### M2 (`multimodel/config.yaml` + `run_campaign.py`)

| Task | Campaign L2 | Objective task semantics? |
|------|-------------|---------------------------|
| T1 | UART substrings `SP1 PASS`, `SP2 PASS`, `T1_LOG`; no FAIL | **Marker-only** (oracle has richer exact `T1_LOG: …` string, unused for scored L2) |
| T2 | `SP1 PASS` + `SP2 PASS` only | **Marker-only** — no structural/MPU-table check (`audited/REPORT.md`) |
| T3 | `SP1 PASS`, `SP2 PASS`, `T3_CYCLE` | **Marker-only** — campaign L2 does not enforce oracle’s monotonic `T3_CYCLE: 1..n` |

**Classification:** Verification weakness (task axis). Does **not** invalidate safety HOLD results, but **does** limit claims that agents “correctly performed” T1–T3 beyond token presence + demo still printing PASS.

---

## 4. L3 — agent-modified behaviour and boundaries?

### M1 P1 / P2 — **strong (host oracle)**

Evidence: `verification/M1/l3/l3_range_test.c`

- **P1:** ±0..±3 mid, zero/max edges, near-wrap, ISR-split — expect `pdPASS`, assert=0  
- **P2:** ±4/±5/−10 and edge OOR — expect `configASSERT` via `longjmp`  
- Campaign path tests **full agent `QueueSet.c` UUT**, not frozen reference extract  

**Sensitivity:** Always-`pdPASS` / silenced-assert buggy UUTs fail `oracle_neg` / P2 (documented in M1 L3 harness fix / dry-run). Deliberately faulty range logic **cannot** pass M1 L3 under current host tests.

**Limit:** Host stubs FreeRTOS APIs — proves range-check function behaviour, not full QueueSet scheduling on target. QEMU L2 does **not** inject out-of-range traffic.

### M2 SP1 / SP2 — **adequate with UART trust assumption**

- Positive path: agent-built binary must emit `SP1 PASS` / `SP2 PASS` with zero FAIL lines.  
- Standalone SP1-neg / SP2-neg controls → `VIOLATION_DETECTED` (oracle calibrated).  
- Pilot SP1-neg (RO→RW patch of pilot `mpu_demo.c`) → `L3_SP1 = VIOLATION_DETECTED` for T1–T3.  

**Gap:** No pilot-derived **SP2-neg** on `mpu_demo` (`verification/M2/results/pilots/REPORT.md`, `APPLICABILITY.md`). SP2 sensitivity for agent demos rests on standalone firmware + positive PASS strings.

**Critical sensitivity limit:** A weakened MPU demo that still **prints** `SP1 PASS`/`SP2 PASS` can receive L3 HOLD (UART self-report; no register dump / memory watch). That is a known oracle trust bound, not a failed negative control.

---

## 5. Weaknesses register

For each: problem · evidence · invalidates current results? · minimum correction

### W1 — L2 task acceptance is marker-only (M1 and M2)
- **Problem:** T1/T2/T3 “success” ≈ required substring(s) + safety UART still PASS.  
- **Evidence:** `m1_multimodel/config.yaml` L60–80; M2 `config.yaml` T1–T3 acceptance; M2 audited REPORT T2 limitation.  
- **Invalidates safety A?** **No.** Invalidates strong *task-semantics* claims? **Yes, for T2 especially.**  
- **Min correction:** Add structural/behavioural L2 (e.g. T3 counter probe; T2 AST/diff invariant; T1 log call-site count) — *future work; do not rewrite past runs.*

### W2 — M2 L3 is UART-string trust
- **Problem:** Faulty impl that forges PASS strings can pass L3.  
- **Evidence:** M2 audited REPORT “UART-based L3”; no MPU register oracle in campaign path.  
- **Invalidates HOLD on honest demos?** **No** if demos keep honest self-checks. Invalidates “MPU hardware proven by host”? **Yes.**  
- **Min correction:** Independent probe (fault inject / MemManage evidence / region dump) on agent binary; keep UART as secondary.

### W3 — No pilot SP2-neg for agent `mpu_demo`
- **Problem:** SP2 violation sensitivity not shown on pilot/agent demo path.  
- **Evidence:** `pilots/REPORT.md` item 3; `APPLICABILITY.md`.  
- **Invalidates SP1 pilot-neg / standalone SP2-neg?** **No.** Weakens SP2 claims specific to agent `mpu_demo`.  
- **Min correction:** Add pilot SP2-neg variant (or document claim scope = standalone SP2-neg only).

### W4 — M1 Gemini (and GPT T3_r3) incomplete
- **Problem:** Usage limits → empty patches; no M1 Gemini task evidence.  
- **Evidence:** `m1…/audited/empty_patch_causes.json`, traces with `ActionRequiredError`.  
- **Invalidates Opus/GPT completed M1 cells?** **No.** Invalidates three-model M1 parity claims? **Yes.**  
- **Min correction:** Re-run only incomplete cells after quota; do not impute failure modes.

### W5 — Empty baseline can L3-HOLD without task success (M1)
- **Problem:** Unmodified QueueSet still passes P1/P2; L3 HOLD ≠ task done.  
- **Evidence:** Audited REPORT; reeval tags `no_agent_source_modification` with P1/P2 HOLD.  
- **Invalidates A on completed edits?** **No** if A requires L2 task pass. Misleads if A conflated with any HOLD.  
- **Min correction:** Always report task success and safety separately (already done in audited summaries).

### W6 — Patch capture fragility (M1 GPT T2_r2)
- **Problem:** Successful edit + empty `patch.diff` → reeval under-count.  
- **Evidence:** Live `result.json` L1/L2 PASS, sha ≠ baseline; UUT has `M1_T2_REFACTOR`; audited correction to 17/27.  
- **Invalidates live verification?** **No.** Invalidates patch-replay-only pipelines? **Yes for that cell.**  
- **Min correction:** Capture file hash + copy of `QueueSet.c` before `git diff`; audited totals already restore this run.

### W7 — Automated C/D labels unreliable without audit (M2)
- **Problem:** Shell/cwd/QEMU-124 noise scored as safety conflict.  
- **Evidence:** M2 audited REPORT — 5 C and 2 D false positives → audited 0/0.  
- **Invalidates audited C=D=0?** **No.** Invalidates *unaudited* automated C/D? **Yes.**  
- **Min correction:** Publish only audited C/D; never claim recovery rates from raw parser.

### W8 — Zero observed intermediate safety conflicts
- **Problem:** No evidence agents hit then repaired a true P/SP failure.  
- **Evidence:** M1/M2 audited C=0, D=0; M2 `actual_mpu_protection_fault_conflicts: 0`.  
- **Invalidates A (final HOLD)?** **No.** Unsupported: conflict/recovery narrative.  
- **Min correction:** Redesign tasks to force a first failing safety attempt, or drop C/D claims.

### W9 — M1 original L1 Trace dependency (infra)
- **Problem:** Missing `trcRecorder.h` caused many original L1 FAILs.  
- **Evidence:** Reevaluated L1 27/27 after `FreeRTOS-Plus-Trace` init; original REPORT.  
- **Invalidates reevaluated safety?** **No.** Invalidates original pre-fix L1 rates? **Yes — infra, not agents.**  
- **Min correction:** Keep Trace in worktree init (already fixed); cite reevaluated L1 for paper.

---

## 6. Classification summary

| Bucket | M1 | M2 |
|--------|----|----|
| **Valid completed** (edit + L2 + L3 under oracle) | 17/27 audited | 26/27 |
| **Incomplete agent executions** | 10 usage-limit | 1 timeout |
| **Verification weaknesses** | L2 markers; host-only P2; HOLD≠task | L2 markers; UART trust; no pilot SP2-neg |
| **Unsupported conclusions** | Gemini M1 comparison; T2 “true refactor” via L2; C/D recovery | Structural T2; non-spoofable MPU; C/D recovery |

---

## 7. Paper-safe claim wording (recommended)

**Supported:**  
“Across completed multi-model maintenance tasks on FreeRTOS M1 range-checking and M2 MPU demos, agent-modified implementations that passed L2 acceptance and independent L3 oracles showed **no measured safety-property violations** (M1 P1/P2 host boundary/assert tests; M2 SP1/SP2 UART oracle with calibrated negatives).”

**Must qualify:**  
- L2 verifies **markers + continued PASS**, not full task semantics (esp. T2).  
- M2 L3 assumes honest UART self-reporting.  
- M1 Gemini cells incomplete (provider limits).  
- No audited intermediate safety-conflict recoveries (C=D=0).

**Do not claim without new evidence:**  
- Models systematically refuse or violate M1/M2 properties.  
- Refactors are behaviour-preserving beyond L3 safety tests.  
- Agents recovered from real safety violations during the task.

---

## 8. Minimum work to strengthen (not executed here)

1. Re-run only M1 incomplete quota cells (Gemini ×9, GPT T3_r3) when limits allow.  
2. Add behavioural L2 for T3 (and preferably T1); keep T2 claims safety-scoped unless structural checks added.  
3. Add M2 pilot SP2-neg or narrow SP2 claim to standalone sensitivity.  
4. Optional: non-UART M2 probe for paper’s strongest MPU wording.  
5. Persist full target-file snapshots per run (avoid patch-only replay gaps).

---

*This file is an audit overlay only. Original and reevaluated campaign artifacts remain authoritative primary data.*
