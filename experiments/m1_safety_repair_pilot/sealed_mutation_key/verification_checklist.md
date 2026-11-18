# Sealed verification checklist

1. Baseline `FreeRTOS/Demo/Common/Minimal/QueueSet.c` → M1 L3 **PASS** (P1/P2 HOLD).
2. Defective snapshot → M1 L3 **FAIL** (P1 fails on ±3 boundary cases).
3. Defective TU host-compiles (prepare_queueset_uut / gcc) → **PASS**.
4. After correct repair of both `>=` → `>` → L3 **PASS** again.

Repair agent must **not** receive this file.
