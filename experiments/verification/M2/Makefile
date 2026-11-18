# Independent L3 verification builds for SP1/SP2.
# Does not modify FreeRTOS/Demo/.../mpu_demo.c or pilot sources.
#
# Usage:
#   make PROPERTY=sp1 CONTROL=pos DEBUG=1
#   make PROPERTY=sp1 CONTROL=neg DEBUG=1
#   make PROPERTY=sp2 CONTROL=pos DEBUG=1
#   make PROPERTY=sp2 CONTROL=neg DEBUG=1

PROPERTY              ?= sp1
CONTROL               ?= pos
DEBUG                 ?= 1

CC                     = arm-none-eabi-gcc
SIZE                   = arm-none-eabi-size
BIN                   := RTOSDemo.axf

BUILD_DIR             := build/$(PROPERTY)_$(CONTROL)

ROOT                  := $(abspath ../../..)
DEMO_DIR              := $(ROOT)/FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC
KERNEL_DIR            := $(ROOT)/FreeRTOS/Source
VER_DIR               := $(abspath .)

SOURCE_FILES          :=
SOURCE_FILES          += $(DEMO_DIR)/init/startup.c
SOURCE_FILES          += $(DEMO_DIR)/syscall.c
SOURCE_FILES          += $(DEMO_DIR)/main.c
SOURCE_FILES          += $(KERNEL_DIR)/portable/GCC/ARM_CM3_MPU/port.c
SOURCE_FILES          += $(KERNEL_DIR)/portable/GCC/ARM_CM3_MPU/mpu_wrappers_v2_asm.c
SOURCE_FILES          += $(KERNEL_DIR)/portable/Common/mpu_wrappers.c
SOURCE_FILES          += $(KERNEL_DIR)/portable/Common/mpu_wrappers_v2.c
SOURCE_FILES          += $(KERNEL_DIR)/tasks.c
SOURCE_FILES          += $(KERNEL_DIR)/list.c
SOURCE_FILES          += $(KERNEL_DIR)/queue.c
SOURCE_FILES          += $(KERNEL_DIR)/timers.c
SOURCE_FILES          += $(KERNEL_DIR)/event_groups.c
SOURCE_FILES          += $(KERNEL_DIR)/portable/MemMang/heap_4.c
SOURCE_FILES          += $(KERNEL_DIR)/stream_buffer.c
SOURCE_FILES          += $(VER_DIR)/common/l3_app_main.c
SOURCE_FILES          += $(VER_DIR)/common/l3_uart.c

ifeq ($(PROPERTY),sp1)
    SOURCE_FILES      += $(VER_DIR)/sp1/l3_sp1.c
    ifeq ($(CONTROL),neg)
        CPPFLAGS      += -DL3_SP1_NEGATIVE=1
    else
        CPPFLAGS      += -DL3_SP1_NEGATIVE=0
    endif
else ifeq ($(PROPERTY),sp2)
    SOURCE_FILES      += $(VER_DIR)/sp2/l3_sp2.c
    ifeq ($(CONTROL),neg)
        CPPFLAGS      += -DL3_SP2_NEGATIVE=1
    else
        CPPFLAGS      += -DL3_SP2_NEGATIVE=0
    endif
else
    $(error PROPERTY must be sp1 or sp2)
endif

INCLUDE_DIRS          += -I$(VER_DIR)/common
INCLUDE_DIRS          += -I$(DEMO_DIR)
INCLUDE_DIRS          += -I$(DEMO_DIR)/CMSIS
INCLUDE_DIRS          += -I$(KERNEL_DIR)/include
INCLUDE_DIRS          += -I$(KERNEL_DIR)/portable/GCC/ARM_CM3_MPU

CPPFLAGS              += -DHEAP4

CFLAGS                += -mthumb -mcpu=cortex-m3
ifeq ($(DEBUG),1)
    CFLAGS            += -g3 -Og -ffunction-sections -fdata-sections
else
    CFLAGS            += -Os -ffunction-sections -fdata-sections
endif
CFLAGS                += -Wall -Wextra -Wshadow -Wno-unused-parameter
CFLAGS                += $(INCLUDE_DIRS)

LDFLAGS                = -T $(DEMO_DIR)/scripts/mps2_m3.ld
LDFLAGS               += -Xlinker -Map=$(BUILD_DIR)/output.map
LDFLAGS               += -Xlinker --gc-sections
LDFLAGS               += -nostdlib

OBJ_FILES             := $(addprefix $(BUILD_DIR)/,$(notdir $(SOURCE_FILES:.c=.o)))

vpath %.c $(sort $(dir $(SOURCE_FILES)))

.PHONY: all clean

all: $(BUILD_DIR)/$(BIN)

$(BUILD_DIR)/$(BIN): $(OBJ_FILES)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) $(LDFLAGS) $+ -o $(@)
	$(SIZE) $(@)

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) -MMD -c $< -o $@

clean:
	rm -rf build
