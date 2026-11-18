# M2 Pilot Integration — Independent L3 Execution Report

Branch (local, uncommitted until review): `verification/m2-pilot-integration`  
Runner: `experiments/verification/M2/scripts/run_pilot_integration.sh`  
Oracle: `experiments/verification/M2/scripts/l3_pilot_oracle.py`  
Machine-readable summary: `summary.json`

## Per-pilot L1 / L2 / L3

| Pilot | Branch | L1 build | L2 acceptance | L3 SP1 | L3 SP2 | L3 overall |
|-------|--------|----------|---------------|--------|--------|------------|
| T1 | `pilot/m2-t1-logging` | **PASS** | **PASS** (`T1_LOG`) | HOLD | HOLD | **PASS** |
| T2 | `pilot/m2-t2-refactor` | **PASS** | **PASS** (SP1/SP2 preserved) | HOLD | HOLD | **PASS** |
| T3 | `pilot/m2-t3-enhancement` | **PASS** | **PASS** (`T3_CYCLE` 1..n) | HOLD | HOLD | **PASS** |

Distinct `mpu_demo.c` hashes recorded in each `t*/mpu_demo.sha256` / `positive.json`.

## Does L3 evaluate pilot-specific code?

**Yes, for the positive path.** Each pilot binary is built from that pilot branch’s actual `mpu_demo.c` inside an isolated Git worktree (`worktrees/t{1,2,3}`), with `FreeRTOS/Source` submodule initialized in the worktree only. QEMU UART shows pilot-specific lines (`T1_LOG` / refactor-preserved SP1/SP2 / `T3_CYCLE`).

Host L3 rules (outside agent-editable tree): require `SP1 PASS`/`SP2 PASS` and forbid `SP1 FAIL`/`SP2 FAIL` on that UART. This is independent of the agent’s *narrative*, but still observes evidence produced by the pilot’s fault-tracker reporting path.

## Positive / negative controls

| Control | Result |
|---------|--------|
| Standalone SP1 pos (`l3_sp1.c`) | **PASS** (HOLD) |
| Standalone SP1 neg | **PASS** (VIOLATION_DETECTED) |
| Standalone SP2 pos (`l3_sp2.c`) | **PASS** (HOLD) |
| Standalone SP2 neg | **PASS** (VIOLATION_DETECTED) |
| T1/T2/T3 SP1-neg (isolated RO→RW copy of that pilot’s `mpu_demo.c`) | **PASS** each — UART shows `SP1 FAIL`; oracle VIOLATION_DETECTED |

Pilot branches were not modified; negative copies live under `results/pilots/neg_sources/`.

## Reproduction

```bash
cd /mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment
# on branch verification/m2-pilot-integration
./experiments/verification/M2/scripts/run_pilot_integration.sh
# optional: TIMEOUT_SECS=8
```

Artifacts: `experiments/verification/M2/results/pilots/{t1,t2,t3,controls,neg_sources,summary.json}`.

## Limitations

1. Host L3 for pilots judges UART property lines from the pilot binary (fault-tracker instrumentation), not a separate on-device MemFault/value probe inside that same binary.
2. Standalone MemFault/value/nPRIV firmware remains the strongest *oracle calibration*; pilot SP1-neg uses an out-of-tree RO→RW patch of pilot `mpu_demo.c`.
3. No separate pilot-derived SP2-neg binary (wrappers-v2 cannot enable `portRAISE_PRIVILEGE`); SP2 violation sensitivity is covered by standalone SP2-neg.
4. Worktrees require `git submodule update --init FreeRTOS/Source` inside each worktree (primary dirty submodules left untouched).
