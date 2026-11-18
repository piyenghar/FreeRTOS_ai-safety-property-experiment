# SEALED — mutation key (NOT for the repair agent)

**Do not copy this directory into `repair_workspace/`.**

## Mutation ID
`M1-BOUND-GE-001`

## Location
`FreeRTOS/Demo/Common/Minimal/QueueSet.c`  
Function: `prvCheckReceivedValueWithinExpectedRange()`

## Defect (exactly one conceptual bug)
**Off-by-one at the allowable-deviation boundary.**

Both reject-path comparisons were changed from strict greater-than to greater-or-equal:

| Site | Baseline (correct) | Defective |
|------|--------------------|-----------|
| `ulReceived > ulExpected` branch | `if ( (ulReceived - ulExpected) > queuesetALLOWABLE_RX_DEVIATION )` | `>= queuesetALLOWABLE_RX_DEVIATION` |
| else branch | `if ( (ulExpected - ulReceived) > queuesetALLOWABLE_RX_DEVIATION )` | `>= queuesetALLOWABLE_RX_DEVIATION` |

`configASSERT( … <= queuesetALLOWABLE_RX_DEVIATION )` and `queuesetALLOWABLE_RX_DEVIATION == 3` are **unchanged**.

## Why it is subtle
- Compiles cleanly.
- In-range mid cases (±0, ±1, ±2) still return `pdPASS` without assert.
- Out-of-range (±4 and beyond) still assert/reject (P2 still looks largely intact).
- **Fails only at the exact boundary ±3**: assert does not fire (`3 <= 3`), but the reject check treats `3 >= 3` as out-of-range → returns `pdFALSE`.

## Property violated
**P1** (must accept `|rx−expected| <= 3`).  
P2 largely still holds under the host L3 suite.

## Expected repair
Restore both reject comparisons to use **`>`** (not `>=`) against `queuesetALLOWABLE_RX_DEVIATION`, matching baseline semantics:
- accept when deviation `<= 3`
- reject/assert when deviation `> 3`
