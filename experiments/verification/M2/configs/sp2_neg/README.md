# SP2 negative-control note

This directory previously held a FreeRTOSConfig.h that set
`configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY` to 0.

That override is **not** used by the current SP2 negative build.

Reason: the MPU demo uses `configUSE_MPU_WRAPPERS_V1 == 0`. Under wrappers
v2, the `portSVC_RAISE_PRIVILEGE` handler is not compiled, so flipping
`configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY` does not make
`portRAISE_PRIVILEGE()` succeed from an unprivileged task.

The SP2 negative control instead creates the verification task with
`portPRIVILEGE_BIT` inside `sp2/l3_sp2.c` (isolated verification source only).
