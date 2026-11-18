/*
 * FreeRTOS V202212.00
 * Copyright (C) 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of
 * this software and associated documentation files (the "Software"), to deal in
 * the Software without restriction, including without limitation the rights to
 * use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 * the Software, and to permit persons to whom the Software is furnished to do so,
 * subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 * https://www.FreeRTOS.org
 * https://github.com/FreeRTOS
 *
 */

/* FreeRTOS includes. */
#include "FreeRTOS.h"
#include "FreeRTOSConfig.h"
#include "task.h"

#include <stdint.h>

/** ARMv7 MPU Details:
 *
 * - ARMv7 MPU requires that the size of a MPU region is a power of 2.
 * - Smallest supported region size is 32 bytes.
 * - Start address of a region must be aligned to an integer multiple of the
 *   region size. For example, if the region size is 4 KB(0x1000), the starting
 *   address must be N x 0x1000, where N is an integer.
 */

/**
 * @brief Size of the shared memory region.
 */
#define SHARED_MEMORY_SIZE             32

/**
 * @brief Values of ucROTaskFaultTracker[ 0 ].
 *
 * FAULT_TRACKER_ARMED tells the Memory Fault Handler that the next MemFault is
 * expected. The handler sets FAULT_TRACKER_HANDLED after recovering from it.
 */
#define FAULT_TRACKER_ARMED            ( ( uint8_t ) 1 )
#define FAULT_TRACKER_HANDLED          ( ( uint8_t ) 0 )

/**
 * @brief CMSDK UART0 DATA register. Same address used by syscall.c.
 */
#define UART0_DATA_REGISTER_ADDRESS    ( 0x40004000UL )

/**
 * @brief Index of the stacked PC in the exception stack frame.
 */
#define STACKED_PC_INDEX               ( 6 )

/**
 * @brief Thumb instruction decoding.
 *
 * From ARM docs: if bits[15:11] of the halfword being decoded are 0b11101,
 * 0b11110 or 0b11111, the halfword is the first halfword of a 32-bit
 * instruction. Otherwise, the halfword is a 16-bit instruction.
 */
#define THUMB_PREFIX_MASK              ( 0xF800U )
#define THUMB_PREFIX_SHIFT             ( 11U )
#define THUMB_32BIT_PREFIX_0b11101     ( 0x001DU )
#define THUMB_32BIT_PREFIX_0b11110     ( 0x001EU )
#define THUMB_32BIT_PREFIX_0b11111     ( 0x001FU )

/**
 * @brief Delay between two iterations of the demo tasks.
 */
#define DEMO_TASK_PERIOD_MS            ( 1000 )

/**
 * @brief Memory region shared between two tasks.
 */
static uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ] __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

/**
 * @brief Memory region used to track Memory Fault intentionally caused by the
 * RO Access task.
 *
 * RO Access task sets ucROTaskFaultTracker[ 0 ] to FAULT_TRACKER_ARMED before
 * accessing illegal memory. Illegal memory access causes Memory Fault and the
 * fault handler checks ucROTaskFaultTracker[ 0 ] to see if this is an expected
 * fault. We recover gracefully from an expected fault by jumping to the next
 * instruction.
 *
 * @note We are declaring a region of 32 bytes even though we need only one.
 * The reason is that the smallest supported MPU region size is 32 bytes.
 */
static volatile uint8_t ucROTaskFaultTracker[ SHARED_MEMORY_SIZE ] __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) ) = { 0 };
/*-----------------------------------------------------------*/

/**
 * @brief Implements the task which has Read Only access to the memory region
 * ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvROAccessTask( void * pvParameters );

/**
 * @brief Implements the task which has Read Write access to the memory region
 * ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvRWAccessTask( void * pvParameters );

/**
 * @brief Print one safety-property result on UART0.
 *
 * The read-only task runs unprivileged, so it cannot call printf(): C library
 * globals lie outside its MPU regions. UART0 is already inside the
 * general-peripherals region, which is readable and writable by unprivileged
 * code. This does not change any MPU permission.
 */
static void prvReportPropertyResult( const char * pcMessage );

/**
 * @brief Report pcPassMessage if xPassed is pdTRUE, pcFailMessage otherwise.
 */
static void prvReportPropertyVerdict( BaseType_t xPassed,
                                      const char * pcPassMessage,
                                      const char * pcFailMessage );

