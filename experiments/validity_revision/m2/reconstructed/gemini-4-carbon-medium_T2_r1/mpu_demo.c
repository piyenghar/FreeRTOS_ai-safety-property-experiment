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

/* Demo includes. */
#include "mpu_demo.h"

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
 * @brief Size and alignment (in bytes) of the shared and fault-tracker MPU regions.
 */
#define SHARED_MEMORY_SIZE                   32

/**
 * @brief Shared-memory and fault-tracker indices/values used by the demo probes.
 */
#define SHARED_MEMORY_TEST_INDEX             ( 0U )
#define SHARED_MEMORY_WRITE_VALUE            ( 0U )
#define FAULT_TRACKER_SLOT_INDEX             ( 0U )
#define FAULT_TRACKER_CLEARED                ( 0U )
#define FAULT_TRACKER_FAULT_EXPECTED         ( 1U )

/**
 * @brief Task configuration constants for the MPU demo tasks.
 */
#define DEMO_TASK_STACK_ALIGNMENT_BYTES      ( 1024U * sizeof( StackType_t ) )
#define DEMO_LOOP_DELAY_TICKS                ( pdMS_TO_TICKS( 1000UL ) )
#define RO_TASK_SHARED_MEMORY_PERMISSIONS    ( portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY | \
                                               portMPU_REGION_EXECUTE_NEVER )
#define UNPRIV_READ_WRITE_DATA_PERMISSIONS   ( portMPU_REGION_READ_WRITE | \
                                               portMPU_REGION_EXECUTE_NEVER )

/**
 * @brief CMSDK UART0 data register (accessible from unprivileged peripheral region).
 */
#define CMSDK_UART0_DATA_REG                 ( ( volatile uint32_t * ) 0x40004000UL )

/**
 * @brief Cortex-M exception frame and Thumb-2 instruction decoding constants.
 */
#define FAULT_STACK_PC_OFFSET                ( 6U )
#define THUMB_32BIT_PREFIX_MASK              ( 0xF800U )
#define THUMB_32BIT_PREFIX_SHIFT             ( 11U )
#define THUMB_32BIT_PREFIX_11101             ( 0x001DU )
#define THUMB_32BIT_PREFIX_11110             ( 0x001EU )
#define THUMB_32BIT_PREFIX_11111             ( 0x001FU )
#define THUMB_32BIT_INSTRUCTION_BYTES        ( 4UL )
#define THUMB_16BIT_INSTRUCTION_BYTES        ( 2UL )

/**
 * @brief UART messages reporting SP1 and SP2 safety property outcomes.
 */
#define SP1_PASS_MESSAGE                     "SP1 PASS: read-only memory isolation preserved"
#define SP1_FAIL_MESSAGE                     "SP1 FAIL: read-only memory isolation violated"
#define SP2_PASS_MESSAGE                     "SP2 PASS: unauthorized privilege escalation rejected"
#define SP2_FAIL_MESSAGE                     "SP2 FAIL: privilege containment violated"

/**
 * @brief Memory region shared between the ROAccess and RWAccess tasks.
 */
static uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ] __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

/**
 * @brief Memory region used to track Memory Fault intentionally caused by the
 * RO Access task.
 *
 * RO Access task sets ucROTaskFaultTracker[ 0 ] to FAULT_TRACKER_FAULT_EXPECTED
 * before attempting an illegal write. The illegal access triggers a Memory
 * Management fault; the fault handler checks the tracker and recovers gracefully
 * from an expected fault by advancing the stacked PC to the next instruction.
 *
 * @note Declared as 32 bytes because the smallest supported ARMv7-M MPU region
 * size is 32 bytes.
 */
static volatile uint8_t ucROTaskFaultTracker[ SHARED_MEMORY_SIZE ] __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) ) = { 0 };
/*-----------------------------------------------------------*/

/**
 * @brief Implements the task which has Read Only access to ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvROAccessTask( void * pvParameters );

/**
 * @brief Implements the task which has Read Write access to ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvRWAccessTask( void * pvParameters );

/**
 * @brief Print one safety-property result line on UART0.
 *
 * The read-only task runs unprivileged, so it cannot call printf(): C library
 * globals lie outside its MPU regions. UART0 is already inside the
 * general-peripherals region, which is readable and writable by unprivileged
 * code. This does not change any MPU permission.
 */
static void prvReportPropertyResult( const char * pcMessage );

/**
 * @brief Report pass or fail message for a safety property check.
 */
static void prvReportSafetyCheck( BaseType_t xCheckPassed,
                                  const char * pcPassMessage,
                                  const char * pcFailMessage );

/**
 * @brief Perform a permitted read from ucSharedMemory.
 */
