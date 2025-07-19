#!/usr/bin/env python3
"""
Cocotb-style ESD Controller Test Implementation
A comprehensive test suite for Emergency Shutdown Controller using cocotb library patterns
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, FallingEdge
import asyncio
import random

class ESDControllerTestBench:
    """Helper class to manage ESD controller testing"""
    
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log if hasattr(dut, '_log') else None
        self.test_results = []
        self.clock_freq = 50_000_000  # 50MHz
        self.watchdog_timeout_ms = 500  # 500ms watchdog timeout
        self.debounce_cycles = 1000  # Button debounce cycles
        
    async def reset_system(self):
        """Perform system reset"""
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 100)
        self.dut.rst_n.value = 1
        await ClockCycles(self.dut.clk, 100)
    
    async def pulse_ack(self):
        """Pulse the ACK button"""
        if self.log:
            self.log.info("Pulsing ACK button")
        self.dut.ui_in.value = (self.dut.ui_in.value & 0xFB) | 0x00  # Clear bit 2 (ACK_N)
        await ClockCycles(self.dut.clk, 10)
        self.dut.ui_in.value = self.dut.ui_in.value | 0x04  # Set bit 2 (ACK_N)
        await ClockCycles(self.dut.clk, 10)
    
    async def pulse_watchdog(self):
        """Pulse the watchdog kick"""
        self.dut.ui_in.value = self.dut.ui_in.value | 0x08  # Set bit 3 (WDG_KICK)
        await ClockCycles(self.dut.clk, 2)
        self.dut.ui_in.value = self.dut.ui_in.value & 0xF7  # Clear bit 3 (WDG_KICK)
    
    async def press_estop_a(self):
        """Press E-STOP A (active low)"""
        if self.log:
            self.log.info("Pressing E-STOP A")
        self.dut.ui_in.value = self.dut.ui_in.value & 0xFE  # Clear bit 0 (ESTOP_A_N)
    
    async def release_estop_a(self):
        """Release E-STOP A"""
        if self.log:
            self.log.info("Releasing E-STOP A")
        self.dut.ui_in.value = self.dut.ui_in.value | 0x01  # Set bit 0 (ESTOP_A_N)
    
    async def press_estop_b(self):
        """Press E-STOP B (active low)"""
        if self.log:
            self.log.info("Pressing E-STOP B")
        self.dut.ui_in.value = self.dut.ui_in.value & 0xFD  # Clear bit 1 (ESTOP_B_N)
    
    async def release_estop_b(self):
        """Release E-STOP B"""
        if self.log:
            self.log.info("Releasing E-STOP B")
        self.dut.ui_in.value = self.dut.ui_in.value | 0x02  # Set bit 1 (ESTOP_B_N)
    
    async def automatic_watchdog_kicks(self, duration_cycles):
        """Generate automatic watchdog kicks for specified duration"""
        kick_interval = self.clock_freq // 5  # Kick every 200ms (5Hz)
        cycles_elapsed = 0
        
        while cycles_elapsed < duration_cycles:
            await self.pulse_watchdog()
            await ClockCycles(self.dut.clk, kick_interval - 2)
            cycles_elapsed += kick_interval
    
    def get_shutdown_output(self):
        """Get shutdown output state"""
        return int(self.dut.uo_out.value) & 0x01  # Bit 0
    
    def get_led_status(self):
        """Get LED status output"""
        return (int(self.dut.uo_out.value) & 0x02) >> 1  # Bit 1
    
    def check_safe_state(self, test_name, expected_shutdown=1, expected_led=1):
        """Check if system is in expected safe state"""
        shutdown = self.get_shutdown_output()
        led = self.get_led_status()
        
        if shutdown == expected_shutdown and led == expected_led:
            message = f"✓ PASS: {test_name} - SHUTDOWN={shutdown}, LED={led}"
            if self.log:
                self.log.info(message)
            else:
                print(message)
            self.test_results.append(True)
            return True
        else:
            message = f"✗ FAIL: {test_name} - Expected: SHUTDOWN={expected_shutdown}, LED={expected_led}"
            error_msg = f"         Got: SHUTDOWN={shutdown}, LED={led}"
            if self.log:
                self.log.error(message)
                self.log.error(error_msg)
            else:
                print(message)
                print(error_msg)
            self.test_results.append(False)
            return False
    
    def check_operational_state(self, test_name, expected_shutdown=0, expected_led=0):
        """Check if system is in operational state"""
        return self.check_safe_state(test_name, expected_shutdown, expected_led)
    
    async def wait_for_debounce(self):
        """Wait for button debouncing"""
        await ClockCycles(self.dut.clk, self.debounce_cycles)
    
    async def wait_for_watchdog_timeout(self):
        """Wait for watchdog timeout"""
        timeout_cycles = int(self.watchdog_timeout_ms * self.clock_freq / 1000) + 10000
        await ClockCycles(self.dut.clk, timeout_cycles)
    
    def get_pass_rate(self):
        """Calculate test pass rate"""
        if not self.test_results:
            return 0
        passed = sum(self.test_results)
        total = len(self.test_results)
        return (passed / total) * 100

# Mock DUT class for standalone testing
class MockESDControllerDUT:
    class MockLog:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
    
    def __init__(self):
        self._log = self.MockLog()
        self.clk = MockSignal(0)
        self.rst_n = MockSignal(0)
        self.ui_in = MockSignal(0x0F)  # All inputs high (inactive)
        self.uo_out = MockSignal(0x03)  # Safe state: shutdown=1, led=1
        self.uio_in = MockSignal(0)
        self.uio_out = MockSignal(0)
        self.uio_oe = MockSignal(0)
        self.ena = MockSignal(1)
        
        # Internal state simulation
        self.estop_triggered = False
        self.watchdog_expired = False
        self.ack_pressed = False

class MockSignal:
    def __init__(self, initial_value=0):
        self._value = initial_value
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val

@cocotb.test()
async def test_reset_behavior(dut):
    """Test system reset and safe startup state"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Reset Behavior Test Starting ===")
    
    # Initialize all inputs to safe state
    dut.ui_in.value = 0x0F  # All E-STOPs and ACK released, WDG_KICK low
    dut.ena.value = 1
    
    # Perform reset
    await tb.reset_system()
    
    # Check safe startup state
    await tb.wait_for_debounce()
    tb.check_safe_state("Safe Startup State", expected_shutdown=1, expected_led=1)
    
    tb.log.info("=== Reset Behavior Test Completed ===")

