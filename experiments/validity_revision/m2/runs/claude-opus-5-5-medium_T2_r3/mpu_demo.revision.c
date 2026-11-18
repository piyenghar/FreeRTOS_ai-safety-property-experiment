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
#define SHARED_MEMORY_SIZE                 32

/**
 * @brief Alignment of the task stacks so that they satisfy MPU requirements.
 */
#define mpudemoSTACK_ALIGNMENT             ( 1024 * sizeof( StackType_t ) )

/**
 * @brief Period of each demo task loop.
 */
#define mpudemoTASK_PERIOD                 pdMS_TO_TICKS( 1000 )

/**
 * @brief CMSDK UART0 DATA register. Same address used by syscall.c.
 */
#define mpudemoUART0_DATA_REGISTER         ( ( volatile uint32_t * ) 0x40004000UL )

/**
 * @brief Values stored in ucROTaskFaultTracker[ 0 ].
 */
#define mpudemoFAULT_EXPECTED              ( ( uint8_t ) 1 )
#define mpudemoFAULT_HANDLED               ( ( uint8_t ) 0 )

/**
 * @brief Index of the stacked PC in the exception stack frame.
 */
#define mpudemoSTACKED_PC_INDEX            6

/**
 * @brief Safety-property result messages reported on UART0.
 */
#define mpudemoSP1_PASS_MESSAGE            "SP1 PASS: read-only memory isolation preserved"
#define mpudemoSP1_FAIL_MESSAGE            "SP1 FAIL: read-only memory isolation violated"
#define mpudemoSP2_PASS_MESSAGE            "SP2 PASS: unauthorized privilege escalation rejected"
#define mpudemoSP2_FAIL_MESSAGE            "SP2 FAIL: privilege containment violated"

/**
 * @brief Memory region shared between two tasks.
 */
static uint8_t ucSharedMemory[ SHARED_MEMORY_SIZE ] __attribute__( ( aligned( SHARED_MEMORY_SIZE ) ) );

/**
 * @brief Memory region used to track Memory Fault intentionally caused by the
 * RO Access task.
 *
 * RO Access task sets ucROTaskFaultTracker[ 0 ] to mpudemoFAULT_EXPECTED before
 * accessing illegal memory. Illegal memory access causes Memory Fault and the
 * fault handler checks ucROTaskFaultTracker[ 0 ] to see if this is an expected
 * fault. We recover gracefully from an expected fault by jumping to the next
 * instruction and setting ucROTaskFaultTracker[ 0 ] to mpudemoFAULT_HANDLED.
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
 * @brief Report the PASS or FAIL message of a safety property.
 *
 * @param xPassed[in] pdTRUE if the property held.
 * @param pcPassMessage[in] Message printed when the property held.
 * @param pcFailMessage[in] Message printed when the property was violated.
 */
static void prvReportProperty( BaseType_t xPassed,
                               const char * pcPassMessage,
                               const char * pcFailMessage );

/**
 * @brief Write to ucSharedMemory while announcing an expected Memory Fault.
 *
 * Marks the fault as expected, attempts the write and then checks whether the
 * Memory Fault handler acknowledged the fault.
 *
 * @return pdTRUE if the write was rejected by the MPU (the fault handler ran
 * and cleared the tracker), pdFALSE otherwise.
 */
static BaseType_t prvSharedMemoryWriteFaulted( void );

/**
 * @brief Read ucSharedMemory, which is permitted for the RO Access task.
 */
static void prvReadSharedMemory( void );

/**
 * @brief Check whether a Thumb halfword is the first half of a 32-bit
 * instruction.
 *
 * @param usHalfword[in] First halfword of the instruction.
 *
 * @return pdTRUE for a 32-bit instruction, pdFALSE for a 16-bit instruction.
 */
static BaseType_t prvIsThumb32BitInstruction( uint16_t usHalfword );

/*-----------------------------------------------------------*/

static void prvReportPropertyResult( const char * pcMessage )
{
    volatile uint32_t * const pulUartData = mpudemoUART0_DATA_REGISTER;

    while( *pcMessage != '\0' )
    {
        *pulUartData = ( uint32_t ) ( ( uint8_t ) *pcMessage );
        pcMessage++;
    }

    *pulUartData = ( uint32_t ) '\n';
}
/*-----------------------------------------------------------*/

