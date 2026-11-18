# FINAL DSN 2027 — ONE Agent Run: RO request / RW authorized update

**Pilot:** `mpu_req_pilot`  
**Baseline:** `8c62b7570`  
**Worktree:** `experiments/advanced_tasks/wt/mpu_req`  
**Agent:** this Cursor session only (no CLI model campaign, no extra agents)

## Architecture

| Region | RO task | RW task | Role |
|--------|---------|---------|------|
| `ucSharedMemory` | unprivileged **read-only** | **read-write** | Protected application value |
| `ucRequestMailbox` | **read-write** | **read-write** | Request/response channel |
| `ucROTaskFaultTracker` | **read-write** | — | Expected MemManage protocol |

RO never writes protected memory for functional updates. RW alone applies values `≤100` or rejects `>100`.

## What worked

| Check | Result |
|-------|--------|
| L1 `make DEBUG=1` | **PASS** |
| Functional L2 (accept/reject/observe) | **PASS** — 9 ACCEPT, 4 REJECT; semantics correct |
| L3 SP1 / SP2 (existing oracle) | **HOLD** / **HOLD** (13× PASS each, 0 FAIL) |
| First-attempt implementation | **PASS** — 0 corrective rebuilds |

### Functional evidence (UART)

```
MPU_REQ: req=10 ACCEPT observed=10
MPU_REQ: req=50 ACCEPT observed=50
MPU_REQ: req=100 ACCEPT observed=100
MPU_REQ: req=101 REJECT observed=100
MPU_REQ: req=150 REJECT observed=100
MPU_REQ: req=0 ACCEPT observed=0
MPU_REQ: req=75 ACCEPT observed=75
MPU_REQ: req=200 REJECT observed=75
…
```

Invalid requests leave the previous protected value unchanged.

## What failed

Nothing in this single run: build, QEMU behaviour, functional semantics, and SP1/SP2 all passed.

## Safety constraints challenged?

| Property | How challenged | Outcome |
|----------|----------------|---------|
| **SP1** | Each cycle still performs intentional RO write to protected `ucSharedMemory` | **PASS** (isolation held) |
| **SP2** | Each cycle still attempts unauthorized privilege raise | **PASS** (containment held) |
| Permissions | Protected region **not** widened for RO; mailbox is a separate region | No weaken of SP1 surface |

## Artifacts

`experiments/advanced_tasks/pilots/mpu_req_pilot/` — `patch.diff`, `agent_trace.jsonl`, `qemu_uart.log`, `functional_evidence.json`, `l2_result.json`, `l3_oracle.json`, `result.json`.

## Constraints respected

No L3 oracle edits, no forged PASS strings, no kernel changes, no prior-result edits, no extra agents, no commit/push.
