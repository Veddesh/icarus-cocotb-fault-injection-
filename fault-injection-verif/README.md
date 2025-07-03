# 🧪 Stable Cocotb Fault Injection Framework (Up-Down Counter Example)

This repository provides a **stable and upgraded fault injection tool** for RTL designs using [Cocotb](https://www.cocotb.org/) and [Yosys](https://yosyshq.net/yosys/). It is compatible with the latest versions of both tools, including Cocotb’s `async`/`await` syntax and Yosys’s JSON netlist format.

> ✅ Based on and **upgraded from**: [https://gitlab.cern.ch/tmrg/cocotb_fault_injection](https://gitlab.cern.ch/tmrg/cocotb_fault_injection)  
> ✅ Legacy Python dependencies removed  
> ✅ Full support for native JSON parsing from bleeding-edge Yosys  
> ✅ Works with any RTL design — the included Up-Down Counter is just an example  
> ✅ Async/await testbench style supported out of the box

---

## 📂 Repository Structure

```
stable-cocotb-fault-injection-up-down-counter/
├── Makefile                    # Main makefile to run yosys and simulation
├── yosys_script.ys             # Yosys synthesis script for generating JSON netlist
├── rtl/                        # Folder for RTL designs
│   └── up_down_counter.v
├── sim/                        # Cocotb simulation files
│   ├── makefile                # Cocotb-specific makefile
│   └── test_up_down_counter.py # Async/await testbench
├── cocotb_fault_injection/     # Fault injection tool source code
│   ├── __init__.py
│   ├── fault_injector.py
│   ├── strategy.py
│   ├── goal.py
│   ├── timer.py
│   └── yosys_if.py
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

- Python 3.8 or higher  
- Yosys (with JSON backend support)  
- Cocotb (latest version supporting `async`/`await`)  
- Icarus Verilog (`iverilog`)  

Install cocotb:

```bash
pip install cocotb
```

---

### 2️⃣ Generate the Yosys Netlist

```bash
make yosys
```

This creates `netlist.json` using `yosys_script.ys`.

---

### 3️⃣ Run Simulation with Fault Injection

```bash
make run
```

This parses the netlist, injects faults, and runs the simulation using Cocotb.

---

## 🧠 How It Works

- RTL is synthesized with Yosys to generate a JSON netlist.  
- The tool parses this JSON and identifies places to inject faults (e.g., DFFs).  
- Fault injection occurs during simulation using defined timing strategies.  
- Cocotb testbenches stimulate the DUT and observe faulty behaviors.

---

## 🧪 Example: Up-Down Counter

An example 4-bit up-down counter is included to demonstrate usage. The testbench (`test_up_down_counter.py`) uses `async`/`await` to drive and monitor the DUT during SEE injection.

---

## 🧬 Use with Your Own RTL

1. Replace `rtl/up_down_counter.v` with your own design.  
2. Modify `yosys_script.ys` to synthesize your top module.  
3. Create a new testbench in the `sim/` folder.  
4. Update `sim/makefile` with your module name.  

Then run:

```bash
make yosys
make run
```

---

## ✍️ Example Cocotb Testbench

```python
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_up_down_counter(dut):
    dut.reset.value = 1
    await Timer(10, units="ns")
    dut.reset.value = 0

    for i in range(20):
        dut.updown.value = 1  # Count up
        dut.enable.value = 1
        await Timer(10, units="ns")
```

---

## 📌 Notes

- Supports multiple fault injection strategies (random, Poisson, sequential)  
- Faults are injected dynamically during simulation  
- Extendable for different fault models or RTL targets  

---



## 👤 Author

**Veddesh**  
GitHub: [https://github.com/Veddesh](https://github.com/Veddesh)

---

## 🏷️ Tags

`#FaultInjection` `#Cocotb` `#Yosys` `#SEE` `#DigitalDesign` `#RTL` `#Verification` `#Python` `#Verilog`
