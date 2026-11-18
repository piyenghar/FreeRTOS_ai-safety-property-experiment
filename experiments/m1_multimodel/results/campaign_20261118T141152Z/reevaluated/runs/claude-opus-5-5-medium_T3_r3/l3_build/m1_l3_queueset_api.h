/*
 * Minimal QueueSet public API for host L3 (replaces Demo QueueSet.h include).
 */
#ifndef M1_L3_QUEUESET_API_H
#define M1_L3_QUEUESET_API_H

#include "m1_l3_freertos_shim.h"

void vStartQueueSetTasks( void );
BaseType_t xAreQueueSetTasksStillRunning( void );
void vQueueSetAccessQueueSetFromISR( void );

/* Exported by prepared agent QueueSet UUT (static removed for the checker). */
BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                     uint32_t ulExpectedReceived );

#endif /* M1_L3_QUEUESET_API_H */
