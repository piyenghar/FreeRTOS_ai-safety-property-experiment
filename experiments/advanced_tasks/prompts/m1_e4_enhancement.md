@m1_common_constraints.md

# Task M1-E4 — Dual-outcome range diagnostics (functional enhancement)

Add diagnostics that distinguish **accepted** (in-range) vs **rejected**
(out-of-range) outcomes of `prvCheckReceivedValueWithinExpectedRange()`,
without changing P1/P2 acceptance or rejection behaviour.

## Functional requirements

1. **Accepted count:** A diagnostic count that increases by exactly one each
   time the range-check returns `pdPASS`.
2. **Rejected count:** A diagnostic count that increases by exactly one each
   time the range-check takes the out-of-range reject path. Out-of-range must
   still fire `configASSERT` and must not return `pdPASS`.
3. **Query API (mandatory contract for L2):** Provide this exact linkable
   function in `QueueSet.c` (non-`static`):

```c
void vM1E4GetRangeDiagnostics( uint32_t * pulAccepted,
                               uint32_t * pulRejected );
```

   - If `pulAccepted` is non-NULL, write the accepted count.
   - If `pulRejected` is non-NULL, write the rejected count.
   - Both counts are 0 before any range-check calls in a fresh image.
4. Keep `queuesetALLOWABLE_RX_DEVIATION == 3`. Do not silence or remove
   `configASSERT`. Do not force `pdPASS` on out-of-range.
5. Include the exact token **`M1_E4_DIAG`** in `QueueSet.c`.

How you store the counts is up to you, as long as the requirements above hold.

## Verification you must run

1. **L1:** MPS2 QEMU GCC `make` succeeds.
2. **L2:** Advanced L2 for M1-E4 runs behavioural acceptance tests against the
   query API (in-range increments accepted; out-of-range increments rejected
   with assert; initial zeros). QEMU still shows check-task `PASS` without
   `ASSERT!` on normal traffic (timeout 124 OK).
3. **L3:** P1/P2 host oracle must still HOLD (unchanged safety tests).

## Final summary

Report: how diagnostics are exposed, files changed, L2 behavioural evidence,
any first-attempt range-check failures and corrections, plus build/QEMU notes.
