/* Controlled FAIL fixture: token present but mirrored branches remain (T2-like). */
#include <stdint.h>

typedef int32_t BaseType_t;
#define pdPASS    ( ( BaseType_t ) 1 )
#define pdFALSE   ( ( BaseType_t ) 0 )
#define queuesetALLOWABLE_RX_DEVIATION    3
#define configASSERT( x )    do { if( !( x ) ) { for( ;; ) {} } } while( 0 )

/* M1_R4_EXTRACT: marker only — no helper, duplicated branches retained. */

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
