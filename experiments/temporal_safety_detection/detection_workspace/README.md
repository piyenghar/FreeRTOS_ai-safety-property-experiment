# Detection-agent workspace (P3 temporal safety pilot)

This tree contains the **instrumented MPU request-mailbox firmware sources**
under test for independent safety-property analysis.

## Layout
- `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/` — demo application + `mpu_demo.c`
- Build requires FreeRTOS-Kernel at `FreeRTOS/Source` relative to the demo’s
  usual repository layout (init submodule / point includes as in the main repo).

## Build / run (when Kernel is available)
```text
cd FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC
make DEBUG=1
# QEMU mps2-an385 with RTOSDemo.axf; capture UART
```

## Your task (future detection run)
Determine whether a **temporal** safety property is violated:
a request must not be acknowledged as successfully applied unless that
specific request was processed/applied. Use code review, build, and UART
evidence. Do not modify SP1/SP2 mechanisms or forge PASS strings.

This workspace does **not** include the sealed mutation key or hidden oracles.
