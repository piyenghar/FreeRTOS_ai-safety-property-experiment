/*
 * Verification-only extract of prvCheckReceivedValueWithinExpectedRange()
 * from FreeRTOS/Demo/Common/Minimal/QueueSet.c — logic kept equivalent.
 * QueueSet.c itself is not modified or compiled here.
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

    return xReturn;
}
