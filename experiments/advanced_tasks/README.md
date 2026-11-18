# Advanced maintenance tasks (M1-R4 / M1-E4 / M2-R4 / M2-E4)

Integrated with existing M1/M2 verification oracles. **Does not** modify original T1–T3 campaigns or FreeRTOS safety sources.

| Path | Role |
|------|------|
| `config_m1.yaml` / `config_m2.yaml` | Task matrix (AI disabled) |
| `prompts/` | Frozen task prompts |
| `l2/` | Advanced L2 checkers + small-UUT harness |
| `scripts/run_m1_e4_l2_against_queueset.py` | M1-E4 L2 on real `QueueSet.c` |
| `scripts/run_integrated_validation.py` | Fixture L1/L2/L3 matrix |
| `scripts/dry_run_advanced.py` | End-to-end dry-run (no agents) |
| `scripts/verify_advanced_task.py` | Per-task L2+L3 hook |
| `REPRODUCTION.md` | Exact commands |
| `validation/` | Reports + results |

Design: `../ADVANCED_TASK_DESIGN.md`

```bash
python experiments/advanced_tasks/scripts/dry_run_advanced.py
```
