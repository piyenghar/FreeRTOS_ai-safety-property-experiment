#include "l3_uart.h"

#include <stdint.h>

void vL3Report( const char * pcMessage )
{
    volatile uint32_t * const pulUartData = ( volatile uint32_t * ) 0x40004000UL;

    while( *pcMessage != '\0' )
    {
        *pulUartData = ( uint32_t ) ( ( uint8_t ) *pcMessage );
        pcMessage++;
    }

    *pulUartData = ( uint32_t ) '\n';
}
