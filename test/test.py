#!/usr/bin/env python3
"""Compact Cocotb ESD Controller Test Suite"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

class ESDTester:
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log

    async def reset_dut(self):
        self.log.info("Resetting DUT...")
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 5)
        self.dut.rst_n.value = 1
        await ClockCycles(self.dut.clk, 5)

    async def pulse_ack(self):
        self.log.info("Pulsing ACK")
        self.dut.ui_in.value = self.dut.ui_in.value & 0xFB  # clear bit 2
        await ClockCycles(self.dut.clk, 2)
        self.dut.ui_in.value = self.dut.ui_in.value | 0x04  # set bit 2
        await ClockCycles(self.dut.clk, 2)

    async def kick_watchdog(self):
        self.dut.ui_in.value = self.dut.ui_in.value | 0x08  # set bit 3
        await ClockCycles(self.dut.clk, 1)
        self.dut.ui_in.value = self.dut.ui_in.value & 0xF7  # clear bit 3

    def set_estop(self, a=None, b=None):
        if a is not None:
            self.dut.ui_in.value = (self.dut.ui_in.value & 0xFE) | (a & 0x1)  # bit 0
        if b is not None:
            self.dut.ui_in.value = (self.dut.ui_in.value & 0xFD) | ((b & 0x1) << 1)  # bit 1

    async def auto_kick(self, cycles):
        self.log.info(f"Auto kicking watchdog every ~10k cycles for {cycles} total")
        for _ in range(cycles // 10000):
            await self.kick_watchdog()
            await ClockCycles(self.dut.clk, 9998)

    def check_state(self, name, exp_shutdown, exp_led):
        uo = int(self.dut.uo_out.value)
        shutdown = uo & 0x01
        led = (uo >> 1) & 0x01
        passed = (shutdown == exp_shutdown and led == exp_led)
        status = "✅ PASS" if passed else "❌ FAIL"
        self.log.info(f"{status} - {name}: SHUTDOWN={shutdown}, LED={led} (Expected: {exp_shutdown},{exp_led})")
        return passed

@cocotb.test()
async def test_esd_controller(dut):
    """Comprehensive ESD Controller Test"""

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    tester = ESDTester(dut)

    # Initialize
    dut.ui_in.value = 0x0F  # All inputs high (estop_a=1, estop_b=1, ack=1, kick=1)
    dut.ena.value = 1       # Enable always on

    passed = 0
    total = 0

    # Test 1: Reset
    await tester.reset_dut()
    await ClockCycles(dut.clk, 20)
    total += 1
    if tester.check_state("After Reset", 1, 1): passed += 1

    # Test 2: Acknowledge
    await tester.pulse_ack()
    await ClockCycles(dut.clk, 20)
    total += 1
    if tester.check_state("ACK Pulse", 1, 1): passed += 1

    # Test 3: Normal Running with watchdog kicking
    kick_task = cocotb.start_soon(tester.auto_kick(100000))
    await ClockCycles(dut.clk, 1000)
    total += 1
    if tester.check_state("Normal Operation", 0, 0): passed += 1

    # Test 4: Emergency Stop A
    tester.set_estop(a=0)
    kick_task.kill()
    await ClockCycles(dut.clk, 50)
    total += 1
    if tester.check_state("E-STOP A", 1, 1): passed += 1

    # Recovery A
    tester.set_estop(a=1)
    await tester.pulse_ack()
    kick_task = cocotb.start_soon(tester.auto_kick(50000))
    await ClockCycles(dut.clk, 1000)
    total += 1
    if tester.check_state("Recovery A", 0, 0): passed += 1

    # Test 5: Emergency Stop B
    tester.set_estop(b=0)
    kick_task.kill()
    await ClockCycles(dut.clk, 50)
    total += 1
    if tester.check_state("E-STOP B", 1, 1): passed += 1

    # Recovery B
    tester.set_estop(b=1)
    await tester.pulse_ack()
    kick_task = cocotb.start_soon(tester.auto_kick(50000))
    await ClockCycles(dut.clk, 1000)
    total += 1
    if tester.check_state("Recovery B", 0, 0): passed += 1

    # Test 6: Watchdog timeout
    kick_task.kill()
    await ClockCycles(dut.clk, 100000)  # Wait longer than expected
    total += 1
    if tester.check_state("Watchdog Timeout", 1, 1): passed += 1

    # Summary
    tester.log.info(f"=== TEST SUMMARY: {passed}/{total} PASSED ===")
    if passed == total:
        tester.log.info("🎉 All tests passed successfully!")
    else:
        tester.log.error(f"❌ {total - passed} test(s) failed.")
