import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_fault_injection import (
    HierarchyFaultInjector,
    BoundedRandomTimer,
    RandomInjectionStrategy,
    SEEsPerNode
)
import logging

@cocotb.test()
async def counter_test(dut):
    """🔁 Up-Down Counter Test with Fault Injection"""

    cocotb.log.setLevel(logging.INFO)
    dut._log.info("🚦 Running Up/Down Counter Test")

    # Start clock at 10 ns period
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst.value = 1
    dut.up.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # Count up for 5 cycles
    for i in range(5):
        await RisingEdge(dut.clk)
        dut._log.info(f"Cycle {i}: count={int(dut.count.value)}")

    # Inject faults after a few cycles
    dut._log.info("💥 Starting fault injection")
    seugen = HierarchyFaultInjector(
        root=dut,
        exclude_names=["clk", "rst"],
        mttf_timer=BoundedRandomTimer(mttf_min=80, mttf_max=200, units="ns"),
        transient_duration_timer=BoundedRandomTimer(mttf_min=10, mttf_max=20, units="ns"),
        injection_strategy=RandomInjectionStrategy(),
        injection_goal=SEEsPerNode(20),
        log_level=logging.DEBUG
    )
    cocotb.start_soon(seugen.start())
    # After cocotb.start_soon(seugen.start()):
    await Timer(200, units="ns")  # allow up to 200 ns for an injection
    seugen.stop()
    await seugen.join()

     
    # Now count down for 5 cycles
    dut.up.value = 0
    for i in range(5, 15):
        await RisingEdge(dut.clk)
        dut._log.info(f"Cycle {i}: count={int(dut.count.value)}")

    # Stop injection and wait for it to finish
    seugen.stop()
    await seugen.join()
    seugen.print_summary()

    dut._log.info("✅ Test completed.")