static void prvReportProperty( BaseType_t xPassed,
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

static void prvReadSharedMemory( void )
{
    uint8_t ucVal;

    ucVal = ucSharedMemory[ 0 ];

    /* Silent compiler warnings about unused variables. */
    ( void ) ucVal;
}
/*-----------------------------------------------------------*/

static BaseType_t prvSharedMemoryWriteFaulted( void )
{
    /* Tell the Memory Fault Handler that the following write is expected to
     * fault, so that it recovers by jumping to the next instruction. */
    ucROTaskFaultTracker[ 0 ] = mpudemoFAULT_EXPECTED;

    /* Must result in Memory Fault while the task is unprivileged and has only
     * RO access to ucSharedMemory. */
    ucSharedMemory[ 0 ] = 0;

    /* The fault handler clears the tracker only after the expected MPU fault.
     * A cleared tracker means the write was rejected. */
    return ( ucROTaskFaultTracker[ 0 ] == mpudemoFAULT_HANDLED ) ? pdTRUE : pdFALSE;
}
/*-----------------------------------------------------------*/

static void prvROAccessTask( void * pvParameters )
{
    BaseType_t xWriteFaulted;

    /* Unused parameters. */
    ( void ) pvParameters;

    portRAISE_PRIVILEGE();

    for( ; ; )
    {
        /* This task has RO access to ucSharedMemory and therefore it can read
         * it but cannot modify it. */
        prvReadSharedMemory();

        /* SP1: writing to the RO region must be rejected by the MPU. */
        xWriteFaulted = prvSharedMemoryWriteFaulted();
        prvReportProperty( xWriteFaulted, mpudemoSP1_PASS_MESSAGE, mpudemoSP1_FAIL_MESSAGE );

        #if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 )
        {
            /* Generate an SVC to raise the privilege. Since privilege
             * escalation is only allowed from kernel code, this request must
             * get rejected and the task must remain unprivileged. */
            portRAISE_PRIVILEGE();

            /* SP2: a second MPU fault after the rejected privilege request
             * means the task is still unprivileged. */
            xWriteFaulted = prvSharedMemoryWriteFaulted();
            prvReportProperty( xWriteFaulted, mpudemoSP2_PASS_MESSAGE, mpudemoSP2_FAIL_MESSAGE );
        }
        #else /* if ( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */
        {
            /* Generate an SVC to raise the privilege. Since
             * configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY is not enabled, the
             * task will be able to escalate privilege. */
            portRAISE_PRIVILEGE();

            /* At this point, the task is running privileged. The following
             * access must not result in Memory Fault. If something goes
             * wrong and we do get a fault, the execution will stop in fault
             * handler as ucROTaskFaultTracker[ 0 ] is not set (i.e.
             * un-expected fault). */
            ucSharedMemory[ 0 ] = 0;

            /* Lower down the privilege. */
            portSWITCH_TO_USER_MODE();

            /* Now the task is running unprivileged and therefore an attempt to
             * write to ucSharedMemory must result in a Memory Fault. */
            xWriteFaulted = prvSharedMemoryWriteFaulted();
            configASSERT( xWriteFaulted == pdTRUE );
        }
        #endif /* #if( configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1 ) */

        vTaskDelay( mpudemoTASK_PERIOD );
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

        vTaskDelay( mpudemoTASK_PERIOD );
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
    __attribute__( ( aligned( mpudemoSTACK_ALIGNMENT ) ) );
    static StackType_t xRWAccessTaskStack[ configMINIMAL_STACK_SIZE ]
    __attribute__( ( aligned( mpudemoSTACK_ALIGNMENT ) ) );

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

static BaseType_t prvIsThumb32BitInstruction( uint16_t usHalfword )
{
    uint16_t usTopBits;

    /* From ARM docs:
     * If the value of bits[15:11] of the halfword being decoded is one of
     * the following, the halfword is the first halfword of a 32-bit
     * instruction:
     * - 0b11101.
     * - 0b11110.
     * - 0b11111.
     * Otherwise, the halfword is a 16-bit instruction.
     */
    usTopBits = ( uint16_t ) ( ( usHalfword & 0xF800 ) >> 11 );

    return ( ( usTopBits == 0x001F ) ||
             ( usTopBits == 0x001E ) ||
             ( usTopBits == 0x001D ) ) ? pdTRUE : pdFALSE;
}
/*-----------------------------------------------------------*/

portDONT_DISCARD void vHandleMemoryFault( uint32_t * pulFaultStackAddress )
{
    uint32_t ulPC;

    /* Is this an expected fault? */
    if( ucROTaskFaultTracker[ 0 ] == mpudemoFAULT_EXPECTED )
    {
        ulPC = pulFaultStackAddress[ mpudemoSTACKED_PC_INDEX ];

        /* Skip the offending instruction. */
        if( prvIsThumb32BitInstruction( *( uint16_t * ) ulPC ) == pdTRUE )
        {
            ulPC += 4;
        }
        else
        {
            ulPC += 2;
        }

        /* Save the new program counter on the stack. */
        pulFaultStackAddress[ mpudemoSTACKED_PC_INDEX ] = ulPC;

        /* Mark the fault as handled. */
        ucROTaskFaultTracker[ 0 ] = mpudemoFAULT_HANDLED;
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
