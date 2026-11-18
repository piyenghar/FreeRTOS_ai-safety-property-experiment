# M1 safety-repair pilot — preparation report

**Branch:** `experiment/m1-safety-repair-pilot` (no commit / no push)  
**Repair attempted:** no  
**AI repair agent invoked:** no  

## Readiness

**Defective version: READY** for a future repair run.

| Check | Result |
|-------|--------|
| Baseline L3 | **PASS** (P1/P2 HOLD) |
| Defective L3 | **FAIL** (P1 VIOLATION; P2 HOLD; compiles) |
| Host build of defective UUT | **PASS** (`stage: run`) |
| Original `FreeRTOS/.../QueueSet.c` | **untouched** |
| Mutation key outside repair workspace | **yes** (`sealed_mutation_key/`) |
| Prior experiment results | **preserved** |

## Layout

- `repair_workspace/` — defective `QueueSet.c` + L3/build support only  
- `sealed_mutation_key/` — mutation description + expected repair (**not** for repair agent)  
- `snapshots/` — baseline + defective copies  
- `verification_runs/` — recorded L3 oracle outputs  

## Stop

Preparation complete. Repair not started.
