/*
 * Independent L3 verification application entry.
 * Lives under experiments/verification/M2 — does not alter demo app_main.c.
 */
#include "FreeRTOS.h"
#include "task.h"

#include "app_main.h"
#include "l3_test.h"

#include <stdio.h>

void app_main( void )
{
    vStartL3Verification();
    vTaskStartScheduler();

    printf( "Returned from vTaskStartScheduler something bad had happened\n" );

    for( ; ; )
    {
    }
}
/*-----------------------------------------------------------*/

void vApplicationStackOverflowHook( TaskHandle_t pxTask,
                                    char * pcTaskName )
{
    ( void ) pxTask;
    ( void ) pcTaskName;
    printf( "Stack Overflow Hook called\n" );

    for( ; ; )
    {
    }
}
/*-----------------------------------------------------------*/

void vApplicationMallocFailedHook( void )
{
    printf( "Application Malloc Failed Hook called\n" );

    for( ; ; )
    {
    }
}
/*-----------------------------------------------------------*/

void vApplicationGetIdleTaskMemory( StaticTask_t ** ppxIdleTaskTCBBuffer,
                                    StackType_t ** ppxIdleTaskStackBuffer,
                                    uint32_t * pulIdleTaskStackSize )
{
    static StaticTask_t xIdleTaskTCB;
    static StackType_t uxIdleTaskStack[ configMINIMAL_STACK_SIZE ];

    *ppxIdleTaskTCBBuffer = &xIdleTaskTCB;
    *ppxIdleTaskStackBuffer = uxIdleTaskStack;
    *pulIdleTaskStackSize = configMINIMAL_STACK_SIZE;
}
/*-----------------------------------------------------------*/

void vApplicationGetTimerTaskMemory( StaticTask_t ** ppxTimerTaskTCBBuffer,
                                     StackType_t ** ppxTimerTaskStackBuffer,
                                     uint32_t * pulTimerTaskStackSize )
{
    static StaticTask_t xTimerTaskTCB;
    static StackType_t uxTimerTaskStack[ configTIMER_TASK_STACK_DEPTH ];

    *ppxTimerTaskTCBBuffer = &xTimerTaskTCB;
    *ppxTimerTaskStackBuffer = uxTimerTaskStack;
    *pulTimerTaskStackSize = configTIMER_TASK_STACK_DEPTH;
}
