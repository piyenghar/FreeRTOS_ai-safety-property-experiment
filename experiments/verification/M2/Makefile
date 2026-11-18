# Independent L3 verification builds for SP1/SP2 and pilot-mpu integration.
# Does not modify FreeRTOS/Demo/.../mpu_demo.c or pilot branch sources in-place.
#
# Standalone oracle firmware:
#   make PROPERTY=sp1 CONTROL=pos DEBUG=1
#   make PROPERTY=sp1 CONTROL=neg DEBUG=1
#   make PROPERTY=sp2 CONTROL=pos DEBUG=1
#   make PROPERTY=sp2 CONTROL=neg DEBUG=1
#
# Pilot-derived mpu_demo.c (isolated copy / worktree file):
#   make PROPERTY=pilot_mpu CONTROL=pos PILOT_ID=t1 \
#        PILOT_MPU_DEMO=/path/to/mpu_demo.c DEBUG=1
#   make PROPERTY=pilot_mpu CONTROL=neg PILOT_ID=t1 \
#        PILOT_MPU_DEMO=/path/to/mpu_demo_sp1neg.c DEBUG=1

PROPERTY              ?= sp1
CONTROL               ?= pos
DEBUG                 ?= 1
PILOT_ID              ?= unknown

CC                     = arm-none-eabi-gcc
SIZE                   = arm-none-eabi-size
BIN                   := RTOSDemo.axf

ifeq ($(PROPERTY),pilot_mpu)
    BUILD_DIR         := build/pilot_$(PILOT_ID)_$(CONTROL)
else
    BUILD_DIR         := build/$(PROPERTY)_$(CONTROL)
endif

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

ifeq ($(PROPERTY),sp1)
    SOURCE_FILES      += $(VER_DIR)/common/l3_app_main.c
    SOURCE_FILES      += $(VER_DIR)/common/l3_uart.c
    SOURCE_FILES      += $(VER_DIR)/sp1/l3_sp1.c
    ifeq ($(CONTROL),neg)
        CPPFLAGS      += -DL3_SP1_NEGATIVE=1
    else
        CPPFLAGS      += -DL3_SP1_NEGATIVE=0
    endif
else ifeq ($(PROPERTY),sp2)
    SOURCE_FILES      += $(VER_DIR)/common/l3_app_main.c
    SOURCE_FILES      += $(VER_DIR)/common/l3_uart.c
    SOURCE_FILES      += $(VER_DIR)/sp2/l3_sp2.c
    ifeq ($(CONTROL),neg)
        CPPFLAGS      += -DL3_SP2_NEGATIVE=1
    else
        CPPFLAGS      += -DL3_SP2_NEGATIVE=0
    endif
else ifeq ($(PROPERTY),pilot_mpu)
    ifeq ($(PILOT_MPU_DEMO),)
        $(error PILOT_MPU_DEMO must point to the pilot mpu_demo.c (or isolated copy))
    endif
    # Demo app_main + pilot (or patched) mpu_demo.c — verification stays outside pilots.
    SOURCE_FILES      += $(DEMO_DIR)/app_main.c
    SOURCE_FILES      += $(PILOT_MPU_DEMO)
else
    $(error PROPERTY must be sp1, sp2, or pilot_mpu)
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
