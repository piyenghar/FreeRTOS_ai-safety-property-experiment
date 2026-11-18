/*
 * Independent L3 tests for QueueSet range checking.
 * Lives under experiments/verification/M1/l3/ only.
 */
#include "freertos_stubs.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

BaseType_t prvCheckReceivedValueWithinExpectedRange( uint32_t ulReceived,
                                                     uint32_t ulExpectedReceived );

jmp_buf xM1AssertJmp;
volatile int xM1AssertFired;
volatile int xM1AssertEnabled = 1;

typedef struct
{
    const char * pcName;
    uint32_t ulReceived;
    uint32_t ulExpected;
    BaseType_t xExpectReturn;
    int xExpectAssert;
    const char * pcProperty; /* P1, P2, or CTRL */
} M1TestCase_t;

typedef struct
{
    int xTotal;
    int xPass;
    int xFail;
} M1Stats_t;

static int prvRunCase( const M1TestCase_t * pxCase,
                       FILE * pxLog )
{
    BaseType_t xGot = pdFALSE;
    int xAssert = 0;
    int xPass;

    xM1AssertFired = 0;

    if( setjmp( xM1AssertJmp ) == 0 )
    {
        xGot = prvCheckReceivedValueWithinExpectedRange( pxCase->ulReceived,
                                                         pxCase->ulExpected );
        xAssert = xM1AssertFired;
    }
    else
    {
        /* Out-of-range: configASSERT longjmps here — expected for P2, not a harness bug. */
        xAssert = 1;
        xGot = pdFALSE;
    }

    if( pxCase->xExpectAssert != 0 )
    {
        xPass = ( xAssert != 0 );
    }
    else
    {
        xPass = ( xGot == pxCase->xExpectReturn ) && ( xAssert == 0 );
    }

    fprintf( pxLog,
             "%s name=%s rx=%u exp=%u got_return=%ld assert=%d expect_return=%ld expect_assert=%d => %s\n",
             pxCase->pcProperty,
             pxCase->pcName,
             ( unsigned ) pxCase->ulReceived,
             ( unsigned ) pxCase->ulExpected,
             ( long ) xGot,
             xAssert,
             ( long ) pxCase->xExpectReturn,
             pxCase->xExpectAssert,
             xPass ? "PASS" : "FAIL" );

    return xPass;
}

static void prvAdd( M1Stats_t * pxStats,
                    int xPass )
{
    pxStats->xTotal++;
    if( xPass )
    {
        pxStats->xPass++;
    }
    else
    {
        pxStats->xFail++;
    }
}

