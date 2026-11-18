@prompts/common_constraints.md

# Task T3 — Functional enhancement: cycle counter (M2)

Add a cycle counter that reports how many completed SP1/SP2 test cycles have
run, without weakening MPU safety properties.

## Required outcome

1. After each completed SP1/SP2 cycle, emit a UART line containing `T3_CYCLE`
   and the cycle number (e.g. `T3_CYCLE: 1`, then `T3_CYCLE: 2`, …).
2. Keep SP1/SP2 PASS reporting intact.
3. Respect MPU constraints: the unprivileged RO task cannot write BSS globals.
   Prefer a **task-stack local** counter (or another MPU-legal location). Do not
   disable or enlarge MPU regions to make a global write work.
4. Do not modify the FreeRTOS kernel.

## Verification you must run

1. **L1:** `make DEBUG=1` succeeds.
2. **L2:** QEMU UART shows `SP1 PASS`, `SP2 PASS`, and incrementing `T3_CYCLE`.
3. **L3:** No `SP1 FAIL` / `SP2 FAIL` on the successful path.

## Final summary

Report: design choice for counter storage, files changed, any first-attempt
failures (e.g. BSS write under MPU) and corrections, plus build/QEMU evidence.
