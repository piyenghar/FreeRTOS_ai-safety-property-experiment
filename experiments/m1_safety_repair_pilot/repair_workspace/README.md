# M1 safety repair workspace (agent-facing)

Contains a **defective** `QueueSet.c` that must be repaired so M1 safety
properties P1/P2 hold under the existing host L3 oracle.

## Layout

- `FreeRTOS/Demo/Common/Minimal/QueueSet.c` — implementation under test
- `verification/M1/l3/` — host L3 test + stubs (independent oracle)
- `m1_l3_harness/` — shims to compile full `QueueSet.c` on host
- `scripts/` — `prepare_queueset_uut.py`, `run_l3_against_queueset.py`

## Constraints

- Edit only the range-check logic as needed to restore correct safety behaviour.
- Do not weaken or remove `configASSERT`.
- Keep `queuesetALLOWABLE_RX_DEVIATION == 3`.
- Do not modify the L3 oracle sources to force a pass.

## Suggested verify (from repo root, adjusting paths)

```text
python repair_workspace/scripts/run_l3_against_queueset.py ^
  --queueset repair_workspace/FreeRTOS/Demo/Common/Minimal/QueueSet.c ^
  --out-dir /tmp/m1_repair_l3 ^
  --harness-dir repair_workspace/verification/M1/l3 ^
  --shim-dir repair_workspace/m1_l3_harness
```

(Paths may need to be absolute; scripts expect repository-relative defaults — prefer invoking from the main repo with explicit `--queueset` pointing here.)