static void prvExercisePermittedSharedMemoryRead( void );

/**
 * @brief Arm the fault tracker, attempt a write to ucSharedMemory, and verify
 * whether the MPU rejected the write via vHandleMemoryFault().
 *
 * @return pdTRUE if the expected MPU fault fired and cleared the tracker;
 *         pdFALSE if the write succeeded without faulting.
 */
static BaseType_t prvAttemptWriteExpectingMPUFault( void );

/**
 * @brief Verify SP1: unprivileged read succeeds and write to read-only shared
 * memory is rejected by the MPU.
 */
static void prvVerifyReadOnlyMemoryIsolation( void );

/**
 * @brief Verify privilege containment (SP2 when kernel-only system calls are
 * enforced, or user-mode demotion fault check otherwise).
 */
static void prvVerifyPrivilegeContainment( void );

/**
 * @brief Determine the byte length (2 or 4) of a Thumb instruction from its
 * first halfword.
 */
static uint32_t prvGetThumbInstructionSize( uint16_t usFirstHalfword );

/**
 * @brief Advance the stacked return PC past the instruction that triggered an
 * expected Memory Management fault.
 */
static void prvSkipFaultingInstruction( uint32_t * pulFaultStackAddress );

/*-----------------------------------------------------------*/

static void prvReportPropertyResult( const char * pcMessage )
{
    volatile uint32_t * const pulUartData = CMSDK_UART0_DATA_REG;

    while( *pcMessage != '\0' )
    {
        *pulUartData = ( uint32_t ) ( ( uint8_t ) *pcMessage );
        pcMessage++;
    }

    *pulUartData = ( uint32_t ) '\n';
}
/*-----------------------------------------------------------*/

static void prvReportSafetyCheck( BaseType_t xCheckPassed,
                                  const char * pcPassMessage,
                                  const char * pcFailMessage )
{
    if( xCheckPassed != pdFALSE )
    {
        prvReportPropertyResult( pcPassMessage );
    }
    else
    {
        prvReportPropertyResult( pcFailMessage );
    }
}
/*-----------------------------------------------------------*/

static void prvExercisePermittedSharedMemoryRead( void )
{
    uint8_t ucVal;

    /* ROAccess has read-only permission on ucSharedMemory, so reading is allowed. */
    ucVal = ucSharedMemory[ SHARED_MEMORY_TEST_INDEX ];
    ( void ) ucVal;
}
/*-----------------------------------------------------------*/

static BaseType_t prvAttemptWriteExpectingMPUFault( void )
{
    /* Mark the upcoming write fault as expected so vHandleMemoryFault() skips
     * the faulting instruction and clears the tracker. */
    ucROTaskFaultTracker[ FAULT_TRACKER_SLOT_INDEX ] = FAULT_TRACKER_FAULT_EXPECTED;

    /* Illegal write when running unprivileged with RO access to ucSharedMemory. */
    ucSharedMemory[ SHARED_MEMORY_TEST_INDEX ] = SHARED_MEMORY_WRITE_VALUE;

    return ( ucROTaskFaultTracker[ FAULT_TRACKER_SLOT_INDEX ] == FAULT_TRACKER_CLEARED ) ? pdTRUE : pdFALSE;
}
/*-----------------------------------------------------------*/

static void prvVerifyReadOnlyMemoryIsolation( void )
{
    BaseType_t xWriteRejected;

    prvExercisePermittedSharedMemoryRead();

    /* SP1: the fault handler clears the tracker only after the expected MPU
     * fault. A cleared tracker confirms the write to RO memory was rejected. */
    xWriteRejected = prvAttemptWriteExpectingMPUFault();
    prvReportSafetyCheck( xWriteRejected, SP1_PASS_MESSAGE, SP1_FAIL_MESSAGE );
}
/*-----------------------------------------------------------*/

static void prvVerifyPrivilegeContainment( void )
{
    #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 )
    {
        BaseType_t xWriteStillRejected;

        /* Attempt an SVC privilege escalation from application code. With
         * kernel-only system calls enforced, the request must be rejected and
         * the task must remain unprivileged. */
        portRAISE_PRIVILEGE();

        /* SP2: a second MPU fault on writing ucSharedMemory confirms the task
         * remained unprivileged after the unauthorized escalation attempt. */
        xWriteStillRejected = prvAttemptWriteExpectingMPUFault();
        prvReportSafetyCheck( xWriteStillRejected, SP2_PASS_MESSAGE, SP2_FAIL_MESSAGE );
    }
    #else /* if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
    {
        BaseType_t xUnprivilegedWriteFaulted;

        /* When kernel-only system call enforcement is disabled, raising
         * privilege succeeds and a privileged write does not fault. */
        portRAISE_PRIVILEGE();
        ucSharedMemory[ SHARED_MEMORY_TEST_INDEX ] = SHARED_MEMORY_WRITE_VALUE;

        /* Drop back to unprivileged mode and confirm writes fault again. */
        portSWITCH_TO_USER_MODE();
        xUnprivilegedWriteFaulted = prvAttemptWriteExpectingMPUFault();
        configASSERT( xUnprivilegedWriteFaulted == pdTRUE );
    }
    #endif /* #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
}
/*-----------------------------------------------------------*/

