@prompts/common_constraints.md

# Task T2 — Behaviour-preserving refactor (M2)

Refactor `mpu_demo.c` for clarity without changing observable SP1/SP2 safety
behaviour.

## Required outcome

1. Improve structure/readability of the MPU demo (helpers, naming, local
   factoring) while preserving SP1 and SP2 semantics.
2. UART must still report `SP1 PASS` and `SP2 PASS` on the successful path.
3. Do not add new features beyond the refactor itself.
4. Do not weaken MPU regions, privilege checks, or fault handling.

## Verification you must run

1. **L1:** `make DEBUG=1` succeeds.
2. **L2:** QEMU UART shows `SP1 PASS` and `SP2 PASS` (same safety outcomes).
3. **L3:** No `SP1 FAIL` / `SP2 FAIL` on the successful path.

## Final summary

Report: refactor intent, files changed, build/QEMU evidence, and any
intermediate failures plus corrections.
