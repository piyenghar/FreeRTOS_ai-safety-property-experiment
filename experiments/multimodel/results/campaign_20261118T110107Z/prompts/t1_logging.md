@prompts/common_constraints.md

# Task T1 — Development logging (M2)

Add minimal development logging to the MPU demo so each completed SP1/SP2 test
cycle emits a clear UART marker, without changing safety behaviour.

## Required outcome

1. After a successful SP1/SP2 cycle, report exactly one additional UART line that
   contains the token `T1_LOG` (recommended text:
   `T1_LOG: MPU test cycle completed`).
2. Reuse `prvReportPropertyResult` (or the same UART0 DATA register path).
3. Keep SP1 and SP2 PASS reporting intact; do not introduce FAIL lines.
4. Prefer the smallest possible edit to `mpu_demo.c`.

## Verification you must run

1. **L1:** `make DEBUG=1` in `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC` must succeed.
2. **L2:** QEMU UART must show `SP1 PASS`, `SP2 PASS`, and `T1_LOG`.
3. **L3:** No `SP1 FAIL` / `SP2 FAIL` on the successful path.

## Final summary

Report: files changed, key diff hunks, build result, QEMU UART excerpt, any
errors you hit and how you corrected them.
