/*
 * Stub implementations for compiling agent QueueSet.c on the host.
 */
#include "m1_l3_freertos_shim.h"

BaseType_t xTaskCreate( void ( * pxTaskCode )( void * ),
                        const char * pcName,
                        uint16_t usStackDepth,
                        void * pvParameters,
                        UBaseType_t uxPriority,
                        TaskHandle_t * pxCreatedTask )
{
    ( void ) pxTaskCode;
    ( void ) pcName;
    ( void ) usStackDepth;
    ( void ) pvParameters;
    ( void ) uxPriority;
    if( pxCreatedTask != NULL )
    {
        *pxCreatedTask = ( TaskHandle_t ) 1;
    }
    return pdPASS;
}

void vTaskSuspend( TaskHandle_t xTaskToSuspend )
{
    ( void ) xTaskToSuspend;
}
void vTaskResume( TaskHandle_t xTaskToResume )
{
    ( void ) xTaskToResume;
}
void vTaskDelay( TickType_t xTicksToDelay )
{
    ( void ) xTicksToDelay;
}
void vTaskPrioritySet( TaskHandle_t xTask, UBaseType_t uxNewPriority )
{
    ( void ) xTask;
    ( void ) uxNewPriority;
}
UBaseType_t uxTaskPriorityGet( TaskHandle_t xTask )
{
    ( void ) xTask;
    return tskIDLE_PRIORITY;
}

QueueHandle_t xQueueCreate( UBaseType_t uxQueueLength, UBaseType_t uxItemSize )
{
    ( void ) uxQueueLength;
    ( void ) uxItemSize;
    return ( QueueHandle_t ) 2;
}
QueueSetHandle_t xQueueCreateSet( UBaseType_t uxEventQueueLength )
{
    ( void ) uxEventQueueLength;
    return ( QueueSetHandle_t ) 3;
}
BaseType_t xQueueAddToSet( QueueSetMemberHandle_t xQueueOrSemaphore,
                           QueueSetHandle_t xQueueSet )
{
    ( void ) xQueueOrSemaphore;
    ( void ) xQueueSet;
    return pdPASS;
}
BaseType_t xQueueRemoveFromSet( QueueSetMemberHandle_t xQueueOrSemaphore,
                                QueueSetHandle_t xQueueSet )
{
    ( void ) xQueueOrSemaphore;
    ( void ) xQueueSet;
    return pdPASS;
}
void vQueueDelete( QueueHandle_t xQueue )
{
    ( void ) xQueue;
}
BaseType_t xQueueSendToBack( QueueHandle_t xQueue,
                             const void * pvItemToQueue,
                             TickType_t xTicksToWait )
{
    ( void ) xQueue;
    ( void ) pvItemToQueue;
    ( void ) xTicksToWait;
    return pdPASS;
}
BaseType_t xQueueSend( QueueHandle_t xQueue,
                       const void * pvItemToQueue,
                       TickType_t xTicksToWait )
{
    return xQueueSendToBack( xQueue, pvItemToQueue, xTicksToWait );
}
BaseType_t xQueueSendFromISR( QueueHandle_t xQueue,
                              const void * pvItemToQueue,
                              BaseType_t * pxHigherPriorityTaskWoken )
{
    ( void ) pxHigherPriorityTaskWoken;
    return xQueueSendToBack( xQueue, pvItemToQueue, 0 );
}
BaseType_t xQueueOverwrite( QueueHandle_t xQueue, const void * pvItemToQueue )
{
    ( void ) xQueue;
    ( void ) pvItemToQueue;
    return pdPASS;
}
BaseType_t xQueueOverwriteFromISR( QueueHandle_t xQueue,
                                   const void * pvItemToQueue,
                                   BaseType_t * pxHigherPriorityTaskWoken )
{
    ( void ) pxHigherPriorityTaskWoken;
    return xQueueOverwrite( xQueue, pvItemToQueue );
}
BaseType_t xQueueReceive( QueueHandle_t xQueue,
                          void * pvBuffer,
                          TickType_t xTicksToWait )
{
    ( void ) xQueue;
    ( void ) pvBuffer;
    ( void ) xTicksToWait;
    return pdFALSE;
}
BaseType_t xQueueReceiveFromISR( QueueHandle_t xQueue,
                                 void * pvBuffer,
                                 BaseType_t * pxHigherPriorityTaskWoken )
{
    ( void ) pxHigherPriorityTaskWoken;
    return xQueueReceive( xQueue, pvBuffer, 0 );
}
BaseType_t xQueuePeek( QueueHandle_t xQueue,
                       void * pvBuffer,
                       TickType_t xTicksToWait )
{
    return xQueueReceive( xQueue, pvBuffer, xTicksToWait );
}
UBaseType_t uxQueueMessagesWaiting( const QueueHandle_t xQueue )
{
    ( void ) xQueue;
    return 0;
}
QueueSetMemberHandle_t xQueueSelectFromSet( QueueSetHandle_t xQueueSet,
                                            TickType_t xTicksToWait )
{
    ( void ) xQueueSet;
    ( void ) xTicksToWait;
    return NULL;
}
QueueSetMemberHandle_t xQueueSelectFromSetFromISR( QueueSetHandle_t xQueueSet )
{
    ( void ) xQueueSet;
    return NULL;
}
