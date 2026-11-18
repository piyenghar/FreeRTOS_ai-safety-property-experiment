/*
 * M1-E4 behavioural L2 harness linked against a full prepared QueueSet UUT
 * (m1_l3 shims), testing the actual modified QueueSet.c implementation.
 * Independent of M1 L3 oracle scoring.
 */
#include "m1_l3_freertos_shim.h"

#include <stdio.h>
#include <stdlib.h>

BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                     uint32_t ulExpectedReceived );

void vM1E4GetRangeDiagnostics( uint32_t * pulAccepted,
                               uint32_t * pulRejected );

jmp_buf xM1AssertJmp;
volatile int xM1AssertFired;
volatile int xM1AssertEnabled = 1;

static int g_fail;

static void fail( const char * msg )
{
    fprintf( stderr, "M1-E4 L2 FAIL: %s\n", msg );
    g_fail = 1;
}

static void query( uint32_t * a, uint32_t * r )
{
    *a = 0xFFFFFFFFu;
    *r = 0xFFFFFFFFu;
    vM1E4GetRangeDiagnostics( a, r );
}

static BaseType_t call_check( uint32_t rx, uint32_t exp, int * assert_out )
{
    BaseType_t got = pdFALSE;

    xM1AssertFired = 0;
    if( setjmp( xM1AssertJmp ) == 0 )
    {
        got = prvCheckReceivedValueWithinExpectedRange( rx, exp );
        *assert_out = xM1AssertFired;
    }
    else
    {
        *assert_out = 1;
        got = pdFALSE;
    }
    return got;
}

int main( void )
{
    uint32_t acc = 0;
    uint32_t rej = 0;
    int asrt = 0;
    BaseType_t got;

    g_fail = 0;

    query( &acc, &rej );
    if( acc != 0 || rej != 0 )
    {
        fail( "AT1_initial_counts_not_zero" );
    }

    got = call_check( 100u, 100u, &asrt );
    query( &acc, &rej );
    if( got != pdPASS || asrt != 0 || acc != 1u || rej != 0u )
    {
        fail( "AT2_in_range_exact" );
    }

    got = call_check( 103u, 100u, &asrt );
    query( &acc, &rej );
    if( got != pdPASS || asrt != 0 || acc != 2u || rej != 0u )
    {
        fail( "AT3_in_range_boundary" );
    }

    got = call_check( 104u, 100u, &asrt );
    query( &acc, &rej );
    if( got == pdPASS || asrt == 0 || acc != 2u || rej != 1u )
    {
        fail( "AT4_out_of_range" );
    }

    if( g_fail != 0 )
    {
        fprintf( stderr, "M1-E4 behavioural L2 (QueueSet UUT): FAIL\n" );
        return 1;
    }

    printf( "M1-E4 behavioural L2 (QueueSet UUT): PASS\n" );
    return 0;
}
