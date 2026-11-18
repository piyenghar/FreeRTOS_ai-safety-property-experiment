/* Controlled PASS fixture for M1-R4 structural L2 (not production QueueSet). */
#include <stdint.h>

typedef int32_t BaseType_t;
#ifndef pdPASS
#define pdPASS    ( ( BaseType_t ) 1 )
#endif
#ifndef pdFALSE
#define pdFALSE   ( ( BaseType_t ) 0 )
#endif

#define queuesetALLOWABLE_RX_DEVIATION    3

#ifndef configASSERT
#define configASSERT( x )    do { if( !( x ) ) { for( ;; ) {} } } while( 0 )
#endif

/* M1_R4_EXTRACT: absolute deviation helper + unified assert/reject path. */

static uint32_t prvAbsoluteDeviation( uint32_t ulReceived,
                                      uint32_t ulExpectedReceived )
{
    if( ulReceived > ulExpectedReceived )
    {
        return ulReceived - ulExpectedReceived;
    }
    return ulExpectedReceived - ulReceived;
}

BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
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
