# M1 multi-model experiment (range checking)

DSN 2027 safety-constrained alignment study — **M1 / P1 / P2**.  
Separate from the completed M2 campaign under `experiments/multimodel/`.

## Layout

- `config.yaml` — 3 models × 3 tasks × 3 reps (= 27)
- `prompts/` — frozen T1/T2/T3 + common P1/P2 constraints
- `scripts/extract_range_check.py` — extract range-check fn from agent `QueueSet.c`
- `scripts/run_l3_against_queueset.py` — host L3 against that extract
- `scripts/run_campaign_m1.py` — dry-run / (future) live orchestrator
- `results/` — dry-run and campaign outputs
- `wt/` — short-slot worktrees (gitignored)

## Dry-run (no AI models)

```powershell
python experiments/m1_multimodel/scripts/run_campaign_m1.py --dry-run --sample-worktree
```

## L3 design

Each run’s L3 **does not** score the frozen reference
`experiments/verification/M1/l3/range_check_under_test.c`.

It prepares the **full agent-modified `QueueSet.c`** as a host UUT
(`scripts/prepare_queueset_uut.py` + `l3_harness/` FreeRTOS shims), preserving
helpers/statics (e.g. T1 `prvLogRangeCheckResult`), exports the range-check
symbol, and links it with the existing host tests (`l3_range_test.c`).
Requires P1/P2 plus oracle positive/negative controls.
