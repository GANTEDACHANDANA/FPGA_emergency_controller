#!/usr/bin/env python3
"""Compact Cocotb ESD Controller Test Suite"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

class ESDTester:
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log
        
    async def reset_dut(self):
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 100)
        self.dut.rst_n.value = 1
        await ClockCycles(self.dut.clk, 100)
    
    async def pulse_ack(self):
        self.dut.ui_in.value = (self.dut.ui_in.value & 0xFB)
        await ClockCycles(self.dut.clk, 10)
        self.dut.ui_in.value = (self.dut.ui_in.value | 0x04)
        await ClockCycles(self.dut.clk, 10)
    
    async def kick_watchdog(self):
        self.dut.ui_in.value = (self.dut.ui_in.value | 0x08)
        await ClockCycles(self.dut.clk, 2)
        self.dut.ui_in.value = (self.dut.ui_in.value & 0xF7)
    
    def set_estop(self, a=None, b=None):
        if a is not None:
            self.dut.ui_in.value = (self.dut.ui_in.value & 0xFE) | a
        if b is not None:
            self.dut.ui_in.value = (self.dut.ui_in.value & 0xFD) | (b << 1)
    
    async def auto_kick(self, cycles):
        for _ in range(cycles // 10000):
            await self.kick_watchdog()
            await ClockCycles(self.dut.clk, 9998)
    
    def check_state(self, name, exp_shutdown, exp_led):
        uo_out = int(self.dut.uo_out.value)
        shutdown, led = uo_out & 0x01, (uo_out & 0x02) >> 1
        passed = shutdown == exp_shutdown and led == exp_led
        status = "✓ PASS" if passed else "✗ FAIL"
        self.log.info(f"{status}: {name} - SHUTDOWN={shutdown}, LED={led}")
        return passed

@cocotb.test()
async def test_esd_controller(dut):
    """Comprehensive ESD controller test"""
    
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    t = ESDTester(dut)
    
    # Initialize
    dut.ui_in.value = 0x0F
    dut.ena.value = 1
    
    passed = 0
    total = 0
    
    # Test 1: Reset
    await t.reset_dut()
    await ClockCycles(dut.clk, 1000)
    total += 1
    if t.check_state("Reset", 1, 1): passed += 1
    
    # Test 2: ACK
    await t.pulse_ack()
    await ClockCycles(dut.clk, 1000)
    total += 1
    if t.check_state("ACK", 1, 1): passed += 1
    
    # Test 3: Normal Operation
    kick_task = cocotb.start_soon(t.auto_kick(2000000))
    await ClockCycles(dut.clk, 50000)
    total += 1
    if t.check_state("Normal", 0, 0): passed += 1
    
    # Test 4: E-STOP A
    t.set_estop(a=0)
    kick_task.kill()
    await ClockCycles(dut.clk, 1000)
    total += 1
    if t.check_state("E-STOP A", 1, 1): passed += 1
    
    # Recovery A
    t.set_estop(a=1)
    await t.pulse_ack()
    kick_task = cocotb.start_soon(t.auto_kick(1000000))
    await ClockCycles(dut.clk, 50000)
    total += 1
    if t.check_state("Recovery A", 0, 0): passed += 1
    
    # Test 5: E-STOP B
    t.set_estop(b=0)
    kick_task.kill()
    await ClockCycles(dut.clk, 1000)
    total += 1
    if t.check_state("E-STOP B", 1, 1): passed += 1
    
    # Recovery B
    t.set_estop(b=1)
    await t.pulse_ack()
    kick_task = cocotb.start_soon(t.auto_kick(1000000))
    await ClockCycles(dut.clk, 50000)
    total += 1
    if t.check_state("Recovery B", 0, 0): passed += 1
    
    # Test 6: Watchdog Timeout
    kick_task.kill()
    await ClockCycles(dut.clk, 30000000)
    total += 1
    if t.check_state("Watchdog", 1, 1): passed += 1
    
    # Summary
    t.log.info(f"=== Results: {passed}/{total} passed ===")
    if passed == total:
        t.log.info("🎉 All tests PASSED!")
    else:
        t.log.error(f"❌ {total - passed} tests FAILED")
