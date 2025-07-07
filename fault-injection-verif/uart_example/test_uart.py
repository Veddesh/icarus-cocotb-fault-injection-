import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb_fault_injection import (
    HierarchyFaultInjector,
    BoundedRandomTimer,
    RandomInjectionStrategy,
    TotalSEEs
)
import logging


CLOCK_PERIOD_NS = 10
DEFAULT_BAUD_DIVIDER = 5
BIT_PERIOD_NS_DEFAULT = 16 * DEFAULT_BAUD_DIVIDER * CLOCK_PERIOD_NS


TX_REG_ADDR = 0x04
RX_REG_ADDR = 0x08
STATUS_REG_ADDR = 0x0C
DELAY_REG_ADDR = 0x10


def uart_frame(data: int) -> list:
    return [0] + [(data >> i) & 1 for i in range(8)] + [1]

async def reset_dut(dut):
    dut.RST_N.value = 0
    dut.io_SIN.value = 1
    dut.EN_write_req.value = 0
    dut.EN_read_req.value = 0
    await Timer(CLOCK_PERIOD_NS * 5, units="ns")
    dut.RST_N.value = 1
    await Timer(CLOCK_PERIOD_NS * 10, units="ns")
    cocotb.log.info("DUT Reset Complete")

#  TX Test (No Faults) 
@cocotb.test()
async def uart_tx_test(dut):
    cocotb.log.info("Starting UART TX Test")
    cocotb.start_soon(Clock(dut.CLK, CLOCK_PERIOD_NS, units="ns").start())
    await reset_dut(dut)

    tx_byte = 0x5A
    expected_bits = uart_frame(tx_byte)

   
    dut.write_req_addr.value = TX_REG_ADDR
    dut.write_req_data.value = tx_byte
    dut.write_req_size.value = 0
    dut.EN_write_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_write_req.value = 0

    
    dut.write_req_addr.value = DELAY_REG_ADDR
    dut.write_req_data.value = 1
    dut.write_req_size.value = 1
    dut.EN_write_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_write_req.value = 0

    await FallingEdge(dut.io_SOUT)
    await Timer(BIT_PERIOD_NS_DEFAULT / 2, units="ns")

    received_bits = []
    for _ in range(10):
        received_bits.append(dut.io_SOUT.value.integer)
        await Timer(BIT_PERIOD_NS_DEFAULT, units="ns")

    cocotb.log.info(f"TX byte written: 0x{tx_byte:02X}")
    cocotb.log.info(f"Expected frame: {expected_bits}")
    cocotb.log.info(f"Observed frame: {received_bits}")
    assert received_bits == expected_bits, "❌ TX Frame mismatch"
    cocotb.log.info("✅ TX Test Passed")

#  RX Test (No Faults) 
@cocotb.test()
async def uart_rx_test(dut):
    cocotb.log.info("Starting UART RX Test")
    cocotb.start_soon(Clock(dut.CLK, CLOCK_PERIOD_NS, units="ns").start())
    await reset_dut(dut)

    tx_byte = 0xAD
    bits_to_send = uart_frame(tx_byte)

    for bit in bits_to_send:
        dut.io_SIN.value = bit
        await Timer(BIT_PERIOD_NS_DEFAULT, units="ns")
    dut.io_SIN.value = 1
    await Timer(BIT_PERIOD_NS_DEFAULT * 2, units="ns")

    dut.read_req_addr.value = RX_REG_ADDR
    dut.read_req_size.value = 1
    dut.EN_read_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_read_req.value = 0
    await RisingEdge(dut.CLK)

    full_val = dut.read_req.value.integer
    success = full_val & 1
    received_byte = (full_val >> 1) & 0xFF

    cocotb.log.info(f"Received RX byte: 0x{received_byte:02X}")
    assert success == 1, "❌ Read failed (success bit = 0)"
    assert received_byte == tx_byte, f"❌ RX mismatch: got 0x{received_byte:02X}, expected 0x{tx_byte:02X}"
    cocotb.log.info("✅ RX Test Passed")

