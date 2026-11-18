#!/usr/bin/env bash
set -uo pipefail
cd '/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/verification/M2'
L1=PASS
make PROPERTY=pilot_mpu CONTROL=neg PILOT_ID=claude_opus_5_5_medium_T1_r1_sp2neg PILOT_MPU_DEMO='/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/validity_revision/m2/sp2_neg/claude-opus-5-5-medium_T1_r1/claude-opus-5-5-medium_T1_r1_mpu_demo_sp2neg.c' DEBUG=1 > '/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/validity_revision/m2/sp2_neg/claude-opus-5-5-medium_T1_r1/make_sp2neg.log' 2>&1 || L1=FAIL
echo "$L1" > '/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/validity_revision/m2/sp2_neg/claude-opus-5-5-medium_T1_r1/L1_sp2neg_status.txt'
AXF='/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/verification/M2/build/pilot_claude_opus_5_5_medium_T1_r1_sp2neg_neg/RTOSDemo.axf'
echo "AXF=$AXF L1=$L1"
if [[ "$L1" == "PASS" && -f "$AXF" ]]; then
  timeout 8s qemu-system-arm -machine mps2-an385 -cpu cortex-m3 \
    -monitor none -semihosting --semihosting-config enable=on,target=native \
    -kernel "$AXF" -serial stdio -nographic > '/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/validity_revision/m2/sp2_neg/claude-opus-5-5-medium_T1_r1/sp2_negative.uart.log' 2>&1 || true
else
  echo BUILD_FAILED > '/mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/validity_revision/m2/sp2_neg/claude-opus-5-5-medium_T1_r1/sp2_negative.uart.log'
fi
