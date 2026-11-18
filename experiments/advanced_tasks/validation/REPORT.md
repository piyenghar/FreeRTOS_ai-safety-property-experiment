# Advanced tasks — L2 validation report

**Cases:** 11
**Met expectation:** 11/11

| Case | Expected | Got | OK | Top failures |
|------|----------|-----|----|--------------|
| `M1-R4_baseline_QueueSet` | FAIL | FAIL | yes | missing_token_M1_R4_EXTRACT, missing_deviation_helper_called_from_check, duplicated_mirrored_assert_branches_remain |
| `M1-R4_fixture_pass` | PASS | PASS | yes | — |
| `M1-R4_fixture_marker_only` | FAIL | FAIL | yes | missing_deviation_helper_called_from_check, duplicated_mirrored_assert_branches_remain, multiple_allowable_deviation_asserts_in_check |
| `M1-E4_baseline_QueueSet_structural` | FAIL | FAIL | yes | missing_token_M1_E4_DIAG, missing_vM1E4GetRangeDiagnostics_signature |
| `M1-E4_fixture_pass_behavioural` | PASS | PASS | yes | — |
| `M1-E4_fixture_wrong_counts` | FAIL | FAIL | yes | behavioural_acceptance_failed |
| `M2-R4_baseline_mpu_demo` | FAIL | FAIL | yes | missing_token_M2_R4_STRUCT, missing_sp1_helper_called_from_ro_task, missing_sp2_helper_called_from_ro_task |
| `M2-R4_fixture_pass` | PASS | PASS | yes | — |
| `M2-E4_baseline_mpu_demo` | FAIL | FAIL | yes | missing_telemetry_prefix_in_source, telemetry_not_wired_to_uart_path, uart_log_required_for_m2_e4 |
| `M2-E4_fixture_pass` | PASS | PASS | yes | — |
| `M2-E4_fixture_non_monotonic_uart` | FAIL | FAIL | yes | uart_telemetry_not_monotonic_or_missing |

## Readiness

- Frozen prompts: `experiments/advanced_tasks/prompts/`
- Executable L2: `experiments/advanced_tasks/l2/check_advanced_l2.py`
- M1-E4 behavioural harness: `l2/m1_e4_behavioural_harness.c`
- Design: `experiments/ADVANCED_TASK_DESIGN.md`

## Remaining limitations

1. M1-E4 behavioural L2 requires a host-compilable UUT exposing `vM1E4GetRangeDiagnostics` + range-check (full `QueueSet.c` needs an extract/shim step before live campaigns).
2. M2 L2 for E4 requires a UART log capture; source-only is insufficient.
3. M2-R4 explicit-region check is heuristic (named macros/descriptors).
4. L3 not re-run here (intentionally independent); campaign integration pending.
5. No AI agent runs executed.

