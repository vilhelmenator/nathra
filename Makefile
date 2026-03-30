# Nathra — build the native bootstrap compiler
#
# Usage:
#   make                 Build the native compiler dylib from pre-generated C
#   make regenerate      Regenerate C from .py sources (needs Python compiler)
#   make test            Run the test suite
#   make bootstrap       Run bootstrap verification
#   make clean           Remove build artifacts

# ── Platform detection ───────────────────────────────────────────────────
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
  DYLIB_EXT  := dylib
  SHARED     := -dynamiclib
else ifeq ($(UNAME),Linux)
  DYLIB_EXT  := so
  SHARED     := -shared -fPIC
else
  DYLIB_EXT  := dll
  SHARED     := -shared
endif

# ── Toolchain ────────────────────────────────────────────────────────────
CC       ?= cc
CFLAGS   ?= -O2 -w
RUNTIME  := runtime
GEN      := native/generated
BUILD    := build

DYLIB    := $(BUILD)/compiler_native.$(DYLIB_EXT)

# All generated .c files (order doesn't matter for compilation)
SRCS := $(wildcard $(GEN)/*.c)
OBJS := $(patsubst $(GEN)/%.c,$(BUILD)/%.o,$(SRCS))

# ── Targets ──────────────────────────────────────────────────────────────
.PHONY: all clean regenerate test bootstrap

all: $(DYLIB)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: $(GEN)/%.c | $(BUILD)
	$(CC) $(CFLAGS) -fPIC -I$(RUNTIME) -I$(GEN) -c $< -o $@

$(DYLIB): $(OBJS)
	$(CC) $(SHARED) $^ -o $@
	@echo ""
	@echo "Built $(DYLIB)"

# Regenerate native/generated/ from native/src/*.py (requires Python compiler)
regenerate:
	python3 scripts/regenerate.py

# Run the test suite using the Python compiler
test:
	@python3 -c "\
	import subprocess, glob, sys; \
	sys.path.insert(0, '.'); \
	tests = sorted(glob.glob('tests/test_*.py')); \
	fails = []; \
	[fails.append(t) for t in tests \
	 if subprocess.run(['python3', 'compiler/compiler.py', t], \
	    capture_output=True, timeout=30).returncode != 0]; \
	print(f'{len(tests)-len(fails)}/{len(tests)} tests passed'); \
	sys.exit(1 if fails else 0)"

# Run bootstrap verification (requires dylib to be built)
bootstrap: $(DYLIB)
	python3 scripts/bootstrap_test.py

clean:
	rm -rf $(BUILD)
