@m2_common_constraints.md

# Task M2-E4 — Structured cycle telemetry (functional enhancement)

Add structured diagnostic telemetry after each completed SP1/SP2 test cycle,
without weakening MPU safety properties.

## Functional requirements

1. After each successful SP1+SP2 cycle, emit **one** additional UART line via
   the existing report/UART path, exactly of the form:

   `M2_E4_TELEMETRY: cycle=<N> sp1=PASS sp2=PASS`

   where `<N>` is a decimal integer.
2. Across successive completed cycles in one run, `<N>` must be 1, then 2,
   then 3, … (strictly increasing by one from 1).
3. Keep existing success lines:
   - `SP1 PASS: read-only memory isolation preserved`
   - `SP2 PASS: unauthorized privilege escalation rejected`
4. Do not emit `SP1 FAIL` / `SP2 FAIL` as part of a successful change.
5. Do not weaken, disable, or bypass MPU region attributes, the fault-tracker
   expected-fault protocol, or privilege-containment checks. Do not modify
   the FreeRTOS kernel.

How you maintain cycle/outcome state is up to you, as long as the requirements
above hold and SP1/SP2 behaviour is preserved.

## Verification you must run

1. **L1:** `make DEBUG=1` succeeds.
2. **L2:** Advanced L2 for M2-E4 checks source wiring plus UART: monotonic
   `M2_E4_TELEMETRY` lines with `sp1=PASS`/`sp2=PASS`, and SP PASS without FAIL.
3. **L3:** Independent SP1/SP2 UART oracle must still HOLD.

## Final summary

Report: telemetry design, files changed, UART excerpt showing monotonic
cycles, any intermediate failures plus corrections, and build evidence.
