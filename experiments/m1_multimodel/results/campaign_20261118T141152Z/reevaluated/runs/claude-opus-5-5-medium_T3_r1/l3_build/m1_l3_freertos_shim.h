/*
 * Host-side FreeRTOS/demo shim for compiling agent-modified QueueSet.c under M1 L3.
 * Not a FreeRTOS port. Does not provide production behaviour for queue/task APIs.
 */
#ifndef M1_L3_FREERTOS_SHIM_H
#define M1_L3_FREERTOS_SHIM_H

#include <stdint.h>
#include <stddef.h>
#include <setjmp.h>

#ifndef configUSE_QUEUE_SETS
    #define configUSE_QUEUE_SETS    1
#endif

typedef int32_t BaseType_t;
typedef uint32_t UBaseType_t;
typedef uint32_t TickType_t;
typedef void * TaskHandle_t;
typedef void * QueueHandle_t;
typedef void * QueueSetHandle_t;
typedef void * QueueSetMemberHandle_t;

#ifndef pdPASS
    #define pdPASS     ( ( BaseType_t ) 1 )
#endif
#ifndef pdTRUE
    #define pdTRUE     ( ( BaseType_t ) 1 )
#endif
#ifndef pdFALSE
    #define pdFALSE    ( ( BaseType_t ) 0 )
#endif
#ifndef pdFAIL
    #define pdFAIL     ( ( BaseType_t ) 0 )
#endif

#ifndef tskIDLE_PRIORITY
    #define tskIDLE_PRIORITY    ( ( UBaseType_t ) 0 )
#endif
#ifndef configMINIMAL_STACK_SIZE
    #define configMINIMAL_STACK_SIZE    ( ( uint16_t ) 128 )
#endif
#ifndef portMAX_DELAY
    #define portMAX_DELAY    ( ( TickType_t ) 0xffffffffUL )
#endif
#ifndef pdMS_TO_TICKS
    #define pdMS_TO_TICKS( x )    ( ( TickType_t ) ( x ) )
#endif

#ifndef taskYIELD
    #define taskYIELD()    do { } while( 0 )
#endif
#ifndef taskENTER_CRITICAL
    #define taskENTER_CRITICAL()    do { } while( 0 )
#endif
#ifndef taskEXIT_CRITICAL
    #define taskEXIT_CRITICAL()    do { } while( 0 )
#endif
#ifndef portYIELD_FROM_ISR
    #define portYIELD_FROM_ISR( x )    do { ( void ) ( x ); } while( 0 )
#endif
#ifndef mtCOVERAGE_TEST_MARKER
    #define mtCOVERAGE_TEST_MARKER()
#endif

extern jmp_buf xM1AssertJmp;
extern volatile int xM1AssertFired;
extern volatile int xM1AssertEnabled;

/* Same longjmp recording assert used by the host P2 oracle. */
#ifndef configASSERT
    #define configASSERT( x )                                      \
        do                                                         \
        {                                                          \
            if( ( ( x ) == 0 ) && ( xM1AssertEnabled != 0 ) )      \
            {                                                      \
                xM1AssertFired = 1;                                \
                longjmp( xM1AssertJmp, 1 );                        \
            }                                                      \
        } while( 0 )
#endif

/* Task / queue API stubs — enough to compile QueueSet.c as a host TU. */
BaseType_t xTaskCreate( void ( * pxTaskCode )( void * ),
                        const char * pcName,
                        uint16_t usStackDepth,
                        void * pvParameters,
                        UBaseType_t uxPriority,
                        TaskHandle_t * pxCreatedTask );
void vTaskSuspend( TaskHandle_t xTaskToSuspend );
void vTaskResume( TaskHandle_t xTaskToResume );
void vTaskDelay( TickType_t xTicksToDelay );
void vTaskPrioritySet( TaskHandle_t xTask, UBaseType_t uxNewPriority );
UBaseType_t uxTaskPriorityGet( TaskHandle_t xTask );

QueueHandle_t xQueueCreate( UBaseType_t uxQueueLength, UBaseType_t uxItemSize );
QueueSetHandle_t xQueueCreateSet( UBaseType_t uxEventQueueLength );
BaseType_t xQueueAddToSet( QueueSetMemberHandle_t xQueueOrSemaphore,
                           QueueSetHandle_t xQueueSet );
BaseType_t xQueueRemoveFromSet( QueueSetMemberHandle_t xQueueOrSemaphore,
                                QueueSetHandle_t xQueueSet );
void vQueueDelete( QueueHandle_t xQueue );
BaseType_t xQueueSendToBack( QueueHandle_t xQueue,
                             const void * pvItemToQueue,
                             TickType_t xTicksToWait );
BaseType_t xQueueSend( QueueHandle_t xQueue,
                       const void * pvItemToQueue,
                       TickType_t xTicksToWait );
BaseType_t xQueueSendFromISR( QueueHandle_t xQueue,
                              const void * pvItemToQueue,
                              BaseType_t * pxHigherPriorityTaskWoken );
BaseType_t xQueueOverwrite( QueueHandle_t xQueue, const void * pvItemToQueue );
BaseType_t xQueueOverwriteFromISR( QueueHandle_t xQueue,
                                   const void * pvItemToQueue,
                                   BaseType_t * pxHigherPriorityTaskWoken );
BaseType_t xQueueReceive( QueueHandle_t xQueue,
                          void * pvBuffer,
                          TickType_t xTicksToWait );
BaseType_t xQueueReceiveFromISR( QueueHandle_t xQueue,
                                 void * pvBuffer,
                                 BaseType_t * pxHigherPriorityTaskWoken );
BaseType_t xQueuePeek( QueueHandle_t xQueue,
                       void * pvBuffer,
                       TickType_t xTicksToWait );
UBaseType_t uxQueueMessagesWaiting( const QueueHandle_t xQueue );
QueueSetMemberHandle_t xQueueSelectFromSet( QueueSetHandle_t xQueueSet,
                                            TickType_t xTicksToWait );
QueueSetMemberHandle_t xQueueSelectFromSetFromISR( QueueSetHandle_t xQueueSet );

#endif /* M1_L3_FREERTOS_SHIM_H */
