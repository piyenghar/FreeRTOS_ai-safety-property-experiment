/*
 * Minimal stubs for host-side L3 of QueueSet range checking.
 * Not part of FreeRTOS / QueueSet.c.
 */
#ifndef M1_L3_FREERTOS_STUBS_H
#define M1_L3_FREERTOS_STUBS_H

#include <stdint.h>
#include <setjmp.h>

typedef int32_t BaseType_t;

#ifndef pdPASS
    #define pdPASS     ( ( BaseType_t ) 1 )
#endif
#ifndef pdFALSE
    #define pdFALSE    ( ( BaseType_t ) 0 )
#endif

/* Same constant as QueueSet.c */
#define queuesetALLOWABLE_RX_DEVIATION    3

extern jmp_buf xM1AssertJmp;
extern volatile int xM1AssertFired;
extern volatile int xM1AssertEnabled;

/* Recording assert: longjmps so out-of-range tests can complete. */
#define configASSERT( x )                                      \
    do                                                         \
    {                                                          \
        if( ( ( x ) == 0 ) && ( xM1AssertEnabled != 0 ) )      \
        {                                                      \
            xM1AssertFired = 1;                                \
            longjmp( xM1AssertJmp, 1 );                        \
        }                                                      \
    } while( 0 )

#endif /* M1_L3_FREERTOS_STUBS_H */
