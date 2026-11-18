/*
 * AUTO-GENERATED for M1 multimodel L3 — do not edit by hand.
 * Source: F:/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment/experiments/m1_multimodel/wt/r01/FreeRTOS/Demo/Common/Minimal/QueueSet.c
 * sha256: 895cccd1244ce1046c85200f2de166cbc2bc35a4416c8c8967118560ead6953e
 * queuesetALLOWABLE_RX_DEVIATION observed in source: 3
 *
 * Linked against experiments/verification/M1/l3/l3_range_test.c
 * using freertos_stubs.h (configASSERT -> longjmp for P2 scoring).
 */
#include "freertos_stubs.h"

BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                                uint32_t ulExpectedReceived )
    {
        BaseType_t xReturn = pdPASS;

        if( ulReceived > ulExpectedReceived )
        {
            configASSERT( ( ulReceived - ulExpectedReceived ) <= queuesetALLOWABLE_RX_DEVIATION );

            if( ( ulReceived - ulExpectedReceived ) > queuesetALLOWABLE_RX_DEVIATION )
            {
                xReturn = pdFALSE;
            }
        }
        else
        {
            configASSERT( ( ulExpectedReceived - ulReceived ) <= queuesetALLOWABLE_RX_DEVIATION );

            if( ( ulExpectedReceived - ulReceived ) > queuesetALLOWABLE_RX_DEVIATION )
            {
                xReturn = pdFALSE;
            }
        }

        /* M1_T1_LOG: record the range-check outcome before returning it. */
        prvLogRangeCheckResult( ulReceived, ulExpectedReceived, xReturn );

        return xReturn;
    }
