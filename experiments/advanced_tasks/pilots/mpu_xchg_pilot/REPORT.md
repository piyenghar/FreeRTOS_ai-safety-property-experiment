# ONE Advanced MPU Pilot — Inter-task shared data exchange

**Pilot ID:** `mpu_xchg_pilot`  
**Baseline:** `8c62b7570` (SP1/SP2 harness)  
**Worktree:** `experiments/advanced_tasks/wt/mpu_xchg`  
**Target:** `mpu_demo.c` only  
**Agent:** this Cursor session (no Cursor CLI / paid model campaign)

## Objective

Add RW→RO inter-task data exchange while preserving SP1 (RO isolation) and SP2 (privilege containment).

## Implementation

1. **RW task** publishes an incrementing byte to `ucSharedMemory[0]` each cycle (1…255).
2. **RO task** reads that byte (legal RO mapping) and reports  
   `MPU_XCHG: observed=<n>` via existing UART helper.
3. Existing SP1 intentional write-fault and SP2 rejected-privilege checks unchanged.
4. MPU region attributes and `vHandleMemoryFault` unchanged.

## Results

| Gate | Verdict | Evidence |
|------|---------|----------|
| **L1** build `make DEBUG=1` | **PASS** | `build/RTOSDemo.axf` |
| **L2** exchange + SP UART gate | **PASS** | observed `[0,1,2,…,9]`; SP1/SP2 PASS ×10; FAIL ×0 |
| **L3** SP1 | **HOLD** | existing `l3_pilot_oracle.py` |
| **L3** SP2 | **HOLD** | existing `l3_pilot_oracle.py` |

### UART excerpt

```
MPU_XCHG: observed=0
SP1 PASS: read-only memory isolation preserved
SP2 PASS: unauthorized privilege escalation rejected
MPU_XCHG: observed=1
SP1 PASS: read-only memory isolation preserved
SP2 PASS: unauthorized privilege escalation rejected
…
MPU_XCHG: observed=9
```

First observation `0` is pre-publish BSS; subsequent values increase — RO sees RW updates.

## Intermediate MPU faults / corrections

- **Expected** MemManage faults each cycle for SP1 (and SP2) intentional illegal writes; fault tracker protocol unchanged.
- **Unexpected faults:** 0  
- **Corrections / rebuilds after safety failure:** none (first implementation attempt passed L1/L2/L3).

## Artifacts

| File | Contents |
|------|----------|
| `patch.diff` | Worktree diff of `mpu_demo.c` |
| `mpu_demo.c` | Modified source copy |
| `qemu_uart.log` | QEMU serial capture |
| `l2_result.json` | Exchange-specific L2 |
| `l3_oracle.json` | Existing M2 oracle output |
| `agent_trace.jsonl` | Pilot action log |
| `result.json` | Machine-readable summary |

## Constraints respected

- No MPU permission weakening  
- No fault-handler changes  
- No oracle modifications  
- No prior campaign edits  
- No additional agent runs / no commit or push  