/**
 * @brief Write to ucSharedMemory while telling the fault handler that a
 * MemFault is expected.
 *
 * @return pdTRUE if the write raised a MemFault that the handler recovered
 * from, pdFALSE if the write was not rejected by the MPU.
 */
static BaseType_t prvWriteSharedMemoryExpectingFault( void );

/**
 * @brief SP1: an unprivileged write to the read-only region must be rejected.
 */
static void prvCheckReadOnlyIsolation( void );

/**
 * @brief SP2: privilege escalation outside kernel code must be rejected.
 */
static void prvCheckPrivilegeEscalation( void );

/**
 * @brief Size in bytes (2 or 4) of the Thumb instruction whose first halfword
 * is usFirstHalfword.
 */
static uint32_t prvGetThumbInstructionSize( uint16_t usFirstHalfword );

/*-----------------------------------------------------------*/

static void prvReportPropertyResult( const char * pcMessage )
{
    volatile uint32_t * const pulUartData = ( volatile uint32_t * ) UART0_DATA_REGISTER_ADDRESS;

    while( *pcMessage != '\0' )
    {
        *pulUartData = ( uint32_t ) ( ( uint8_t ) *pcMessage );
        pcMessage++;
    }

    *pulUartData = ( uint32_t ) '\n';
}
/*-----------------------------------------------------------*/

static void prvReportPropertyVerdict( BaseType_t xPassed,
                                      const char * pcPassMessage,
                                      const char * pcFailMessage )
{
    if( xPassed == pdTRUE )
    {
        prvReportPropertyResult( pcPassMessage );
    }
    else
    {
        prvReportPropertyResult( pcFailMessage );
    }
}
/*-----------------------------------------------------------*/

static BaseType_t prvWriteSharedMemoryExpectingFault( void )
{
    ucROTaskFaultTracker[ 0 ] = FAULT_TRACKER_ARMED;

    /* Must fault while the task is unprivileged. The volatile access keeps the
     * store between arming and checking the tracker. */
    *( ( volatile uint8_t * ) &( ucSharedMemory[ 0 ] ) ) = 0;

    /* The fault handler clears the tracker only after the expected MPU fault. */
    return ( ucROTaskFaultTracker[ 0 ] == FAULT_TRACKER_HANDLED ) ? pdTRUE : pdFALSE;
}
/*-----------------------------------------------------------*/

static void prvCheckReadOnlyIsolation( void )
{
    uint8_t ucVal;

    /* This task has RO access to ucSharedMemory and therefore it can read it
     * but cannot modify it. */
    ucVal = ucSharedMemory[ 0 ];
    ( void ) ucVal;

    prvReportPropertyVerdict( prvWriteSharedMemoryExpectingFault(),
                              "SP1 PASS: read-only memory isolation preserved",
                              "SP1 FAIL: read-only memory isolation violated" );
}
/*-----------------------------------------------------------*/

static void prvCheckPrivilegeEscalation( void )
{
    #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 )
    {
        /* Privilege escalation is only allowed from kernel code, so this
         * request must get rejected and the task must remain unprivileged. */
        portRAISE_PRIVILEGE();

        /* A second MPU fault after the rejected privilege request means the
         * task is still unprivileged. */
        prvReportPropertyVerdict( prvWriteSharedMemoryExpectingFault(),
                                  "SP2 PASS: unauthorized privilege escalation rejected",
                                  "SP2 FAIL: privilege containment violated" );
    }
    #else /* if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
    {
        BaseType_t xFaulted;

        /* configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY is not enabled, so the
         * task will be able to escalate privilege. */
        portRAISE_PRIVILEGE();

        /* The task is now privileged, so this write must not fault. The
         * tracker is not armed, so an unexpected fault stops execution in the
         * fault handler. */
        ucSharedMemory[ 0 ] = 0;

        portSWITCH_TO_USER_MODE();

        /* The task is unprivileged again, so this write must fault. */
        xFaulted = prvWriteSharedMemoryExpectingFault();
        configASSERT( xFaulted == pdTRUE );
        ( void ) xFaulted;
    }
    #endif /* #if( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
}
/*-----------------------------------------------------------*/

