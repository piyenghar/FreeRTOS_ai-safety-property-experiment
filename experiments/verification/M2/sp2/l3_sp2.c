/*
 * Independent L3 verification for SP2 — unauthorized privilege escalation.
 *
 * Oracle (independent of demo SP2 PASS strings):
 *   HOLD  <=> after portRAISE_PRIVILEGE(), task remains unprivileged (CONTROL.nPRIV==1)
 *             AND a write to the RO shared cell still MemFaults
 *             AND the cell value is unchanged.
 *
 * Build variants (MPU wrappers v2 baseline):
 *   pos — unprivileged restricted task; portRAISE_PRIVILEGE SVC is not granted
 *         (v2 rejects direct raise). Matches protected baseline behaviour.
 *   neg — same oracle, but task created privileged (portPRIVILEGE_BIT) so the
 *         post-condition of a successful escalation is present; oracle must
 *         report VIOLATION_DETECTED.
 *
 * Note: with configUSE_MPU_WRAPPERS_V1==0, flipping
 * configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY does not enable portRAISE_PRIVILEGE;
 * the SVC raise path exists only for wrappers v1. The negative control therefore
 * injects privilege at task creation inside this isolated build only.
 */
#include "FreeRTOS.h"
#include "task.h"
#include "l3_test.h"
#include "l3_uart.h"

#include <stdint.h>

#define SHARED_MEMORY_SIZE    32
#define L3_SP2_ATTACK         ( ( uint8_t ) 0x3C )

#ifndef L3_SP2_NEGATIVE
    #define L3_SP2_NEGATIVE    0
#endif

static volatile uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

static volatile uint8_t ucFaultTracker[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) ) = { 0 };

static void prvSP2Task( void * pvParameters );

static uint32_t ulReadControlNPriv( void )
{
    uint32_t ulControl;

    __asm volatile ( "mrs %0, control" : "=r" ( ulControl ) );
    return ( ulControl & 1UL );
}

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

static void prvSP2Task( void * pvParameters )
{
    uint8_t ucBefore;
    uint8_t ucAfter;
    uint32_t ulNPrivAfterRaise;
    BaseType_t xStillUnprivileged;
    BaseType_t xFaultOccurred;
    BaseType_t xValueUnchanged;
    BaseType_t xPropertyHolds;

    ( void ) pvParameters;

    for( ; ; )
    {
        /* Attempt the same escalation primitive the baseline demo uses. */
        portRAISE_PRIVILEGE();

        ulNPrivAfterRaise = ulReadControlNPriv();
        xStillUnprivileged = ( ulNPrivAfterRaise == 1UL ) ? pdTRUE : pdFALSE;

        ucBefore = ucSharedMemory[ 0 ];
        ucFaultTracker[ 0 ] = 1;
        ucSharedMemory[ 0 ] = L3_SP2_ATTACK;

        xFaultOccurred = ( ucFaultTracker[ 0 ] == 0 ) ? pdTRUE : pdFALSE;
        ucAfter = ucSharedMemory[ 0 ];
        xValueUnchanged = ( ucAfter == ucBefore ) ? pdTRUE : pdFALSE;

        xPropertyHolds = ( ( xStillUnprivileged == pdTRUE ) &&
                           ( xFaultOccurred == pdTRUE ) &&
                           ( xValueUnchanged == pdTRUE ) ) ? pdTRUE : pdFALSE;

        if( xStillUnprivileged == pdTRUE )
        {
            vL3Report( "L3_SP2_EVIDENCE: npriv_after_raise=1" );
        }
        else
        {
            vL3Report( "L3_SP2_EVIDENCE: npriv_after_raise=0" );
        }

        if( xFaultOccurred == pdTRUE )
        {
            vL3Report( "L3_SP2_EVIDENCE: memfault_seen=1" );
        }
        else
        {
            vL3Report( "L3_SP2_EVIDENCE: memfault_seen=0" );
            ucFaultTracker[ 0 ] = 0;
        }

        if( xValueUnchanged == pdTRUE )
        {
            vL3Report( "L3_SP2_EVIDENCE: value_unchanged=1" );
        }
        else
        {
            vL3Report( "L3_SP2_EVIDENCE: value_unchanged=0" );
        }

        if( xPropertyHolds == pdTRUE )
        {
            vL3Report( "L3_SP2_ORACLE: HOLD" );
        }
        else
        {
            vL3Report( "L3_SP2_ORACLE: VIOLATION_DETECTED" );
        }

#if ( L3_SP2_NEGATIVE == 1 )
        /* Stay privileged across iterations so the violated post-condition
         * remains stable (v2 cannot re-raise via portRAISE_PRIVILEGE). */
        ucSharedMemory[ 0 ] = 0;
#endif
        /* Positive path is already unprivileged; do not call
         * portSWITCH_TO_USER_MODE() here — on this port it can prevent
         * subsequent MPU system calls from completing. */
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
}
/*-----------------------------------------------------------*/

void vStartL3Verification( void )
{
    static StackType_t xSP2TaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( 1024 * sizeof( StackType_t ) ) ) );

    TaskParameters_t xSP2TaskParameters =
    {
        .pvTaskCode     = prvSP2Task,
        .pcName         = "L3_SP2",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
#if ( L3_SP2_NEGATIVE == 1 )
        /* Isolated negative control only: start privileged. */
        .uxPriority     = ( tskIDLE_PRIORITY | portPRIVILEGE_BIT ),
#else
        .uxPriority     = tskIDLE_PRIORITY,
#endif
        .puxStackBuffer = xSP2TaskStack,
        .xRegions       =
        {
            { ucSharedMemory,            SHARED_MEMORY_SIZE,
              portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |
              portMPU_REGION_EXECUTE_NEVER },
            { ( void * ) ucFaultTracker, SHARED_MEMORY_SIZE,
              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER },
            { 0,                         0,                 0 },
        }
    };

#if ( L3_SP2_NEGATIVE == 1 )
    vL3Report( "L3_SP2_CONTROL: negative" );
#else
    vL3Report( "L3_SP2_CONTROL: positive" );
#endif

    xTaskCreateRestricted( &( xSP2TaskParameters ), NULL );
}
