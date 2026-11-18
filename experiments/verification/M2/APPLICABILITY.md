# Applicability of M2 L3 harness to T1–T3 agent pilots

## Does this harness test pilot `mpu_demo.c` binaries?

**No.** The independent L3 builds compile standalone firmware:

- `common/l3_app_main.c` (not demo `app_main.c`)
- `sp1/l3_sp1.c` or `sp2/l3_sp2.c` (not pilot/`mpu_demo.c`)

They link the FreeRTOS MPU kernel and demo startup/syscall/main, but **do not compile or link** `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c` from `main`, T1, T2, or T3.

Therefore:

- SP1/SP2 pos/neg results validate the **oracle and MPU property semantics** on dedicated test firmware.
- They do **not** constitute independent L3 verification of agent-modified pilot binaries.
- Do **not** claim T1/T2/T3 L3 is independently verified by this harness alone.

The `results/baseline_mpu_demo.uart.log` capture only corroborates that a checkout’s existing demo still prints demo `SP1 PASS`/`SP2 PASS` strings; that is not the independent oracle path.

## Minimal integration to evaluate each pilot

1. Add Makefile targets (e.g. `PILOT=t1|t2|t3|main`) that build the demo tree using the pilot branch’s `mpu_demo.c` (worktree or `git show pilot/...:mpu_demo.c` into an isolated build dir).
2. Keep the independent oracle as a **host-side UART checker** (or a thin privileged observer) that asserts the same HOLD criteria against pilot UART/`CONTROL`/fault behaviour **without** replacing the pilot task code.
3. For each pilot positive run: boot the pilot binary; require independent HOLD evidence (MemFault + unchanged RO cell / nPRIV) while allowing pilot-specific lines (`T1_LOG`, refactor-only, `T3_CYCLE`).
4. Keep negative controls in isolated verification builds (already present); optionally also run them against a deliberately weakened copy of each pilot’s `mpu_demo.c` in an out-of-tree dir only.
5. Record per-pilot logs under `results/pilot_t{1,2,3}_*.uart.log` and gate “pilot L3 PASS” on those runs.