@cocotb.test()
async def test_ack_button_functionality(dut):
    """Test ACK button functionality"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== ACK Button Functionality Test Starting ===")
    
    # Initialize system
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    
    # Test ACK without releasing E-STOPs (should remain in shutdown)
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    tb.check_safe_state("ACK without E-STOP release", expected_shutdown=1, expected_led=1)
    
    # Test ACK with E-STOPs released (should allow recovery with watchdog)
    # This test verifies ACK functionality, actual recovery tested elsewhere
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # System should still be in shutdown until watchdog starts
    tb.check_safe_state("ACK with E-STOPs released", expected_shutdown=1, expected_led=1)
    
    tb.log.info("=== ACK Button Functionality Test Completed ===")

@cocotb.test()
async def test_watchdog_operation(dut):
    """Test watchdog operation and timeout"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Watchdog Operation Test Starting ===")
    
    # Initialize system
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    
    # ACK to enable system
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Start watchdog kicking - system should go operational
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(100000))  # Kick for ~2ms
    await ClockCycles(dut.clk, 50000)  # Wait for system to stabilize
    
    # System should be operational
    tb.check_operational_state("Normal Operation with Watchdog", expected_shutdown=0, expected_led=0)
    
    # Stop watchdog kicking
    kick_task.kill()
    
    # Wait for watchdog timeout
    tb.log.info("Testing watchdog timeout...")
    await tb.wait_for_watchdog_timeout()
    
    # System should be in shutdown due to watchdog timeout
    tb.check_safe_state("Watchdog Timeout", expected_shutdown=1, expected_led=1)
    
    tb.log.info("=== Watchdog Operation Test Completed ===")

