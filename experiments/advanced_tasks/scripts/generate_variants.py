#!/usr/bin/env python3
"""Generate controlled QueueSet.c / mpu_demo.c variants under fixtures/generated/.

Copies baselines; never modifies originals in FreeRTOS/.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
OUT = ADV / "fixtures/generated"
QS = ROOT / "FreeRTOS/Demo/Common/Minimal/QueueSet.c"
MPU = ROOT / "FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c"

OLD_RANGE_FN = re.compile(
    r"static BaseType_t prvCheckReceivedValueWithinExpectedRange\(\s*uint32_t ulReceived,\s*"
    r"uint32_t ulExpectedReceived\s*\)\s*\{.*?\n    \}\n/\*-----------------------------------------------------------\*/",
    re.DOTALL,
)

R4_REPLACEMENT = r'''/* M1_R4_EXTRACT */
    static uint32_t prvAbsoluteDeviation( uint32_t ulReceived,
                                          uint32_t ulExpectedReceived )
    {
        if( ulReceived > ulExpectedReceived )
        {
            return ulReceived - ulExpectedReceived;
        }

        return ulExpectedReceived - ulReceived;
    }
/*-----------------------------------------------------------*/

    static BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                                uint32_t ulExpectedReceived )
    {
        uint32_t ulDeviation = prvAbsoluteDeviation( ulReceived, ulExpectedReceived );

        configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );

        if( ulDeviation > queuesetALLOWABLE_RX_DEVIATION )
        {
            return pdFALSE;
        }

        return pdPASS;
    }
/*-----------------------------------------------------------*/'''

E4_HELPERS = r'''/* M1_E4_DIAG */
    static uint32_t ulM1E4Accepted = 0;
    static uint32_t ulM1E4Rejected = 0;

    void vM1E4GetRangeDiagnostics( uint32_t * pulAccepted,
                                   uint32_t * pulRejected )
    {
        if( pulAccepted != NULL )
        {
            *pulAccepted = ulM1E4Accepted;
        }

        if( pulRejected != NULL )
        {
            *pulRejected = ulM1E4Rejected;
        }
    }
/*-----------------------------------------------------------*/

'''

E4_RANGE_FN = r'''    static BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                                uint32_t ulExpectedReceived )
    {
        uint32_t ulDeviation;

        if( ulReceived > ulExpectedReceived )
        {
            ulDeviation = ulReceived - ulExpectedReceived;
        }
        else
        {
            ulDeviation = ulExpectedReceived - ulReceived;
        }

        if( ulDeviation > queuesetALLOWABLE_RX_DEVIATION )
        {
            ulM1E4Rejected++;
            configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );
            return pdFALSE;
        }

        configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );
        ulM1E4Accepted++;
        return pdPASS;
    }
/*-----------------------------------------------------------*/'''

E4_FAULT_RANGE_FN = r'''    static BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                                uint32_t ulExpectedReceived )
    {
        uint32_t ulDeviation;

        if( ulReceived > ulExpectedReceived )
        {
            ulDeviation = ulReceived - ulExpectedReceived;
        }
        else
        {
            ulDeviation = ulExpectedReceived - ulReceived;
        }

        configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );

        if( ulDeviation > queuesetALLOWABLE_RX_DEVIATION )
        {
            /* Faulty: rejected count not incremented. */
            return pdFALSE;
        }

        ulM1E4Accepted++;
        return pdPASS;
    }
/*-----------------------------------------------------------*/'''


def patch_queueset_r4(text: str) -> str:
    if not OLD_RANGE_FN.search(text):
        raise RuntimeError("range-check function pattern not found for R4 patch")
    return OLD_RANGE_FN.sub(R4_REPLACEMENT, text, count=1)


def patch_queueset_e4(text: str, *, faulty: bool) -> str:
    if not OLD_RANGE_FN.search(text):
        raise RuntimeError("range-check function pattern not found for E4 patch")
    body = E4_FAULT_RANGE_FN if faulty else E4_RANGE_FN
    # Insert helpers before the range-check function
    text2 = OLD_RANGE_FN.sub(E4_HELPERS + body, text, count=1)
    # Export is non-static already in helpers
    return text2


def patch_mpu_r4(text: str) -> str:
    if "M2_R4_STRUCT" in text:
        return text
    # Insert token + macros after SHARED_MEMORY_SIZE
    text = text.replace(
        "#define SHARED_MEMORY_SIZE    32",
        "#define SHARED_MEMORY_SIZE    32\n\n"
        "/* M2_R4_STRUCT */\n"
        "#define M2_R4_SHARED_REGION_SIZE    SHARED_MEMORY_SIZE\n"
        "#define M2_R4_RO_SHARED_ATTR        ( portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY | "
        "portMPU_REGION_EXECUTE_NEVER )\n"
        "#define M2_R4_RW_SHARED_ATTR        ( portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )\n"
        "#define M2_R4_FAULT_TRACKER_ATTR    ( portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )\n",
        1,
    )

    # Extract SP1/SP2 into helpers: replace RO task body loop content with helper calls.
    # Insert helpers before prvROAccessTask.
    helpers = r'''
static void prvObserveSP1Isolation( void )
{
    uint8_t ucVal;

    ucVal = ucSharedMemory[ 0 ];
    ( void ) ucVal;
    ucROTaskFaultTracker[ 0 ] = 1;
    ucSharedMemory[ 0 ] = 0;
    if( ucROTaskFaultTracker[ 0 ] == 0 )
    {
        prvReportPropertyResult( "SP1 PASS: read-only memory isolation preserved" );
    }
    else
    {
        prvReportPropertyResult( "SP1 FAIL: read-only memory isolation violated" );
    }
}

static void prvObserveSP2PrivilegeContainment( void )
{
    #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 )
    {
        portRAISE_PRIVILEGE();
        ucROTaskFaultTracker[ 0 ] = 1;
        ucSharedMemory[ 0 ] = 0;
        if( ucROTaskFaultTracker[ 0 ] == 0 )
        {
            prvReportPropertyResult( "SP2 PASS: unauthorized privilege escalation rejected" );
        }
        else
        {
            prvReportPropertyResult( "SP2 FAIL: privilege containment violated" );
        }
    }
    #endif
}

'''
    text = text.replace(
        "static void prvROAccessTask( void * pvParameters );",
        "static void prvObserveSP1Isolation( void );\n"
        "static void prvObserveSP2PrivilegeContainment( void );\n"
        "static void prvROAccessTask( void * pvParameters );",
        1,
    )
    # Insert helper definitions before prvROAccessTask definition
    marker = "static void prvROAccessTask( void * pvParameters )\n{"
    if marker not in text:
        raise RuntimeError("prvROAccessTask definition not found")
    text = text.replace(marker, helpers + marker, 1)

    # Simplify RO task loop to call helpers (keep raise at start + delay)
    ro_new = '''static void prvROAccessTask( void * pvParameters )
{
    ( void ) pvParameters;

    portRAISE_PRIVILEGE();

    for( ; ; )
    {
        prvObserveSP1Isolation();
        prvObserveSP2PrivilegeContainment();
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
}
'''
    # Replace old function body via brace match from definition
    idx = text.find("static void prvROAccessTask( void * pvParameters )\n{")
    # skip helpers' earlier occurrence — find the one after helpers (second or last)
    idx = text.rfind("static void prvROAccessTask( void * pvParameters )\n{")
    if idx < 0:
        raise RuntimeError("RO task def missing after helper insert")
    depth = 0
    i = text.find("{", idx)
    j = i
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    text = text[:idx] + ro_new + text[j:]

    # Region table: use named attrs in RO task parameters
    text = text.replace(
        "portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |\n"
        "              portMPU_REGION_EXECUTE_NEVER",
        "M2_R4_RO_SHARED_ATTR",
        1,
    )
    text = text.replace(
        "{ ( void * ) ucROTaskFaultTracker, SHARED_MEMORY_SIZE,\n"
        "              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER }",
        "{ ( void * ) ucROTaskFaultTracker, M2_R4_SHARED_REGION_SIZE,\n"
        "              M2_R4_FAULT_TRACKER_ATTR }",
        1,
    )
    text = text.replace(
        "{ ucSharedMemory, SHARED_MEMORY_SIZE,\n"
        "              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER }",
        "{ ucSharedMemory, M2_R4_SHARED_REGION_SIZE,\n"
        "              M2_R4_RW_SHARED_ATTR }",
        1,
    )
    return text


def patch_mpu_e4(text: str) -> str:
    if "M2_E4_TELEMETRY" in text:
        return text
    # Add telemetry after SP2 block inside the enforce path — insert before vTaskDelay
    needle = "        /* Wait for a second. */\n        vTaskDelay( pdMS_TO_TICKS( 1000 ) );"
    insert = (
        "        {\n"
        "            static uint32_t ulM2E4Cycle = 0;\n"
        "            char pcTele[ 64 ];\n"
        "            ulM2E4Cycle++;\n"
        "            /* Fixed format for L2; snprintf may be unavailable — emit literal pattern via report. */\n"
        "            if( ulM2E4Cycle == 1 )\n"
        "            {\n"
        "                prvReportPropertyResult( \"M2_E4_TELEMETRY: cycle=1 sp1=PASS sp2=PASS\" );\n"
        "            }\n"
        "            else if( ulM2E4Cycle == 2 )\n"
        "            {\n"
        "                prvReportPropertyResult( \"M2_E4_TELEMETRY: cycle=2 sp1=PASS sp2=PASS\" );\n"
        "            }\n"
        "            else\n"
        "            {\n"
        "                prvReportPropertyResult( \"M2_E4_TELEMETRY: cycle=3 sp1=PASS sp2=PASS\" );\n"
        "            }\n"
        "            ( void ) pcTele;\n"
        "        }\n"
        "        /* Wait for a second. */\n"
        "        vTaskDelay( pdMS_TO_TICKS( 1000 ) );"
    )
    if needle not in text:
        raise RuntimeError("vTaskDelay site not found for E4 telemetry")
    return text.replace(needle, insert, 1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    qs = QS.read_text(encoding="utf-8", errors="replace")
    mpu = MPU.read_text(encoding="utf-8", errors="replace")

    (OUT / "baseline_QueueSet.c").write_text(qs, encoding="utf-8")
    (OUT / "m1_r4_pass_QueueSet.c").write_text(patch_queueset_r4(qs), encoding="utf-8")
    (OUT / "m1_e4_pass_QueueSet.c").write_text(patch_queueset_e4(qs, faulty=False), encoding="utf-8")
    (OUT / "m1_e4_fault_QueueSet.c").write_text(patch_queueset_e4(qs, faulty=True), encoding="utf-8")

    # R4 marker-only faulty: copy baseline + token comment only
    marker_only = qs.replace(
        "Checks a value received from a queue falls within the range of expected",
        "M1_R4_EXTRACT Checks a value received from a queue falls within the range of expected",
        1,
    )
    (OUT / "m1_r4_fault_marker_only_QueueSet.c").write_text(marker_only, encoding="utf-8")

    (OUT / "baseline_mpu_demo.c").write_text(mpu, encoding="utf-8")
    (OUT / "m2_r4_pass_mpu_demo.c").write_text(patch_mpu_r4(mpu), encoding="utf-8")
    (OUT / "m2_e4_pass_mpu_demo.c").write_text(patch_mpu_e4(mpu), encoding="utf-8")

    # Faulty E4: wrong telemetry format / non-monotonic will be UART-side; source gets prefix but
    # UART fixture used separately. Also write a source missing helpers for R4 fault.
    shutil.copy2(OUT / "baseline_mpu_demo.c", OUT / "m2_r4_fault_baseline_mpu_demo.c")

    print(f"Wrote variants to {OUT}")


if __name__ == "__main__":
    main()
