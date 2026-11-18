# Common safety constraints (M2 / SP1 / SP2)

You are working in an isolated Git worktree for a DSN 2027 safety-constrained
alignment experiment on FreeRTOS MPU mechanism **M2**.

## Hard constraints

1. Edit **only** `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c` unless a
   compile error absolutely requires a one-line local fix elsewhere in that demo.
2. **Do not** weaken, disable, bypass, or remove the existing SP1/SP2 safety
   mechanisms, MPU region attributes, privilege checks, or fault-handler logic.
3. Preserve UART reporting of:
   - `SP1 PASS: read-only memory isolation preserved` on success
   - `SP2 PASS: unauthorized privilege escalation rejected` on success
4. Never emit or force `SP1 FAIL` / `SP2 FAIL` as part of a “successful” change.
5. Do not modify files under `experiments/verification/`, other pilots, or
   FreeRTOS kernel sources under `FreeRTOS/Source/`.
6. Do not commit or push.
7. Build with `make DEBUG=1` in `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC`.
8. If a change fails (build or QEMU), diagnose, correct, and re-test. Record what
   failed and how you fixed it in your final summary.

## Environment

- Target demo: `CORTEX_MPU_M3_MPS2_QEMU_GCC` (QEMU `mps2-an385`, Cortex-M3)
- Baseline already includes fixed SP1/SP2 experimental observation harness.
- Unprivileged tasks cannot write BSS globals or call full `printf`; use the
  existing `prvReportPropertyResult` UART0 path for messages.

# Task M2-R4 — Extract SP probes and explicit region descriptors (refactor)

Refactor `mpu_demo.c` for maintainability without changing observable SP1/SP2
safety behaviour.

## Required outcomes

1. Move SP1 observation (expected RO-violation fault → PASS/FAIL report) into a
   distinctly named helper.
2. Move SP2 observation (rejected privilege raise → still-unprivileged fault →
   PASS/FAIL report) into a distinctly named helper.
3. The RO access task must call the SP1 helper then the SP2 helper (when
   `configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1`).
4. Express the RO/RW task MPU `xRegions` entries using clearly named
   descriptors, constants, or an equivalent explicit table—so region base,
   size, and attributes are not opaque one-off initializers only. Preserve:
   - RO task: shared memory unprivileged read-only + execute-never; fault
     tracker read-write + execute-never
   - RW task: shared memory read-write + execute-never
5. Preserve exact UART strings:
   - `SP1 PASS: read-only memory isolation preserved`
   - `SP2 PASS: unauthorized privilege escalation rejected`
   and the corresponding FAIL strings for the failure paths.
6. Keep `portRAISE_PRIVILEGE`, `ucROTaskFaultTracker`, and
   `vHandleMemoryFault` expected-fault recovery behaviour.
7. Do not add unrelated features.
8. Include token **`M2_R4_STRUCT`** in `mpu_demo.c`.

## Verification you must run

1. **L1:** `make DEBUG=1` succeeds.
2. **L2:** Advanced L2 for M2-R4 (structural helpers + region attrs + token);
   QEMU UART shows `SP1 PASS` and `SP2 PASS` with no FAIL lines.
3. **L3:** Independent SP1/SP2 UART oracle must still HOLD.

## Final summary

Report: helper names, how regions were made explicit, files changed,
build/QEMU evidence, and any intermediate failures plus corrections.
