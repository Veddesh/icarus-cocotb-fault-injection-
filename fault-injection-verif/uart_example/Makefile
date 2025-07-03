# =================================================================
# Final, Explicit-Path Makefile for Icarus Verilog
# =================================================================

# --- Configuration ---
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = mktest
MODULE = test_uart
JSON_FILE = yosys.json

# --- Source Files ---
VERILOG_SOURCES  = mktest.v
VERILOG_SOURCES += Counter.v
VERILOG_SOURCES += SizedFIFO.v

# --- Automatically find the Cocotb VPI library directory WITHIN your project's virtual env ---
# This wildcard command finds the correct path, avoiding system-wide libraries.
COCOTB_VPI_DIR = $(wildcard $(PWD)/cocotb_env/lib/python3.*/site-packages/cocotb/libs)


# --- Main Targets ---
# The default target 'make' will build and run the simulation.
all: run

# This target runs the simulation, and depends on the compiled 'simv' file.
run: simv
	@echo "--- [3/3] Running simulation with vvp ---"
	MODULE=$(MODULE) TOPLEVEL=$(TOPLEVEL) COCOTB_RESOLVE_X=ZEROS \
	vvp -M $(COCOTB_VPI_DIR) -m libcocotbvpi_icarus simv

# This target compiles the Verilog into the 'simv' executable.
# It depends on the Verilog files and the yosys.json file.
simv: $(VERILOG_SOURCES) $(JSON_FILE)
	@echo "--- [2/3] Compiling Verilog sources with iverilog ---"
	iverilog -g2012 -o simv -D COCOTB_SIM=1 -s $(TOPLEVEL) $(VERILOG_SOURCES)

# --- Yosys JSON Generation ---
# This rule creates the yosys.json file.
$(JSON_FILE): $(VERILOG_SOURCES)
	@echo "--- [1/3] Generating design JSON with Yosys ---"
	@yosys -p 'read_verilog $(VERILOG_SOURCES); prep -top $(TOPLEVEL); write_json $(JSON_FILE)'


# --- Clean Rule ---
# Removes all generated files.
.PHONY: all run simv clean
clean:
	@echo "--- Cleaning generated files ---"
	@rm -rf simv *.vcd yosys.json