static void prvROAccessTask( void * pvParameters )
{
    /* Unused parameters. */
    ( void ) pvParameters;

    portRAISE_PRIVILEGE();

    for( ; ; )
    {
        prvCheckReadOnlyIsolation();
        prvCheckPrivilegeEscalation();

        vTaskDelay( pdMS_TO_TICKS( DEMO_TASK_PERIOD_MS ) );
    }
}
/*-----------------------------------------------------------*/

static void prvRWAccessTask( void * pvParameters )
{
    /* Unused parameters. */
    ( void ) pvParameters;

    for( ; ; )
    {
        /* This task has RW access to ucSharedMemory and therefore can write to
         * it. */
        ucSharedMemory[ 0 ] = 0;

        vTaskDelay( pdMS_TO_TICKS( DEMO_TASK_PERIOD_MS ) );
    }
}
/*-----------------------------------------------------------*/

void vStartMPUDemo( void )
{
/**
 * Since stack of a task is protected using MPU, it must satisfy MPU
 * requirements as mentioned at the top of this file.
 */
    static StackType_t xROAccessTaskStack[ configMINIMAL_STACK_SIZE ]
    __attribute__( ( aligned( 1024 * sizeof( StackType_t ) ) ) );
    static StackType_t xRWAccessTaskStack[ configMINIMAL_STACK_SIZE ]
    __attribute__( ( aligned( 1024 * sizeof( StackType_t ) ) ) );

    TaskParameters_t xROAccessTaskParameters =
    {
        .pvTaskCode     = prvROAccessTask,
        .pcName         = "ROAccess",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
        .uxPriority     = tskIDLE_PRIORITY,
        .puxStackBuffer = xROAccessTaskStack,
        .xRegions       =
        {
            { ucSharedMemory,                  SHARED_MEMORY_SIZE,
              portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |
              portMPU_REGION_EXECUTE_NEVER },
            { ( void * ) ucROTaskFaultTracker, SHARED_MEMORY_SIZE,
              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER },
            { 0,                               0,                 0},
        }
    };

    TaskParameters_t xRWAccessTaskParameters =
    {
        .pvTaskCode     = prvRWAccessTask,
        .pcName         = "RWAccess",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
        .uxPriority     = tskIDLE_PRIORITY,
        .puxStackBuffer = xRWAccessTaskStack,
        .xRegions       =
        {
            { ucSharedMemory, SHARED_MEMORY_SIZE,
              portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER },
            { 0,              0,                 0  },
            { 0,              0,                 0  },
        }
    };

    /* Create an unprivileged task with RO access to ucSharedMemory. */
    xTaskCreateRestricted( &( xROAccessTaskParameters ), NULL );

    /* Create an unprivileged task with RW access to ucSharedMemory. */
    xTaskCreateRestricted( &( xRWAccessTaskParameters ), NULL );
}
/*-----------------------------------------------------------*/

static uint32_t prvGetThumbInstructionSize( uint16_t usFirstHalfword )
{
    uint16_t usPrefix = ( uint16_t ) ( ( usFirstHalfword & THUMB_PREFIX_MASK ) >> THUMB_PREFIX_SHIFT );
    uint32_t ulSize;

    if( ( usPrefix == THUMB_32BIT_PREFIX_0b11111 ) ||
        ( usPrefix == THUMB_32BIT_PREFIX_0b11110 ) ||
        ( usPrefix == THUMB_32BIT_PREFIX_0b11101 ) )
    {
        ulSize = 4;
    }
    else
    {
        ulSize = 2;
    }

    return ulSize;
}
/*-----------------------------------------------------------*/

portDONT_DISCARD void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    uint32_t ulPC;

    /* Is this an expected fault? */
    if( ucROTaskFaultTracker[ 0 ] == FAULT_TRACKER_ARMED )
    {
        /* Skip the offending instruction by advancing the stacked PC. */
        ulPC = pulFaultStackAddress[ STACKED_PC_INDEX ];
        ulPC += prvGetThumbInstructionSize( *( uint16_t * ) ulPC );
        pulFaultStackAddress[ STACKED_PC_INDEX ] = ulPC;

        /* Mark the fault as handled. */
        ucROTaskFaultTracker[ 0 ] = FAULT_TRACKER_HANDLED;
    }
    else
    {
        /* This is an unexpected fault - loop forever. */
        for( ; ; )
        {
        }
    }
}
/*-----------------------------------------------------------*/
