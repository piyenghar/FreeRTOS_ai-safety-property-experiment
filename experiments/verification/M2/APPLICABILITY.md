# Applicability of M2 L3 harness to T1–T3 agent pilots

## Standalone oracle firmware (`sp1/`, `sp2/`)

The original standalone builds compile `l3_sp1.c` / `l3_sp2.c`, **not** pilot `mpu_demo.c`. They calibrate MemFault + value (+ nPRIV for SP2) oracles with positive HOLD and negative VIOLATION_DETECTED controls.

## Pilot integration (`scripts/run_pilot_integration.sh`)

Positive path:

1. Isolated Git worktree per pilot branch.
2. Build that worktree’s `CORTEX_MPU_M3_MPS2_QEMU_GCC` (actual pilot `mpu_demo.c`).
3. QEMU UART → host oracle (`l3_pilot_oracle.py`) for L1/L2/L3.

Negative path (SP1):

- Isolated copy of each pilot’s `mpu_demo.c` with RO shared-memory region weakened to RW.
- Built via `make PROPERTY=pilot_mpu` (verification Makefile); pilot branches untouched.

See `results/pilots/REPORT.md` and `results/pilots/summary.json` for executed outcomes.

## What remains / caveats

- Pilot L3 host rules still consume SP1/SP2 PASS/FAIL strings emitted by the pilot binary’s existing fault-tracker reporting.
- Stronger on-device independent probes inside the pilot binary (without trusting those strings) are future work.
- Pilot-specific SP2-neg binary not implemented under MPU wrappers v2; use standalone SP2-neg for oracle sensitivity.
