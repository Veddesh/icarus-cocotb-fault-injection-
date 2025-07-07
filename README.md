# Cocotb-fault-injection 

This repository provides an upgraded version of the [cocotb_fault_injection tool developed by CERN TMRG](https://gitlab.cern.ch/tmrg/cocotb_fault_injection), designed for fault injection in hardware verification using [cocotb](https://github.com/cocotb/cocotb). This enhanced implementation includes:

- **Parsing Yosys-generated JSON** to detect flip-flop locations.
- **Selective fault injection** via `include_names` and `exclude_names` signal filtering.
- **Support for both SEU (bit flips in FFs) and SET (transient glitches on wires).**
- **Improved integration with cocotb testbenches.**
- **Parameterizable fault timing and injection goals.**

---

## Features

- **Yosys Integration:** Parse synthesized JSON to map flip-flop locations accurately.
- **Signal Filtering:** Restrict fault injection to specific signal name patterns using `include_names` and `exclude_names`.
- **Custom Timing:** Inject faults with bounded-random delays (MTTF, transient duration).
- **Fault Modes:** Support for both Single Event Upset (SEU) and Single Event Transient (SET).
- **Injection Control:** Stop after a fixed number of SEE (single-event effects) or run indefinitely.

---

## Repository Structure

```
.
.
├── cocotb_fault_injection/
│   ├── fault_injector.py        # Core logic for fault injection
│   ├── strategy.py              # Injection strategy (e.g., RandomInjectionStrategy)
│   ├── goal.py                  # Fault injection stopping criteria
│   ├── timer.py                 # Bounded and fixed time models
│   ├── yosys_if.py              # Parses Yosys-generated JSON netlist
│   ├── yosys_json_parser.py     # Helpers for JSON parsing and flip-flop mapping
│   ├── setup.py                 # Environment setup logic (if any)
├── test_uart.py                 # Cocotb testbench (TX/RX with and without faults)
├── mktest.v, Counter.v, SizedFIFO.v  # RTL modules for the UART DUT
├── yosys.json                   # Yosys-generated netlist with FF information
├── Makefile                     # 3-step simulation flow using yosys + iverilog + vvp

```
---

## Prerequisites

- Python 3.7+
- [cocotb](https://github.com/cocotb/cocotb)
- [Yosys](https://github.com/YosysHQ/yosys) (for RTL-to-JSON synthesis)
- Icarus Verilog or other supported simulators

---

## How It Works

1. **Synthesize RTL via Yosys:**

   ```bash
   yosys -p 'read_verilog mktest.v Counter.v SizedFIFO.v; prep -top mktest; write_json yosys.json'
   ```

2. **Inject faults based on parsed flip-flop signals during simulation.**

3. **Control fault injection** using strategies like random timing and injection limits.

---

## Testbench Usage

The `HierarchyFaultInjector` is used as follows:

```python
from cocotb_fault_injection import (
    HierarchyFaultInjector,
    BoundedRandomTimer,
    RandomInjectionStrategy,
    TotalSEEs
)

async def start_fault_injection(dut):
    injector = HierarchyFaultInjector(
        root=dut,
        exclude_names=["CLK", "RST_N"],
        include_names=["uart_"],
        mttf_timer=BoundedRandomTimer(mttf_min=50, mttf_max=100, units="ns"),
        transient_duration_timer=BoundedRandomTimer(mttf_min=10, mttf_max=20, units="ns"),
        injection_strategy=RandomInjectionStrategy(),
        injection_goal=TotalSEEs(30),
        log_level=logging.INFO
    )
    cocotb.start_soon(injector.start())
    return injector
```

This will:
- Randomly inject up to 30 SEE events
- Only in signals whose names match `"uart_"`
- Exclude clock/reset signals

---

## Makefile Flow

The `Makefile` automates the entire process:

```makefile
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = mktest
MODULE = test_uart
JSON_FILE = yosys.json

VERILOG_SOURCES  = mktest.v Counter.v SizedFIFO.v
COCOTB_VPI_DIR = $(wildcard $(PWD)/cocotb_env/lib/python3.*/site-packages/cocotb/libs)

all: run

run: simv
	@echo "--- [3/3] Running simulation with vvp ---"
	MODULE=$(MODULE) TOPLEVEL=$(TOPLEVEL) COCOTB_RESOLVE_X=ZEROS \
	vvp -M $(COCOTB_VPI_DIR) -m libcocotbvpi_icarus simv

simv: $(VERILOG_SOURCES) $(JSON_FILE)
	@echo "--- [2/3] Compiling Verilog sources with iverilog ---"
	iverilog -g2012 -o simv -D COCOTB_SIM=1 -s $(TOPLEVEL) $(VERILOG_SOURCES)

$(JSON_FILE): $(VERILOG_SOURCES)
	@echo "--- [1/3] Generating design JSON with Yosys ---"
	yosys -p 'read_verilog $(VERILOG_SOURCES); prep -top $(TOPLEVEL); write_json $(JSON_FILE)'

clean:
	rm -rf simv *.vcd yosys.json
```

To run the simulation with logging at `INFO` level:

```bash
make COCOTB_LOG_LEVEL=INFO
```

This suppresses unwanted debug prints from cocotb internals and focuses only on relevant logs.

---

## Supported Injection Modes

| Mode                  | Description                                    |
|-----------------------|------------------------------------------------|
| `TotalSEEs(n)`        | Inject exactly `n` SEE events                  |
| `SEEsPerNode(k)`      | Inject `k` faults per eligible signal          |
| `InfiniteInjection()` | Inject indefinitely until `.stop()` is called |

---

## Example Output

```
INFO FaultInjector.default     Starting SEE injection.
INFO FaultInjector.default     SEU candidates: 45, SET candidates: 112
INFO FaultInjector.default_see SEE ID 1: SET in mktest.uart_rBaudTickCounter[0]
INFO FaultInjector.default_see SEE ID 2: SEU in mktest.uart_rXmitBitCount[3]
```

A final summary is printed after simulation:

```
Injected 30 SEEs into 157 candidate signals.
```

---

## License

This project is derived from open-source work at CERN (TMRG cocotb_fault_injection) and follows the same licensing terms unless otherwise specified.

## Contact

For contributions, questions, or support:
```
Veddesh RGM  
Email: veddesh18@gmail.com  
Institution: College of Engineering, Guindy  
Focus: Fault Injection, Digital Verification, Space-grade Reliability


