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
 * @brief Size of the shared MPU memory regions in bytes (minimum ARMv7-M size).
 */
#define SHARED_MEMORY_SIZE                32

/**
 * @brief Stack alignment in bytes required for MPU-protected task stacks.
 */
#define DEMO_TASK_STACK_ALIGNMENT         ( 1024U * sizeof( StackType_t ) )

/**
 * @brief Delay between demo verification iterations.
 */
#define DEMO_TASK_DELAY_TICKS             pdMS_TO_TICKS( 1000UL )

/**
 * @brief CMSDK UART0 data register address (matches syscall.c).
 */
#define CMSDK_UART0_DATA_REG_ADDR         ( 0x40004000UL )

/**
 * @brief States recorded in ucROTaskFaultTracker[ 0 ] across expected faults.
 */
#define FAULT_TRACKER_CLEARED             ( 0U )
#define FAULT_TRACKER_EXPECTED            ( 1U )

/**
 * @brief Offset of the stacked Program Counter in the ARMv7-M exception frame.
 */
#define EXCEPTION_STACK_PC_INDEX          ( 6U )

/**
 * @brief ARMv7-M Thumb instruction prefix constants used to distinguish 32-bit
 * Thumb-2 instructions (bits[15:11] in {0b11101, 0b11110, 0b11111}) from 16-bit
 * Thumb instructions.
 */
#define THUMB_OPCODE_PREFIX_MASK          ( 0xF800U )
#define THUMB_OPCODE_PREFIX_SHIFT         ( 11U )
#define THUMB_32BIT_PREFIX_11101          ( 0x001DU )
#define THUMB_32BIT_PREFIX_11110          ( 0x001EU )
#define THUMB_32BIT_PREFIX_11111          ( 0x001FU )
#define THUMB_16BIT_INSTRUCTION_LENGTH    ( 2UL )
#define THUMB_32BIT_INSTRUCTION_LENGTH    ( 4UL )

/**
 * @brief UART diagnostic strings for SP1 and SP2 safety properties.
 */
#define SP1_PASS_MESSAGE                  "SP1 PASS: read-only memory isolation preserved"
#define SP1_FAIL_MESSAGE                  "SP1 FAIL: read-only memory isolation violated"
#define SP2_PASS_MESSAGE                  "SP2 PASS: unauthorized privilege escalation rejected"
#define SP2_FAIL_MESSAGE                  "SP2 FAIL: privilege containment violated"
/*-----------------------------------------------------------*/

/**
 * @brief Memory region shared between the RO and RW unprivileged tasks.
 */
static uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

/**
 * @brief Memory region used to track an intentional Memory Fault triggered by
 * the RO Access task.
 *
 * The RO Access task sets ucROTaskFaultTracker[ 0 ] to FAULT_TRACKER_EXPECTED
 * before attempting an illegal write. The fault handler checks this flag and,
 * when armed, recovers gracefully by advancing the stacked PC past the faulting
 * instruction and clearing the flag back to FAULT_TRACKER_CLEARED.
 *
 * @note Declared as 32 bytes because 32 bytes is the smallest supported ARMv7-M
 * MPU region size.
 */
static volatile uint8_t ucROTaskFaultTracker[ SHARED_MEMORY_SIZE ]
    __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) ) = { 0 };
/*-----------------------------------------------------------*/

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
 * @brief Report either the PASS or FAIL diagnostic message for a property check.
 */
static void prvReportPropertyCheck( BaseType_t xPropertyHeld,
                                    const char * pcPassMessage,
                                    const char * pcFailMessage );

/**
 * @brief Arm the fault tracker, attempt a write to ucSharedMemory, and report
 * whether the MPU rejected the write with an expected Memory Fault.
 *
 * @return pdTRUE if the write triggered a Memory Fault and the fault handler
 * cleared ucROTaskFaultTracker[ 0 ]; pdFALSE otherwise.
 */
static BaseType_t prvAttemptProtectedSharedMemoryWrite( void );

/**
 * @brief Verify SP1: unprivileged read succeeds while unprivileged write to the
 * read-only shared memory region is rejected by the MPU.
 */
static void prvVerifyReadOnlyMemoryIsolation( void );

/**
 * @brief Verify SP2: privilege escalation from unprivileged application code is
 * rejected (when kernel-only system calls are enforced) or properly lowered.
 */
static void prvVerifyPrivilegeContainment( void );

/**
 * @brief Decode the byte length (2 or 4) of the Thumb instruction starting with
 * usFirstHalfword.
 */
static uint32_t prvGetThumbInstructionLength( uint16_t usFirstHalfword );

