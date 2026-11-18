# Hidden verification (sealed)

## P3 UART oracle
`p3_oracle.py` — deterministic parse of `MPU_REQ` lines.

## Consecutive / overlapping exercise
The firmware request sequence already issues valid then invalid requests
(e.g. `100` then `101`, `75` then `200`). The oracle requires:
- ≥1 valid ACCEPT with `observed == req`
- ≥1 request with `req > 100` present in the log

## Pass criteria summary
| Build | P3 | Single-req | SP1 | SP2 |
|-------|----|------------|-----|-----|
| Baseline | HOLD | PASS | HOLD | HOLD |
| Defective | VIOLATION | PASS | HOLD | HOLD |
| Defective L1 | PASS | — | — | — |
