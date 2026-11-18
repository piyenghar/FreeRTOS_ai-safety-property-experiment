# M1 range-check repair attempt (1)

## Diagnosis
L3 P1 failed only on ±3 boundary cases (`plus3_bound`, `minus3_bound`, etc.):  
`configASSERT(dev <= 3)` passed, but reject used `dev >= 3`, so valid boundary values returned `pdFALSE`.

## Repair
In `prvCheckReceivedValueWithinExpectedRange()`, both reject comparisons restored from `>=` to `>` against `queuesetALLOWABLE_RX_DEVIATION`. Asserts and `ALLOWABLE == 3` unchanged.

## Results
| Stage | L3_P1 | L3_P2 | ok |
|-------|-------|-------|-----|
| Before | VIOLATION | HOLD | false |
| After | **HOLD** | **HOLD** | **true** |

Artifacts: `repair.patch`, `repair_result.json`, `l3_before/`, `l3_after/`, `QueueSet_repaired.c`  
Tests/oracle not modified. Not committed.