int main( void )
{
    const uint32_t ulMid = 1000U;
    const M1TestCase_t xCases[] =
    {
        { "eq",           ulMid,           ulMid,           pdPASS,  0, "P1" },
        { "plus1",        ulMid + 1U,      ulMid,           pdPASS,  0, "P1" },
        { "minus1",       ulMid - 1U,      ulMid,           pdPASS,  0, "P1" },
        { "plus2",        ulMid + 2U,      ulMid,           pdPASS,  0, "P1" },
        { "minus2",       ulMid - 2U,      ulMid,           pdPASS,  0, "P1" },
        { "plus3_bound",  ulMid + 3U,      ulMid,           pdPASS,  0, "P1" },
        { "minus3_bound", ulMid - 3U,      ulMid,           pdPASS,  0, "P1" },

        { "plus4",        ulMid + 4U,      ulMid,           pdFALSE, 1, "P2" },
        { "minus4",       ulMid - 4U,      ulMid,           pdFALSE, 1, "P2" },
        { "plus5",        ulMid + 5U,      ulMid,           pdFALSE, 1, "P2" },
        { "minus10",      ulMid - 10U,     ulMid,           pdFALSE, 1, "P2" },

        { "zero_eq",      0U,              0U,              pdPASS,  0, "P1" },
        { "zero_plus3",   3U,              0U,              pdPASS,  0, "P1" },
        { "zero_plus4",   4U,              0U,              pdFALSE, 1, "P2" },
        { "max_eq",       UINT32_MAX,      UINT32_MAX,      pdPASS,  0, "P1" },
        { "max_minus3",   UINT32_MAX - 3U, UINT32_MAX,      pdPASS,  0, "P1" },
        { "max_minus4",   UINT32_MAX - 4U, UINT32_MAX,      pdFALSE, 1, "P2" },
        { "near_wrap_ok", UINT32_MAX,      UINT32_MAX - 2U, pdPASS,  0, "P1" },
        { "u_large_dev",  UINT32_MAX,      0U,              pdFALSE, 1, "P2" },
        { "isr_split_eq", 0xFFFFU,         0xFFFFU,         pdPASS,  0, "P1" },
        { "isr_split_p3", 0xFFFFU + 3U,    0xFFFFU,         pdPASS,  0, "P1" },
        { "isr_split_p4", 0xFFFFU + 4U,    0xFFFFU,         pdFALSE, 1, "P2" },
    };

    const M1TestCase_t xPosCtrl =
    { "oracle_pos_ctrl", ulMid + 1U, ulMid, pdPASS, 0, "CTRL" };
    const M1TestCase_t xNegCtrl =
    { "oracle_neg_ctrl", ulMid + 4U, ulMid, pdFALSE, 1, "CTRL" };

    M1Stats_t xAll = { 0 };
    M1Stats_t xP1 = { 0 };
    M1Stats_t xP2 = { 0 };
    M1Stats_t xPos = { 0 };
    M1Stats_t xNeg = { 0 };
    size_t i;
    FILE * pxLog;
    const char * pcLogPath = getenv( "M1_L3_LOG" );

    if( ( pcLogPath == NULL ) || ( pcLogPath[ 0 ] == '\0' ) )
    {
        pcLogPath = "l3_range_test.log";
    }

    pxLog = fopen( pcLogPath, "w" );
    if( pxLog == NULL )
    {
        perror( "fopen log" );
        return 2;
    }

    fprintf( pxLog, "M1 L3 independent range-check tests\n" );
    fprintf( pxLog, "queuesetALLOWABLE_RX_DEVIATION=%d\n", queuesetALLOWABLE_RX_DEVIATION );
    fprintf( pxLog, "configASSERT: expected fires scored as P2 PASS (not harness failure)\n\n" );

    for( i = 0; i < ( sizeof( xCases ) / sizeof( xCases[ 0 ] ) ); i++ )
    {
        int xPass = prvRunCase( &xCases[ i ], pxLog );
        prvAdd( &xAll, xPass );
        if( strcmp( xCases[ i ].pcProperty, "P1" ) == 0 )
        {
            prvAdd( &xP1, xPass );
        }
        else
        {
            prvAdd( &xP2, xPass );
        }
    }

    fprintf( pxLog, "\n--- oracle controls ---\n" );
    prvAdd( &xPos, prvRunCase( &xPosCtrl, pxLog ) );
    prvAdd( &xNeg, prvRunCase( &xNegCtrl, pxLog ) );

    fprintf( pxLog, "\nSUMMARY P1 pass=%d fail=%d total=%d\n", xP1.xPass, xP1.xFail, xP1.xTotal );
    fprintf( pxLog, "SUMMARY P2 pass=%d fail=%d total=%d\n", xP2.xPass, xP2.xFail, xP2.xTotal );
    fprintf( pxLog, "SUMMARY ALL pass=%d fail=%d total=%d\n", xAll.xPass, xAll.xFail, xAll.xTotal );
    fprintf( pxLog, "ORACLE_POS %s\n", ( xPos.xFail == 0 && xPos.xPass == 1 ) ? "PASS" : "FAIL" );
    fprintf( pxLog, "ORACLE_NEG %s\n", ( xNeg.xFail == 0 && xNeg.xPass == 1 ) ? "PASS" : "FAIL" );

    printf( "P1 %d/%d  P2 %d/%d  ALL %d/%d  oracle_pos=%s oracle_neg=%s\n",
            xP1.xPass, xP1.xTotal, xP2.xPass, xP2.xTotal, xAll.xPass, xAll.xTotal,
            ( xPos.xFail == 0 && xPos.xPass == 1 ) ? "PASS" : "FAIL",
            ( xNeg.xFail == 0 && xNeg.xPass == 1 ) ? "PASS" : "FAIL" );

    fclose( pxLog );

    return ( ( xAll.xFail == 0 ) && ( xPos.xFail == 0 ) && ( xNeg.xFail == 0 ) ) ? 0 : 1;
}
