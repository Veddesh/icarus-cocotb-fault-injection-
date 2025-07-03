TOPLEVEL_LANG = verilog
TOPLEVEL = up_down_counter
MODULE = up_down_counter_tb
SIM = icarus
VERILOG_SOURCES = $(shell pwd)/up_down_counter.v

all: run

yosys:
	yosys -p "read_verilog -sv $(TOPLEVEL).v; prep -top $(TOPLEVEL); write_json yosys.json"

run:
	COCOTB_REDUCED_LOG_FMT=1 \
	make -f $(shell cocotb-config --makefiles)/Makefile.sim \
	    SIM=$(SIM) TOPLEVEL=$(TOPLEVEL) MODULE=$(MODULE) \
	    TOPLEVEL_LANG=$(TOPLEVEL_LANG) VERILOG_SOURCES="$(VERILOG_SOURCES)"

clean:
	rm -rf sim_build __pycache__ *.vcd *.fst results.xml yosys.json