#  Fault Injector Setup
async def start_fault_injection(dut):
    seugen = HierarchyFaultInjector(
        root=dut,
        exclude_names=["CLK", "RST_N"],
	include_names=["uart_"],
        mttf_timer=BoundedRandomTimer(mttf_min=50, mttf_max=100, units="ns"),
        transient_duration_timer=BoundedRandomTimer(mttf_min=10, mttf_max=20, units="ns"),
        injection_strategy=RandomInjectionStrategy(),
        injection_goal=TotalSEEs(30),
        log_level=logging.INFO
    )
    cocotb.start_soon(seugen.start())
    return seugen

#  TX Test With Faults
@cocotb.test()
async def uart_tx_test_with_fault(dut):
    cocotb.log.info("💥 TX Test with Fault Injection")
    cocotb.start_soon(Clock(dut.CLK, CLOCK_PERIOD_NS, units="ns").start())
    await reset_dut(dut)

    seugen = await start_fault_injection(dut)

    tx_byte = 0xA3
    expected_bits = uart_frame(tx_byte)

    
    dut.write_req_addr.value = TX_REG_ADDR
    dut.write_req_data.value = tx_byte
    dut.write_req_size.value = 0
    dut.EN_write_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_write_req.value = 0

  
    dut.write_req_addr.value = DELAY_REG_ADDR
    dut.write_req_data.value = 1
    dut.write_req_size.value = 1
    dut.EN_write_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_write_req.value = 0

    await FallingEdge(dut.io_SOUT)
    await Timer(BIT_PERIOD_NS_DEFAULT / 2, units="ns")

    received_bits = []
    for _ in range(10):
        received_bits.append(dut.io_SOUT.value.integer)
        await Timer(BIT_PERIOD_NS_DEFAULT, units="ns")

    cocotb.log.info(f"TX byte written: 0x{tx_byte:02X}")
    cocotb.log.info(f"Expected frame: {expected_bits}")
    cocotb.log.info(f"Observed frame: {received_bits}")

    mismatches = []
    for i, (e, o) in enumerate(zip(expected_bits, received_bits)):
        if e != o:
            mismatches.append((i, e, o))
            cocotb.log.warning(f"❌ Bit {i}: expected {e}, got {o}")

    if not mismatches:
        cocotb.log.info("✅ TX output unaffected by fault")
    else:
        cocotb.log.warning(f"⚠️ TX corrupted in {len(mismatches)} bit(s)")

    seugen.stop()
    await seugen.join()
    seugen.print_summary()

#  RX Test With Faults
@cocotb.test()
async def uart_rx_test_with_fault(dut):
    cocotb.log.info("💥 RX Test with Fault Injection")
    cocotb.start_soon(Clock(dut.CLK, CLOCK_PERIOD_NS, units="ns").start())
    await reset_dut(dut)

    seugen = await start_fault_injection(dut)

    tx_byte = 0xC1
    bits_to_send = uart_frame(tx_byte)

    for bit in bits_to_send:
        dut.io_SIN.value = bit
        await Timer(BIT_PERIOD_NS_DEFAULT, units="ns")
    dut.io_SIN.value = 1
    await Timer(BIT_PERIOD_NS_DEFAULT * 2, units="ns")

    dut.read_req_addr.value = RX_REG_ADDR
    dut.read_req_size.value = 1
    dut.EN_read_req.value = 1
    await RisingEdge(dut.CLK)
    dut.EN_read_req.value = 0
    await RisingEdge(dut.CLK)

    full_val = dut.read_req.value.integer
    received_byte = (full_val >> 1) & 0xFF
    expected_byte = tx_byte

    cocotb.log.info(f"Expected RX byte: 0x{expected_byte:02X}")
    cocotb.log.info(f"Received RX byte: 0x{received_byte:02X}")

    if received_byte == expected_byte:
        cocotb.log.info("✅ RX output unaffected by fault")
    else:
        cocotb.log.warning("❌ RX mismatch due to fault")

    seugen.stop()
    await seugen.join()
    seugen.print_summary()