/**
 * @brief Advance the stacked PC in an exception frame past the faulting Thumb
 * instruction.
 */
static void prvAdvanceProgramCounterPastFault( uint32_t * pulFaultStackAddress );

/**
 * @brief Implements the unprivileged task granted Read-Only access to
 * ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvROAccessTask( void * pvParameters );

/**
 * @brief Implements the unprivileged task granted Read-Write access to
 * ucSharedMemory.
 *
 * @param pvParameters[in] Parameters as passed during task creation.
 */
static void prvRWAccessTask( void * pvParameters );
/*-----------------------------------------------------------*/

static void prvReportPropertyResult( const char * pcMessage )
{
    volatile uint32_t * const pulUartData =
        ( volatile uint32_t * ) CMSDK_UART0_DATA_REG_ADDR;

    while( *pcMessage != '\0' )
    {
        *pulUartData = ( uint32_t ) ( ( uint8_t ) *pcMessage );
        pcMessage++;
    }

    *pulUartData = ( uint32_t ) '\n';
}
/*-----------------------------------------------------------*/

static void prvReportPropertyCheck( BaseType_t xPropertyHeld,
                                    const char * pcPassMessage,
                                    const char * pcFailMessage )
{
    if( xPropertyHeld != pdFALSE )
    {
        prvReportPropertyResult( pcPassMessage );
    }
    else
    {
        prvReportPropertyResult( pcFailMessage );
    }
}
/*-----------------------------------------------------------*/

static BaseType_t prvAttemptProtectedSharedMemoryWrite( void )
{
    /* Mark the upcoming write fault as expected so vHandleMemoryFault()
     * recovers gracefully by skipping past the faulting store instruction. */
    ucROTaskFaultTracker[ 0 ] = FAULT_TRACKER_EXPECTED;
    portMEMORY_BARRIER();

    /* Illegal write when unprivileged: must trigger a synchronous MemFault. */
    *( ( volatile uint8_t * ) ucSharedMemory ) = 0U;
    portMEMORY_BARRIER();

    /* The fault handler clears the tracker only when the expected MPU fault
     * occurred. */
    return ( ucROTaskFaultTracker[ 0 ] == FAULT_TRACKER_CLEARED ) ? pdTRUE : pdFALSE;
}
/*-----------------------------------------------------------*/

static void prvVerifyReadOnlyMemoryIsolation( void )
{
    uint8_t ucVal;
    BaseType_t xWriteRejected;

    /* Reading ucSharedMemory is permitted under unprivileged RO permissions. */
    ucVal = *( ( const volatile uint8_t * ) ucSharedMemory );
    ( void ) ucVal;

    /* SP1: writing to ucSharedMemory from the RO task must fault and leave
     * read-only isolation intact. */
    xWriteRejected = prvAttemptProtectedSharedMemoryWrite();
    prvReportPropertyCheck( xWriteRejected, SP1_PASS_MESSAGE, SP1_FAIL_MESSAGE );
}
/*-----------------------------------------------------------*/

static void prvVerifyPrivilegeContainment( void )
{
    #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 )
    {
        BaseType_t xWriteStillRejected;

        /* Request privilege escalation directly from application code via SVC.
         * With kernel-only system call enforcement enabled, this request must be
         * rejected and the task must remain unprivileged. */
        portRAISE_PRIVILEGE();

        /* SP2: a subsequent write to the RO region must still fault, proving the
         * task remained unprivileged. */
        xWriteStillRejected = prvAttemptProtectedSharedMemoryWrite();
        prvReportPropertyCheck( xWriteStillRejected, SP2_PASS_MESSAGE, SP2_FAIL_MESSAGE );
    }
    #else /* if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
    {
        BaseType_t xUnprivilegedWriteRejected;

        /* Without kernel-only system call enforcement, SVC raises privilege and
         * allows a privileged write without arming the fault tracker. */
        portRAISE_PRIVILEGE();
        *( ( volatile uint8_t * ) ucSharedMemory ) = 0U;

        /* Drop back to unprivileged user mode and confirm writes fault again. */
        portSWITCH_TO_USER_MODE();
        xUnprivilegedWriteRejected = prvAttemptProtectedSharedMemoryWrite();
        configASSERT( xUnprivilegedWriteRejected == pdTRUE );
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

        vTaskDelay( DEMO_TASK_DELAY_TICKS );
    }
}
/*-----------------------------------------------------------*/

static void prvRWAccessTask( void * pvParameters )
{
    ( void ) pvParameters;

    for( ; ; )
    {
        /* This task has RW access to ucSharedMemory and can write without faulting. */
        ucSharedMemory[ 0 ] = 0U;

        vTaskDelay( DEMO_TASK_DELAY_TICKS );
    }
}
/*-----------------------------------------------------------*/

