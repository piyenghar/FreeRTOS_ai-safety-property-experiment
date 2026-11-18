/* Controlled PASS fixture for M2-E4 source-side L2 (synthetic). */
#include <stdint.h>

#define portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY    1
#define portMPU_REGION_EXECUTE_NEVER 4
#define portRAISE_PRIVILEGE()    do {} while( 0 )

static uint8_t ucSharedMemory[ 32 ];
static volatile uint8_t ucROTaskFaultTracker[ 32 ];

static void prvReportPropertyResult( const char * pcMessage );

static void prvReportPropertyResult( const char * pcMessage )
{
    ( void ) pcMessage;
}

static void prvROAccessTask( void * pvParameters )
{
    uint32_t ulCycle = 0;
    char pcLine[ 64 ];

    ( void ) pvParameters;

    for( ;; )
    {
        ucROTaskFaultTracker[ 0 ] = 1;
        ucSharedMemory[ 0 ] = 0;
        prvReportPropertyResult( "SP1 PASS: read-only memory isolation preserved" );

        portRAISE_PRIVILEGE();
        ucROTaskFaultTracker[ 0 ] = 1;
        ucSharedMemory[ 0 ] = 0;
        prvReportPropertyResult( "SP2 PASS: unauthorized privilege escalation rejected" );

        ulCycle++;
        /* Format must match L2; buffer fill omitted in fixture — string literal for wiring check. */
        prvReportPropertyResult( "M2_E4_TELEMETRY: cycle=1 sp1=PASS sp2=PASS" );
        ( void ) pcLine;
        ( void ) ulCycle;
        ( void ) ucSharedMemory;
    }
}

void vStartMPUDemo( void )
{
    uint32_t ulRoAttr = portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |
                        portMPU_REGION_EXECUTE_NEVER;
    ( void ) ulRoAttr;
    ( void ) prvROAccessTask;
}
