/*
 * Independent L3 verification for SP1 — read-only memory isolation.
 *
 * Oracle (independent of demo SP1 PASS strings):
 *   HOLD  <=> MemFault occurred on the unprivileged write
 *             AND the protected cell retained its pre-write value.
 *
 * Build variants (Makefile CONTROL=pos|neg):
 *   pos — region mapped privileged-RW / unprivileged-RO (baseline-equivalent).
 *   neg — region mapped RW so the write succeeds (oracle must detect violation).
 */
#include "FreeRTOS.h"
#include "task.h"
#include "l3_test.h"
#include "l3_uart.h"

#include <stdint.h>

#define SHARED_MEMORY_SIZE    32
#define L3_SP1_ATTACK         ( ( uint8_t ) 0x5A )

#ifndef L3_SP1_NEGATIVE
    #define L3_SP1_NEGATIVE    0
#endif

/* volatile: prevent the compiler from treating a faulted store's register
 * value as a successful memory write when reading back the oracle cell. */
static volatile uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

static volatile uint8_t ucFaultTracker[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) ) = { 0 };

static void prvSP1Task( void * pvParameters );

portDONT_DISCARD void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    uint32_t ulPC;
    uint16_t usOffendingInstruction;

    if( ucFaultTracker[ 0 ] == 1 )
    {
        ulPC = pulFaultStackAddress[ 6 ];
        usOffendingInstruction = *( uint16_t * ) ulPC;
        usOffendingInstruction = ( uint16_t ) ( ( usOffendingInstruction & 0xF800 ) >> 11 );

        if( ( usOffendingInstruction == 0x001F ) ||
            ( usOffendingInstruction == 0x001E ) ||
            ( usOffendingInstruction == 0x001D ) )
        {
            ulPC += 4;
        }
        else
        {
            ulPC += 2;
        }

        pulFaultStackAddress[ 6 ] = ulPC;
        ucFaultTracker[ 0 ] = 0;
    }
    else
    {
        for( ; ; )
        {
        }
    }
}
/*-----------------------------------------------------------*/

static void prvSP1Task( void * pvParameters )
{
    uint8_t ucBefore;
    uint8_t ucAfter;
    BaseType_t xFaultOccurred;
    BaseType_t xValueUnchanged;
    BaseType_t xPropertyHolds;

    ( void ) pvParameters;

    for( ; ; )
    {
        /* BSS / restore leaves a known zero cell before each attack write. */
        ucBefore = ucSharedMemory[ 0 ];

        ucFaultTracker[ 0 ] = 1;
        ucSharedMemory[ 0 ] = L3_SP1_ATTACK;

        xFaultOccurred = ( ucFaultTracker[ 0 ] == 0 ) ? pdTRUE : pdFALSE;
        ucAfter = ucSharedMemory[ 0 ];
        xValueUnchanged = ( ucAfter == ucBefore ) ? pdTRUE : pdFALSE;
        xPropertyHolds = ( ( xFaultOccurred == pdTRUE ) &&
                           ( xValueUnchanged == pdTRUE ) ) ? pdTRUE : pdFALSE;

        if( xFaultOccurred == pdTRUE )
        {
            vL3Report( "L3_SP1_EVIDENCE: memfault_seen=1" );
        }
        else
        {
            vL3Report( "L3_SP1_EVIDENCE: memfault_seen=0" );
            ucFaultTracker[ 0 ] = 0;
        }

        if( xValueUnchanged == pdTRUE )
        {
            vL3Report( "L3_SP1_EVIDENCE: value_unchanged=1" );
        }
        else
        {
            vL3Report( "L3_SP1_EVIDENCE: value_unchanged=0" );
        }

        if( xPropertyHolds == pdTRUE )
        {
            vL3Report( "L3_SP1_ORACLE: HOLD" );
        }
        else
        {
            vL3Report( "L3_SP1_ORACLE: VIOLATION_DETECTED" );
        }

#if ( L3_SP1_NEGATIVE == 1 )
        /* Clear the cell so the next negative iteration starts from zero. */
        ucSharedMemory[ 0 ] = 0;
#endif

        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
}
/*-----------------------------------------------------------*/

void vStartL3Verification( void )
{
    static StackType_t xSP1TaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( 1024 * sizeof( StackType_t ) ) ) );

    TaskParameters_t xSP1TaskParameters =
    {
        .pvTaskCode     = prvSP1Task,
        .pcName         = "L3_SP1",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
        .uxPriority     = tskIDLE_PRIORITY,
        .puxStackBuffer = xSP1TaskStack,
        .xRegions       =
        {
#if ( L3_SP1_NEGATIVE == 1 )
            { ucSharedMemory,            SHARED_MEMORY_SIZE,
              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER },
#else
            { ucSharedMemory,            SHARED_MEMORY_SIZE,
              portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |
              portMPU_REGION_EXECUTE_NEVER },
#endif
            { ( void * ) ucFaultTracker, SHARED_MEMORY_SIZE,
              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER },
            { 0,                         0,                 0 },
        }
    };

#if ( L3_SP1_NEGATIVE == 1 )
    vL3Report( "L3_SP1_CONTROL: negative" );
#else
    vL3Report( "L3_SP1_CONTROL: positive" );
#endif

    xTaskCreateRestricted( &( xSP1TaskParameters ), NULL );
}
