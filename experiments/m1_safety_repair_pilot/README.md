# M1 safety fault-repair pilot (preparation only)

**Branch:** `experiment/m1-safety-repair-pilot`  
**Status:** Defective snapshot prepared — repair **not** started.

| Path | Access |
|------|--------|
| `repair_workspace/` | Repair agent may use |
| `sealed_mutation_key/` | **Sealed** — not for repair agent |
| `snapshots/` | Record of baseline + defective copies |

Original `FreeRTOS/Demo/Common/Minimal/QueueSet.c` in the tree is **unchanged**.
Prior experiment results are untouched.