static void prvROAccessTask( void * pvParameters )
{
    ( void ) pvParameters;

    portRAISE_PRIVILEGE();

    for( ; ; )
    {
        prvVerifyReadOnlyMemoryIsolation();
        prvVerifyPrivilegeContainment();

        vTaskDelay( DEMO_LOOP_DELAY_TICKS );
    }
}
/*-----------------------------------------------------------*/

static void prvRWAccessTask( void * pvParameters )
{
    ( void ) pvParameters;

    for( ; ; )
    {
        /* RWAccess has read-write permission on ucSharedMemory. */
        ucSharedMemory[ SHARED_MEMORY_TEST_INDEX ] = SHARED_MEMORY_WRITE_VALUE;

        vTaskDelay( DEMO_LOOP_DELAY_TICKS );
    }
}
/*-----------------------------------------------------------*/

void vStartMPUDemo( void )
{
    /* Task stacks are MPU-protected and must satisfy ARMv7-M MPU size and
     * alignment constraints. */
    static StackType_t xROAccessTaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( DEMO_TASK_STACK_ALIGNMENT_BYTES ) ) );
    static StackType_t xRWAccessTaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( DEMO_TASK_STACK_ALIGNMENT_BYTES ) ) );

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
            { ucSharedMemory,                  SHARED_MEMORY_SIZE, RO_TASK_SHARED_MEMORY_PERMISSIONS  },
            { ( void * ) ucROTaskFaultTracker, SHARED_MEMORY_SIZE, UNPRIV_READ_WRITE_DATA_PERMISSIONS },
            { 0,                               0,                  0                                  },
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
            { ucSharedMemory, SHARED_MEMORY_SIZE, UNPRIV_READ_WRITE_DATA_PERMISSIONS },
            { 0,              0,                  0                                  },
            { 0,              0,                  0                                  },
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
    uint16_t usOpcodePrefix;
    uint32_t ulInstructionBytes;

    /* Per the ARMv7-M Architecture Reference Manual, if bits[15:11] of the
     * halfword being decoded equal 0b11101, 0b11110, or 0b11111, it is the
     * first halfword of a 32-bit Thumb instruction; otherwise it is a 16-bit
     * Thumb instruction. */
    usOpcodePrefix = ( uint16_t ) ( ( usFirstHalfword & THUMB_32BIT_PREFIX_MASK ) >> THUMB_32BIT_PREFIX_SHIFT );

    if( ( usOpcodePrefix == THUMB_32BIT_PREFIX_11111 ) ||
        ( usOpcodePrefix == THUMB_32BIT_PREFIX_11110 ) ||
        ( usOpcodePrefix == THUMB_32BIT_PREFIX_11101 ) )
    {
        ulInstructionBytes = THUMB_32BIT_INSTRUCTION_BYTES;
    }
    else
    {
        ulInstructionBytes = THUMB_16BIT_INSTRUCTION_BYTES;
    }

    return ulInstructionBytes;
}
/*-----------------------------------------------------------*/

static void prvSkipFaultingInstruction( uint32_t * pulFaultStackAddress )
{
    uint32_t ulPC;
    uint16_t usOffendingInstruction;

    ulPC = pulFaultStackAddress[ FAULT_STACK_PC_OFFSET ];
    usOffendingInstruction = *( const uint16_t * ) ulPC;
    ulPC += prvGetThumbInstructionSize( usOffendingInstruction );
    pulFaultStackAddress[ FAULT_STACK_PC_OFFSET ] = ulPC;
}
/*-----------------------------------------------------------*/

portDONT_DISCARD void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    /* Recover only if the fault was intentionally triggered by ROAccess. */
    if( ucROTaskFaultTracker[ FAULT_TRACKER_SLOT_INDEX ] == FAULT_TRACKER_FAULT_EXPECTED )
    {
        prvSkipFaultingInstruction( pulFaultStackAddress );
        ucROTaskFaultTracker[ FAULT_TRACKER_SLOT_INDEX ] = FAULT_TRACKER_CLEARED;
    }
    else
    {
        /* Unexpected fault: halt here forever. */
        for( ; ; )
        {
        }
    }
}
/*-----------------------------------------------------------*/
