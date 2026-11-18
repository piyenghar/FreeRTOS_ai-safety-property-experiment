# DSN 2027 — Advanced task integration report

**Date:** 2026-11-18  
**AI models invoked:** no  
**Original campaigns / safety code modified:** no  

## Readiness

| Task | Prompts frozen | L2 wired | L3 reused | Fixture pipeline | Baseline L2 FAIL | Ready for paid agents? |
|------|----------------|----------|-----------|------------------|------------------|------------------------|
| **M1-R4** | PASS | PASS | PASS (`run_l3_against_queueset.py`) | **PASS** | PASS | **PASS** (infra) |
| **M1-E4** | PASS | PASS (QueueSet UUT behavioural) | PASS | **PASS** | PASS | **PASS** (infra) |
| **M2-R4** | PASS | PASS | PASS (`l3_pilot_oracle.py`) | **PASS** | PASS | **PASS** with L1 note |
| **M2-E4** | PASS | PASS (UART behavioural) | PASS | **PASS** | PASS | **PASS** with L1 note |

Integrated fixture validation: **12/12** expectations met  
(`validation/integrated/latest.json`).

Dry-run: `validation/DRY_RUN_REPORT.md` — baseline advanced L2 all **FAIL**.

## What was integrated

1. Configs: `config_m1.yaml`, `config_m2.yaml` (separate from original campaign configs).
2. Frozen prompts under `prompts/` linked from those configs.
3. Executable L2: `l2/check_advanced_l2.py` + M1-E4 `scripts/run_m1_e4_l2_against_queueset.py` (full `QueueSet.c` via L3-style prepare/shims).
4. L3: unchanged M1/M2 oracles.
5. Campaign hook: `scripts/verify_advanced_task.py`.
6. Reproduction: `REPRODUCTION.md`.

## Remaining blockers / limits

1. **M2 full demo L1 (QEMU `make DEBUG=1`)** not re-executed inside the fixture matrix; M2 L1 remains a campaign-worktree step. L2/L3 for M2 were validated on patched sources + UART logs / existing oracle.
2. **Paid multi-model campaign** not launched (`invoke_ai_models: false`).
3. M2 oracle CLI still uses pilot ids `t1|t2|t3`; advanced runs map L3 calls to `--pilot t2` for SP scoring only (advanced L2 is separate).
4. M2-R4 explicit-region L2 remains heuristic (named macros/descriptors).

## Verdict

Infrastructure for all four tasks is **PASS-ready** for offline verification and future agent campaigns. Do not claim live multi-model results until agents are run under these configs.
