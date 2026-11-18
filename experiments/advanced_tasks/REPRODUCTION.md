# Advanced tasks — exact reproduction commands

Run from repository root:

`F:\RDProjects\safetyProperties\FreeRTOS_ai-safety-property-experiment`

No Cursor CLI / paid models are invoked by these commands.

## 1. Generate controlled QueueSet / mpu_demo variants

```bash
python experiments/advanced_tasks/scripts/generate_variants.py
```

Outputs under `experiments/advanced_tasks/fixtures/generated/` (copies only; originals untouched).

## 2. Offline L2 unit validation (fixtures)

```bash
python experiments/advanced_tasks/l2/run_validation.py
```

## 3. M1-E4 behavioural L2 against a full QueueSet.c

```bash
python experiments/advanced_tasks/scripts/run_m1_e4_l2_against_queueset.py ^
  --queueset experiments/advanced_tasks/fixtures/generated/m1_e4_pass_QueueSet.c ^
  --out-dir experiments/advanced_tasks/validation/manual_m1_e4
```

Baseline (must FAIL L2):

```bash
python experiments/advanced_tasks/scripts/run_m1_e4_l2_against_queueset.py ^
  --queueset FreeRTOS/Demo/Common/Minimal/QueueSet.c ^
  --out-dir experiments/advanced_tasks/validation/manual_m1_e4_baseline
```

## 4. M1 L3 (existing oracle) against a variant

```bash
python experiments/m1_multimodel/scripts/run_l3_against_queueset.py ^
  --queueset experiments/advanced_tasks/fixtures/generated/m1_r4_pass_QueueSet.c ^
  --out-dir experiments/advanced_tasks/validation/manual_m1_l3
```

## 5. M2 L3 (existing oracle) on a UART log

```bash
python experiments/verification/M2/scripts/l3_pilot_oracle.py ^
  --mode pilot --pilot t2 --control pos --l1 PASS ^
  --log experiments/advanced_tasks/fixtures/m2_e4_pass.uart ^
  --out experiments/advanced_tasks/validation/manual_m2_l3.json ^
  --source-note advanced_tasks_repro
```

## 6. Integrated L1/L2/L3 fixture pipeline

```bash
python experiments/advanced_tasks/scripts/run_integrated_validation.py
```

Report: `experiments/advanced_tasks/validation/integrated/REPORT.md`  
JSON: `experiments/advanced_tasks/validation/integrated/latest.json`

## 7. End-to-end dry-run (configs + prompts + validation; no agents)

```bash
python experiments/advanced_tasks/scripts/dry_run_advanced.py
```

Report: `experiments/advanced_tasks/validation/DRY_RUN_REPORT.md`  
Per-run artifacts: `experiments/advanced_tasks/results/dryrun_<stamp>/`

## Config entry points

| File | Tasks |
|------|-------|
| `experiments/advanced_tasks/config_m1.yaml` | M1-R4, M1-E4 |
| `experiments/advanced_tasks/config_m2.yaml` | M2-R4, M2-E4 |

Prompts: `experiments/advanced_tasks/prompts/`  
`runtime.invoke_ai_models: false` — paid campaigns not enabled here.
