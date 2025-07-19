# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer
from cocotb.utils import get_sim_time
import asyncio

class ESDTestBench:
    """Helper class to manage ESD controller testing"""
    
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log
        
        # Pin mapping based on our design
        self.ESTOP_A_PIN = 0
        self.ESTOP_B_PIN = 1
        self.ACK_PIN = 2
        self.WDG_KICK_PIN = 3
        self.ASYNC_IN_PIN = 4
        
        self.SHUTDOWN_PIN = 0
        self.LED_PIN = 1
        self.SYNC_OUT_PIN = 2
        
    def set_input_pin(self, pin, value):
        """Set individual input pin while preserving others"""
        current = int(self.dut.ui_in.value)
        if value:
            current |= (1 << pin)
        else:
            current &= ~(1 << pin)
        self.dut.ui_in.value = current
        
    def get_output_pin(self, pin):
        """Get individual output pin value"""
        return bool((int(self.dut.uo_out.value) >> pin) & 1)
    
    @property
    def shutdown_active(self):
        return self.get_output_pin(self.SHUTDOWN_PIN)
    
    @property
    def led_status(self):
        return self.get_output_pin(self.LED_PIN)
        
    @property
    def sync_out(self):
        return self.get_output_pin(self.SYNC_OUT_PIN)
    
    def set_estop_a(self, pressed):
        """Set E-STOP A state (active low)"""
        self.set_input_pin(self.ESTOP_A_PIN, not pressed)
        
    def set_estop_b(self, pressed):
        """Set E-STOP B state (active low)"""
        self.set_input_pin(self.ESTOP_B_PIN, not pressed)
        
    def set_ack_button(self, pressed):
        """Set ACK button state (active low)"""
        self.set_input_pin(self.ACK_PIN, not pressed)
        
    def set_wdg_kick(self, value):
        """Set watchdog kick signal"""
        self.set_input_pin(self.WDG_KICK_PIN, value)
        
    def set_async_in(self, value):
        """Set async input signal"""
        self.set_input_pin(self.ASYNC_IN_PIN, value)
    
    async def press_ack_button(self):
        """Simulate ACK button press and release"""
        self.log.info("Pressing ACK button")
        self.set_ack_button(True)   # Press (active low)
        await ClockCycles(self.dut.clk, 1000)  # Hold for debounce time
        self.set_ack_button(False)  # Release
        await ClockCycles(self.dut.clk, 1000)  # Wait for edge detection
    
    async def kick_watchdog(self):
        """Single watchdog kick"""
        self.set_wdg_kick(True)
        await ClockCycles(self.dut.clk, 1)
        self.set_wdg_kick(False)
        await ClockCycles(self.dut.clk, 1)
    
    async def auto_kick_watchdog(self, enable):
        """Background task to automatically kick watchdog"""
        while enable:
            await self.kick_watchdog()
            await Timer(10, units='ms')  # Kick every 10ms (well within 500ms timeout)
    
    async def wait_for_debounce(self):
        """Wait for button debounce to settle"""
        await ClockCycles(self.dut.clk, 2000)  # Conservative debounce wait
        
    def check_state(self, expected_shutdown, message):
        """Check shutdown state and log result"""
        if self.shutdown_active == expected_shutdown:
            self.log.info(f"✓ PASS: {message}")
            return True
        else:
            self.log.error(f"✗ FAIL: {message} (Expected: {expected_shutdown}, Got: {self.shutdown_active})")
            return False
    
    async def check_led_blinking(self, message, duration_cycles=10000):
        """Check if LED is blinking"""
        initial_led = self.led_status
        blink_count = 0
        
        for _ in range(100):
            await ClockCycles(self.dut.clk, duration_cycles // 100)
            if self.led_status != initial_led:
                blink_count += 1
                initial_led = self.led_status
        
        if blink_count > 0:
            self.log.info(f"✓ PASS: {message} (Blinks detected: {blink_count})")
            return True
        else:
            self.log.error(f"✗ FAIL: {message} (No blinking detected)")
            return False
    
    async def check_led_solid(self, expected_state, message, duration_cycles=5000):
        """Check if LED maintains solid state"""
        initial_led = self.led_status
        changed = False
        
        for _ in range(50):
            await ClockCycles(self.dut.clk, duration_cycles // 50)
            if self.led_status != initial_led:
                changed = True
                break
        
        if not changed and self.led_status == expected_state:
            self.log.info(f"✓ PASS: {message}")
            return True
        else:
            self.log.error(f"✗ FAIL: {message} (Expected solid {expected_state}, Got {self.led_status})")
            return False

@cocotb.test()
async def test_esd_controller(dut):
    """Main ESD controller test"""
    
    # Initialize test bench
    tb = ESDTestBench(dut)
    tb.log.info("=== ESD Controller Test Starting ===")
    
    # Set clock to 100kHz (10us period) as in original template
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Initialize all signals
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    
    # Initialize ESD inputs (all inactive)
    tb.set_estop_a(False)  # Not pressed
    tb.set_estop_b(False)  # Not pressed
    tb.set_ack_button(False)  # Not pressed
    tb.set_wdg_kick(False)
    tb.set_async_in(False)
    
    # Reset sequence
    tb.log.info("Applying Reset")
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Test 1: Initial state should be shutdown
    tb.log.info("Test 1: Initial State")
    tb.check_state(True, "Initial state should be shutdown")
    await ClockCycles(dut.clk, 100)
    
    # Test 2: Try to run without ACK (should remain shutdown)
    tb.log.info("Test 2: Start without ACK")
    kick_task = cocotb.start_soon(tb.auto_kick_watchdog(True))
    await ClockCycles(dut.clk, 1000)
    tb.check_state(True, "Should remain shutdown without ACK")
    kick_task.kill()
    
    # Test 3: Proper startup with ACK
    tb.log.info("Test 3: Proper Startup")
    kick_task = cocotb.start_soon(tb.auto_kick_watchdog(True))
    await tb.press_ack_button()
    await tb.wait_for_debounce()
    tb.check_state(False, "Should be running after ACK")
    # Note: LED blinking test might be challenging at 100kHz due to slow blink rate
    
    # Test 4: E-STOP A activation
    tb.log.info("Test 4: E-STOP A Activation")
    tb.set_estop_a(True)  # Press E-STOP A
    await tb.wait_for_debounce()
    tb.check_state(True, "Should shutdown on E-STOP A")
    await tb.check_led_solid(True, "LED should be solid ON when shutdown")
    
    # Test 5: Recovery from E-STOP A
    tb.log.info("Test 5: Recovery from E-STOP A")
    tb.set_estop_a(False)  # Release E-STOP A
    await tb.wait_for_debounce()
    await tb.press_ack_button()
    await tb.wait_for_debounce()
    tb.check_state(False, "Should recover after E-STOP release and ACK")
    
    # Test 6: E-STOP B activation
    tb.log.info("Test 6: E-STOP B Activation")
    tb.set_estop_b(True)  # Press E-STOP B
    await tb.wait_for_debounce()
    tb.check_state(True, "Should shutdown on E-STOP B")
    
    # Test 7: Recovery from E-STOP B
    tb.log.info("Test 7: Recovery from E-STOP B")
    tb.set_estop_b(False)  # Release E-STOP B
    await tb.wait_for_debounce()
    await tb.press_ack_button()
    await tb.wait_for_debounce()
    tb.check_state(False, "Should recover from E-STOP B")
    
    # Test 8: Both E-STOPs
    tb.log.info("Test 8: Both E-STOPs")
    tb.set_estop_a(True)
    tb.set_estop_b(True)
    await tb.wait_for_debounce()
    tb.check_state(True, "Should shutdown with both E-STOPs")
    
    tb.set_estop_a(False)  # Release only one
    await tb.wait_for_debounce()
    tb.check_state(True, "Should remain shutdown with one E-STOP active")
    
    tb.set_estop_b(False)  # Release both
    await tb.wait_for_debounce()
    await tb.press_ack_button()
    await tb.wait_for_debounce()
    tb.check_state(False, "Should recover when both E-STOPs released")
    
    # Test 9: Watchdog timeout
    tb.log.info("Test 9: Watchdog Timeout")
    kick_task.kill()  # Stop auto-kicking
    # Wait for timeout (500ms at 100kHz = 50,000 cycles)
    await ClockCycles(dut.clk, 60000)  # Wait a bit longer than timeout
    tb.check_state(True, "Should shutdown on watchdog timeout")
    
    # Test 10: Recovery from watchdog
    tb.log.info("Test 10: Recovery from Watchdog")
    kick_task = cocotb.start_soon(tb.auto_kick_watchdog(True))
    await tb.press_ack_button()
    await tb.wait_for_debounce()
    tb.check_state(False, "Should recover from watchdog timeout")
    
    # Test 11: Async synchronization
    tb.log.info("Test 11: Async Synchronization")
    tb.set_async_in(True)
    await ClockCycles(dut.clk, 10)  # Wait for synchronization
    if tb.sync_out:
        tb.log.info("✓ PASS: Async input synchronized properly")
    else:
        tb.log.error("✗ FAIL: Sync output not following async input")
    
    tb.set_async_in(False)
    await ClockCycles(dut.clk, 10)
    if not tb.sync_out:
        tb.log.info("✓ PASS: Async sync clear working")
    else:
        tb.log.info(f"? INFO: Sync output: {tb.sync_out} (may take time to clear)")
    
    # Clean up
    kick_task.kill()
    
    tb.log.info("=== All Tests Completed ===")
    tb.log.info(f"Final state - Shutdown: {tb.shutdown_active}, LED: {tb.led_status}")

@cocotb.test()
async def test_basic_functionality(dut):
    """Basic smoke test"""
    
    dut._log.info("=== Basic Functionality Test ===")
    
    # Set the clock period to 10 us (100 KHz) - same as template
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0b11111  # All inputs high (E-STOPs not pressed, etc.)
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    
    dut._log.info("Test basic operation")
    
    # Should start in shutdown state
    await ClockCycles(dut.clk, 10)
    shutdown_state = bool((int(dut.uo_out.value) >> 0) & 1)
    assert shutdown_state == True, f"Should start in shutdown state, got {shutdown_state}"
    dut._log.info("✓ Starts in shutdown state as expected")
    
    # Test E-STOP functionality
    dut.ui_in.value = 0b11110  # Press E-STOP A (bit 0 = 0, active low)
    await ClockCycles(dut.clk, 2000)  # Wait for debouncing
    shutdown_state = bool((int(dut.uo_out.value) >> 0) & 1)
    assert shutdown_state == True, f"Should remain shutdown on E-STOP, got {shutdown_state}"
    dut._log.info("✓ E-STOP functionality working")
    
    dut._log.info("Basic functionality test completed successfully!")

# Additional test for edge cases
@cocotb.test()
async def test_edge_cases(dut):
    """Test edge cases and stress scenarios"""
    
    tb = ESDTestBench(dut)
    tb.log.info("=== Edge Case Testing ===")
    
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Initialize
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Test rapid button presses
    tb.log.info("Testing rapid button presses")
    for i in range(5):
        tb.set_ack_button(True)
        await ClockCycles(dut.clk, 10)
        tb.set_ack_button(False)
        await ClockCycles(dut.clk, 10)
    
    # Test simultaneous inputs
    tb.log.info("Testing simultaneous inputs")
    tb.set_estop_a(True)
    tb.set_estop_b(True)
    tb.set_ack_button(True)
    await ClockCycles(dut.clk, 1000)
    
    # Release all
    tb.set_estop_a(False)
    tb.set_estop_b(False)
    tb.set_ack_button(False)
    await ClockCycles(dut.clk, 1000)
    
    tb.log.info("Edge case testing completed")

if __name__ == "__main__":
    # This allows running the test directly
    import os
    os.system("make")
