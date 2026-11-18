/* Controlled PASS fixture for M2-R4 structural L2 (synthetic mpu_demo fragment). */
#include <stdint.h>

#define SHARED_MEMORY_SIZE    32
#define portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY    1
#define portMPU_REGION_READ_WRITE    2
#define portMPU_REGION_EXECUTE_NEVER 4
#define portRAISE_PRIVILEGE()    do {} while( 0 )

/* M2_R4_STRUCT: explicit region descriptors + extracted SP helpers. */

#define M2_R4_SHARED_REGION_SIZE    SHARED_MEMORY_SIZE
#define M2_R4_RO_SHARED_ATTR        ( portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY | portMPU_REGION_EXECUTE_NEVER )
#define M2_R4_RW_SHARED_ATTR        ( portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )
#define M2_R4_FAULT_TRACKER_ATTR    ( portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )

static uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ];
static volatile uint8_t ucROTaskFaultTracker[ SHARED_MEMORY_SIZE ];

static void prvReportPropertyResult( const char * pcMessage )
{
    ( void ) pcMessage;
}

static void prvObserveSP1Isolation( void )
{
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

static void prvROAccessTask( void * pvParameters )
{
    ( void ) pvParameters;
    for( ;; )
    {
        prvObserveSP1Isolation();
        prvObserveSP2PrivilegeContainment();
    }
}

typedef struct
{
    void * pvBaseAddress;
    uint32_t ulLengthInBytes;
    uint32_t ulParameters;
} MemoryRegion_t;

void vStartMPUDemo( void )
{
    const MemoryRegion_t xROSharedRegion =
    {
        ucSharedMemory, M2_R4_SHARED_REGION_SIZE, M2_R4_RO_SHARED_ATTR
    };
    const MemoryRegion_t xFaultTrackerRegion =
    {
        ( void * ) ucROTaskFaultTracker, M2_R4_SHARED_REGION_SIZE, M2_R4_FAULT_TRACKER_ATTR
    };
    MemoryRegion_t xRegions[ 3 ];

    xRegions[ 0 ] = xROSharedRegion;
    xRegions[ 1 ] = xFaultTrackerRegion;
    xRegions[ 2 ].ulLengthInBytes = 0;
    ( void ) xRegions;
    ( void ) prvROAccessTask;
}

void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    ( void ) pulFaultStackAddress;
    if( ucROTaskFaultTracker[ 0 ] == 1 )
    {
        ucROTaskFaultTracker[ 0 ] = 0;
    }
    else
    {
        for( ;; )
        {
        }
    }
}
