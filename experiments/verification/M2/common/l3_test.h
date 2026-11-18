#ifndef L3_TEST_H
#define L3_TEST_H

/**
 * @brief Start the property-specific independent L3 verification task(s).
 */
void vStartL3Verification( void );

/**
 * @brief MemManage recovery used by independent L3 builds.
 */
void vHandleMemoryFault( uint32_t * pulFaultStackAddress );

#endif /* L3_TEST_H */
