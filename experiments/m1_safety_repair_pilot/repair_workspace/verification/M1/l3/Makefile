# Host-native independent L3 tests for QueueSet range checking.
CC     ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O0 -g
BUILD  := build
ifeq ($(OS),Windows_NT)
  BIN := $(BUILD)/l3_range_test.exe
  MKDIR_P := mkdir
  RM_RF := rmdir /s /q
else
  BIN := $(BUILD)/l3_range_test
  MKDIR_P := mkdir -p
  RM_RF := rm -rf
endif

.PHONY: all test clean

all: $(BIN)

$(BUILD):
	-$(MKDIR_P) $(BUILD)

$(BIN): l3_range_test.c range_check_under_test.c freertos_stubs.h | $(BUILD)
	$(CC) $(CFLAGS) -I. l3_range_test.c range_check_under_test.c -o $(BIN)

test: $(BIN)
	M1_L3_LOG=../results/l3_range_test.log $(BIN)
	@echo "log: ../results/l3_range_test.log"

clean:
	-$(RM_RF) $(BUILD)