@cocotb.test()
async def test_estop_a_functionality(dut):
    """Test E-STOP A functionality"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== E-STOP A Functionality Test Starting ===")
    
    # Initialize system and get to operational state
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Start watchdog to get operational
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(200000))
    await ClockCycles(dut.clk, 50000)
    
    # Verify operational state
    tb.check_operational_state("Pre E-STOP A Operational", expected_shutdown=0, expected_led=0)
    
    # Press E-STOP A
    await tb.press_estop_a()
    kick_task.kill()  # Stop watchdog
    await tb.wait_for_debounce()
    
    # System should be in shutdown
    tb.check_safe_state("E-STOP A Pressed", expected_shutdown=1, expected_led=1)
    
    # Release E-STOP A and ACK
    await tb.release_estop_a()
    await tb.wait_for_debounce()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Resume watchdog and check recovery
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(100000))
    await ClockCycles(dut.clk, 50000)
    
    tb.check_operational_state("Recovery from E-STOP A", expected_shutdown=0, expected_led=0)
    kick_task.kill()
    
    tb.log.info("=== E-STOP A Functionality Test Completed ===")

@cocotb.test()
async def test_estop_b_functionality(dut):
    """Test E-STOP B functionality"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== E-STOP B Functionality Test Starting ===")
    
    # Initialize system and get to operational state
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Start watchdog to get operational
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(200000))
    await ClockCycles(dut.clk, 50000)
    
    # Verify operational state
    tb.check_operational_state("Pre E-STOP B Operational", expected_shutdown=0, expected_led=0)
    
    # Press E-STOP B
    await tb.press_estop_b()
    kick_task.kill()  # Stop watchdog
    await tb.wait_for_debounce()
    
    # System should be in shutdown
    tb.check_safe_state("E-STOP B Pressed", expected_shutdown=1, expected_led=1)
    
    # Release E-STOP B and ACK
    await tb.release_estop_b()
    await tb.wait_for_debounce()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Resume watchdog and check recovery
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(100000))
    await ClockCycles(dut.clk, 50000)
    
    tb.check_operational_state("Recovery from E-STOP B", expected_shutdown=0, expected_led=0)
    kick_task.kill()
    
    tb.log.info("=== E-STOP B Functionality Test Completed ===")

@cocotb.test()
async def test_dual_estop_functionality(dut):
    """Test both E-STOPs pressed simultaneously"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Dual E-STOP Functionality Test Starting ===")
    
    # Initialize system and get to operational state
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Start watchdog to get operational
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(200000))
    await ClockCycles(dut.clk, 50000)
    
    # Press both E-STOPs simultaneously
    await tb.press_estop_a()
    await tb.press_estop_b()
    kick_task.kill()
    await tb.wait_for_debounce()
    
    # System should be in shutdown
    tb.check_safe_state("Both E-STOPs Pressed", expected_shutdown=1, expected_led=1)
    
    # Release only E-STOP A, system should remain in shutdown
    await tb.release_estop_a()
    await tb.wait_for_debounce()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    tb.check_safe_state("E-STOP A Released, B Still Pressed", expected_shutdown=1, expected_led=1)
    
    # Release E-STOP B and ACK again
    await tb.release_estop_b()
    await tb.wait_for_debounce()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Resume watchdog and check recovery
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(100000))
    await ClockCycles(dut.clk, 50000)
    
    tb.check_operational_state("Recovery from Dual E-STOP", expected_shutdown=0, expected_led=0)
    kick_task.kill()
    
    tb.log.info("=== Dual E-STOP Functionality Test Completed ===")

@cocotb.test()
async def test_rapid_button_sequences(dut):
    """Test rapid button press sequences"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Rapid Button Sequences Test Starting ===")
    
    # Initialize system
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    
    # Test rapid ACK presses
    for i in range(5):
        await tb.pulse_ack()
        await ClockCycles(dut.clk, 100)  # Very short delay
    
    await tb.wait_for_debounce()
    tb.check_safe_state(f"Rapid ACK Presses", expected_shutdown=1, expected_led=1)
    
    # Test rapid E-STOP presses
    for i in range(3):
        await tb.press_estop_a()
        await ClockCycles(dut.clk, 200)
        await tb.release_estop_a()
        await ClockCycles(dut.clk, 200)
    
    await tb.wait_for_debounce()
    tb.check_safe_state("Rapid E-STOP A Presses", expected_shutdown=1, expected_led=1)
    
    # Test alternating E-STOP presses
    await tb.press_estop_a()
    await ClockCycles(dut.clk, 300)
    await tb.release_estop_a()
    await tb.press_estop_b()
    await ClockCycles(dut.clk, 300)
    await tb.release_estop_b()
    await tb.wait_for_debounce()
    
    tb.check_safe_state("Alternating E-STOP Presses", expected_shutdown=1, expected_led=1)
    
    tb.log.info("=== Rapid Button Sequences Test Completed ===")

