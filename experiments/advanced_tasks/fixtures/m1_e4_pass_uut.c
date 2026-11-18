/* Host-compilable PASS UUT for M1-E4 behavioural L2. */
#include "freertos_stubs.h"

/* M1_E4_DIAG */

static uint32_t ulM1E4Accepted;
static uint32_t ulM1E4Rejected;

void vM1E4GetRangeDiagnostics( uint32_t * pulAccepted,
                               uint32_t * pulRejected )
{
    if( pulAccepted != 0 )
    {
        *pulAccepted = ulM1E4Accepted;
    }
    if( pulRejected != 0 )
    {
        *pulRejected = ulM1E4Rejected;
    }
}

BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
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
        /* Count reject before assert; host L2 stubs longjmp on configASSERT. */
        ulM1E4Rejected++;
        configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );
        return pdFALSE;
    }

    configASSERT( ulDeviation <= queuesetALLOWABLE_RX_DEVIATION );
    ulM1E4Accepted++;
    return pdPASS;
}