void vStartMPUDemo( void )
{
    /* Task stacks are protected by the MPU and must satisfy ARMv7-M alignment
     * rules stated at the top of this file. */
    static StackType_t xROAccessTaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( DEMO_TASK_STACK_ALIGNMENT ) ) );
    static StackType_t xRWAccessTaskStack[ configMINIMAL_STACK_SIZE ]
        __attribute__( ( aligned( DEMO_TASK_STACK_ALIGNMENT ) ) );

    static const TaskParameters_t xROAccessTaskParameters =
    {
        .pvTaskCode     = prvROAccessTask,
        .pcName         = "ROAccess",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
        .uxPriority     = tskIDLE_PRIORITY,
        .puxStackBuffer = xROAccessTaskStack,
        .xRegions       =
        {
            {
                ucSharedMemory,
                SHARED_MEMORY_SIZE,
                portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY |
                portMPU_REGION_EXECUTE_NEVER
            },
            {
                ( void * ) ucROTaskFaultTracker,
                SHARED_MEMORY_SIZE,
                portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER
            },
            { 0, 0, 0 }
        }
    };

    static const TaskParameters_t xRWAccessTaskParameters =
    {
        .pvTaskCode     = prvRWAccessTask,
        .pcName         = "RWAccess",
        .usStackDepth   = configMINIMAL_STACK_SIZE,
        .pvParameters   = NULL,
        .uxPriority     = tskIDLE_PRIORITY,
        .puxStackBuffer = xRWAccessTaskStack,
        .xRegions       =
        {
            {
                ucSharedMemory,
                SHARED_MEMORY_SIZE,
                portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER
            },
            { 0, 0, 0 },
            { 0, 0, 0 }
        }
    };

    /* Create an unprivileged task with RO access to ucSharedMemory. */
    ( void ) xTaskCreateRestricted( &( xROAccessTaskParameters ), NULL );

    /* Create an unprivileged task with RW access to ucSharedMemory. */
    ( void ) xTaskCreateRestricted( &( xRWAccessTaskParameters ), NULL );
}
/*-----------------------------------------------------------*/

static uint32_t prvGetThumbInstructionLength( uint16_t usFirstHalfword )
{
    uint16_t usOpcodePrefix;
    uint32_t ulInstructionLength;

    /* Per ARMv7-M architecture decoding rules:
     * If bits[15:11] of the halfword being decoded are 0b11101, 0b11110, or
     * 0b11111, the halfword is the first halfword of a 32-bit instruction;
     * otherwise, it is a 16-bit instruction. */
    usOpcodePrefix = ( uint16_t ) ( ( usFirstHalfword & THUMB_OPCODE_PREFIX_MASK ) >>
                                    THUMB_OPCODE_PREFIX_SHIFT );

    if( ( usOpcodePrefix == THUMB_32BIT_PREFIX_11101 ) ||
        ( usOpcodePrefix == THUMB_32BIT_PREFIX_11110 ) ||
        ( usOpcodePrefix == THUMB_32BIT_PREFIX_11111 ) )
    {
        ulInstructionLength = THUMB_32BIT_INSTRUCTION_LENGTH;
    }
    else
    {
        ulInstructionLength = THUMB_16BIT_INSTRUCTION_LENGTH;
    }

    return ulInstructionLength;
}
/*-----------------------------------------------------------*/

static void prvAdvanceProgramCounterPastFault( uint32_t * pulFaultStackAddress )
{
    uint32_t ulFaultingPC;
    uint16_t usOffendingInstruction;

    ulFaultingPC = pulFaultStackAddress[ EXCEPTION_STACK_PC_INDEX ];
    usOffendingInstruction = *( ( const uint16_t * ) ulFaultingPC );

    pulFaultStackAddress[ EXCEPTION_STACK_PC_INDEX ] =
        ulFaultingPC + prvGetThumbInstructionLength( usOffendingInstruction );
}
/*-----------------------------------------------------------*/

portDONT_DISCARD void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    if( ucROTaskFaultTracker[ 0 ] == FAULT_TRACKER_EXPECTED )
    {
        prvAdvanceProgramCounterPastFault( pulFaultStackAddress );
        ucROTaskFaultTracker[ 0 ] = FAULT_TRACKER_CLEARED;
    }
    else
    {
        /* Unexpected memory fault: halt in an infinite loop. */
        for( ; ; )
        {
        }
    }
}
/*-----------------------------------------------------------*/