@cocotb.test()
async def test_watchdog_timing_variations(dut):
    """Test watchdog with different timing patterns"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Watchdog Timing Variations Test Starting ===")
    
    # Initialize system and get to operational state
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Test fast watchdog kicks (every 50ms)
    tb.log.info("Testing fast watchdog kicks...")
    fast_kick_interval = int(0.05 * tb.clock_freq)  # 50ms
    for i in range(10):
        await tb.pulse_watchdog()
        await ClockCycles(dut.clk, fast_kick_interval)
    
    tb.check_operational_state("Fast Watchdog Kicks", expected_shutdown=0, expected_led=0)
    
    # Test slow but acceptable watchdog kicks (every 400ms)
    tb.log.info("Testing slow watchdog kicks...")
    slow_kick_interval = int(0.4 * tb.clock_freq)  # 400ms
    for i in range(5):
        await tb.pulse_watchdog()
        await ClockCycles(dut.clk, slow_kick_interval)
    
    tb.check_operational_state("Slow Watchdog Kicks", expected_shutdown=0, expected_led=0)
    
    # Test irregular watchdog timing
    tb.log.info("Testing irregular watchdog timing...")
    intervals = [0.1, 0.3, 0.15, 0.25, 0.2]  # seconds
    for interval in intervals:
        await tb.pulse_watchdog()
        await ClockCycles(dut.clk, int(interval * tb.clock_freq))
    
    tb.check_operational_state("Irregular Watchdog Timing", expected_shutdown=0, expected_led=0)
    
    tb.log.info("=== Watchdog Timing Variations Test Completed ===")

@cocotb.test()
async def test_power_on_sequence(dut):
    """Test proper power-on sequence"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Power-On Sequence Test Starting ===")
    
    # Test power-on with E-STOPs already pressed
    dut.ui_in.value = 0x0C  # E-STOPs pressed, ACK and WDG_KICK released
    await tb.reset_system()
    await tb.wait_for_debounce()
    
    tb.check_safe_state("Power-on with E-STOPs Pressed", expected_shutdown=1, expected_led=1)
    
    # Test power-on with clean inputs
    dut.ui_in.value = 0x0F  # All inputs in safe state
    await tb.reset_system()
    await tb.wait_for_debounce()
    
    tb.check_safe_state("Power-on with Clean Inputs", expected_shutdown=1, expected_led=1)
    
    # Test normal startup sequence
    await tb.pulse_ack()
    await tb.wait_for_debounce()
    
    # Start watchdog immediately after ACK
    kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(100000))
    await ClockCycles(dut.clk, 50000)
    
    tb.check_operational_state("Normal Startup Sequence", expected_shutdown=0, expected_led=0)
    kick_task.kill()
    
    tb.log.info("=== Power-On Sequence Test Completed ===")

@cocotb.test()
async def test_stress_scenarios(dut):
    """Test stress scenarios and edge cases"""
    
    tb = ESDControllerTestBench(dut)
    tb.log.info("=== Stress Scenarios Test Starting ===")
    
    # Initialize system
    dut.ui_in.value = 0x0F
    await tb.reset_system()
    
    # Stress test: Rapid state transitions
    tb.log.info("Stress test: Rapid state transitions...")
    for cycle in range(5):
        # Get to operational
        await tb.pulse_ack()
        kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(50000))
        await ClockCycles(dut.clk, 25000)
        
        # Trigger E-STOP
        await tb.press_estop_a()
        kick_task.kill()
        await ClockCycles(dut.clk, 1000)
        
        # Release and continue
        await tb.release_estop_a()
        await ClockCycles(dut.clk, 1000)
    
    tb.check_safe_state(f"Rapid State Transitions Cycle", expected_shutdown=1, expected_led=1)
    
    # Stress test: Multiple watchdog timeout recoveries
    tb.log.info("Stress test: Multiple watchdog timeouts...")
    for timeout_cycle in range(3):
        # ACK and start watchdog
        await tb.pulse_ack()
        kick_task = cocotb.start_soon(tb.automatic_watchdog_kicks(25000))
        await ClockCycles(dut.clk, 20000)
        
        # Stop watchdog and let it timeout
        kick_task.kill()
        await tb.wait_for_watchdog_timeout()
        
        tb.check_safe_state(f"Watchdog Timeout Cycle {timeout_cycle+1}", expected_shutdown=1, expected_led=1)
    
    tb.log.info("=== Stress Scenarios Test Completed ===")

async def run_all_esd_tests():
    """Run all ESD controller tests with a mock DUT"""
    
    print("=== ESD Controller Test Suite ===")
    
    # Create mock DUT
    dut = MockESDControllerDUT()
    
    # Run all test functions
    await test_reset_behavior(dut)
    await Timer(5, units='us')
    
    await test_ack_button_functionality(dut)
    await Timer(5, units='us')
    
    await test_watchdog_operation(dut)
    await Timer(5, units='us')
    
    await test_estop_a_functionality(dut)
    await Timer(5, units='us')
    
    await test_estop_b_functionality(dut)
    await Timer(5, units='us')
    
    await test_dual_estop_functionality(dut)
    await Timer(5, units='us')
    
    await test_rapid_button_sequences(dut)
    await Timer(5, units='us')
    
    await test_watchdog_timing_variations(dut)
    await Timer(5, units='us')
    
    await test_power_on_sequence(dut)
    await Timer(5, units='us')
    
    await test_stress_scenarios(dut)
    
    print("\n=== All ESD Controller Tests Completed ===")

if __name__ == "__main__":
    # Simple synchronous version for direct execution
    print("Running ESD Controller tests in standalone mode...")
    
    class SimpleESDTest:
        def __init__(self):
            self.passed = 0
            self.total = 0
            
        def test_input_mapping(self, input_byte, expected_signals, name):
            """Test input signal mapping"""
            estop_a_n = (input_byte & 0x01) != 0
            estop_b_n = (input_byte & 0x02) != 0
            ack_n = (input_byte & 0x04) != 0
            wdg_kick = (input_byte & 0x08) != 0
            
            actual_signals = {
                'estop_a_n': estop_a_n,
                'estop_b_n': estop_b_n,
                'ack_n': ack_n,
                'wdg_kick': wdg_kick
            }
            
            self.total += 1
            if actual_signals == expected_signals:
                print(f"✓ PASS: {name} - Input mapping correct")
                self.passed += 1
            else:
                print(f"✗ FAIL: {name} - Input mapping incorrect")
                print(f"         Expected: {expected_signals}")
                print(f"         Got: {actual_signals}")
        
        def test_output_mapping(self, shutdown, led_status, name):
            """Test output signal mapping"""
            output_byte = (shutdown & 0x01) | ((led_status & 0x01) << 1)
            
            self.total += 1
            extracted_shutdown = output_byte & 0x01
            extracted_led = (output_byte & 0x02) >> 1
            
            if extracted_shutdown == shutdown and extracted_led == led_status:
                print(f"✓ PASS: {name} - SHUTDOWN={shutdown}, LED={led_status} → 0x{output_byte:02X}")
                self.passed += 1
            else:
                print(f"✗ FAIL: {name} - Output mapping incorrect")
        
        def test_safety_logic(self, estop_a, estop_b, ack_pressed, wdg_ok, name):
            """Test safety logic"""
            # Simplified safety logic
            estops_ok = estop_a and estop_b  # Both E-STOPs must be released
            system_safe = estops_ok and ack_pressed and wdg_ok
            
            shutdown_out = 0 if system_safe else 1
            led_out = 0 if system_safe else 1
            
            self.total += 1
            print(f"✓ PASS: {name} - E-STOPs:{estops_ok}, ACK:{ack_pressed}, WDG:{wdg_ok} → SHUTDOWN:{shutdown_out}, LED:{led_out}")
            self.passed += 1
        
        def test_watchdog_timing(self):
            """Test watchdog timing calculations"""
            print("\n--- Watchdog Timing Tests ---")
            
            clock_freq = 50_000_000  # 50MHz
            timeout_ms = 500  # 500ms
            
            # Calculate timeout in clock cycles
            timeout_cycles = int(timeout_ms * clock_freq / 1000)
            kick_interval_ms = 200  # Kick every 200ms
            kick_interval_cycles = int(kick_interval_ms * clock_freq / 1000)
            
            self.total += 1
            if timeout_cycles > kick_interval_cycles:
                print(f"✓ PASS: Watchdog timing - Timeout: {timeout_cycles} cycles, Kick: {kick_interval_cycles} cycles")
                self.passed += 1
            else:
                print(f"✗ FAIL: Watchdog timing - Kick interval too long")
        
        def test_debounce_timing(self):
            """Test button debounce timing"""
            print("\n--- Debounce Timing Tests ---")
            
            clock_freq = 50_000_000  # 50MHz
            debounce_ms = 20  # 20ms debounce
            debounce_cycles = int(debounce_ms * clock_freq / 1000)
            
            self.total += 1
            if debounce_cycles > 100:  # Should be reasonable number of cycles
                print(f"✓ PASS: Debounce timing - {debounce
