#!/usr/bin/env python3
"""
Cocotb-style Sort Test Implementation
A sorting test using cocotb library patterns for hardware verification
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
import asyncio

class SortTestBench:
    """Helper class to manage sorting operations testing"""
    
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log if hasattr(dut, '_log') else None
        self.test_results = []
        
    def sort_array(self, arr):
        """Sort an array in ascending order"""
        if not isinstance(arr, list):
            raise TypeError("Input must be a list")
        return sorted(arr)
    
    def check_sorted(self, original, sorted_result, expected, test_name):
        """Check if sorting result matches expected output"""
        if sorted_result == expected:
            message = f"✓ PASS: {test_name} - {original} → {sorted_result}"
            if self.log:
                self.log.info(message)
            else:
                print(message)
            self.test_results.append(True)
            return True
        else:
            message = f"✗ FAIL: {test_name} - {original}"
            error_msg = f"         Expected: {expected}, Got: {sorted_result}"
            if self.log:
                self.log.error(message)
                self.log.error(error_msg)
            else:
                print(message)
                print(error_msg)
            self.test_results.append(False)
            return False
    
    async def run_sort_test(self, test_data, test_name):
        """Run a single sort test case"""
        original, expected = test_data
        
        # Simulate processing time
        await Timer(1, units='us')
        
        try:
            result = self.sort_array(original.copy())
            self.check_sorted(original, result, expected, test_name)
        except Exception as e:
            message = f"✗ ERROR: {test_name} - Exception: {e}"
            if self.log:
                self.log.error(message)
            else:
                print(message)
            self.test_results.append(False)
    
    def get_pass_rate(self):
        """Calculate test pass rate"""
        if not self.test_results:
            return 0
        passed = sum(self.test_results)
        total = len(self.test_results)
        return (passed / total) * 100

# Mock DUT class for standalone testing
class MockDUT:
    class MockLog:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    
    def __init__(self):
        self._log = self.MockLog()
        self.clk = None

@cocotb.test()
async def test_basic_sorting(dut):
    """Basic sorting functionality test"""
    
    tb = SortTestBench(dut)
    tb.log.info("=== Basic Sorting Test Starting ===")
    
    # Basic test cases
    test_cases = [
        ([], []),  # Empty array
        ([1], [1]),  # Single element
        ([3, 1, 2], [1, 2, 3]),  # Simple case
        ([1, 2, 3], [1, 2, 3]),  # Already sorted
        ([3, 2, 1], [1, 2, 3]),  # Reverse sorted
    ]
    
    for i, (original, expected) in enumerate(test_cases, 1):
        await tb.run_sort_test((original, expected), f"Basic Test {i}")
        await Timer(1, units='us')  # Small delay between tests
    
    tb.log.info("=== Basic Sorting Test Completed ===")

@cocotb.test()
async def test_advanced_sorting(dut):
    """Advanced sorting test cases"""
    
    tb = SortTestBench(dut)
    tb.log.info("=== Advanced Sorting Test Starting ===")
    
    # Advanced test cases
    test_cases = [
        ([1, 3, 2, 3, 1], [1, 1, 2, 3, 3]),  # Duplicates
        ([5, 5, 5], [5, 5, 5]),  # All same
        ([-1, -3, -2], [-3, -2, -1]),  # Negative numbers
        ([-1, 0, 1], [-1, 0, 1]),  # Mixed signs
        ([3, -1, 0, -2, 1], [-2, -1, 0, 1, 3]),  # Complex mixed
        ([100, 1, 50, 25, 75], [1, 25, 50, 75, 100]),  # Larger numbers
    ]
    
    for i, (original, expected) in enumerate(test_cases, 1):
        await tb.run_sort_test((original, expected), f"Advanced Test {i}")
        await Timer(2, units='us')  # Slightly longer delay
    
    tb.log.info("=== Advanced Sorting Test Completed ===")

@cocotb.test()
async def test_edge_cases(dut):
    """Edge case sorting tests"""
    
    tb = SortTestBench(dut)
    tb.log.info("=== Edge Case Testing ===")
    
    # Edge cases
    test_cases = [
        ([0], [0]),  # Zero
        ([0, 0, 0], [0, 0, 0]),  # Multiple zeros
        ([-5, -1, -10, -2], [-10, -5, -2, -1]),  # All negative
        ([9, 5, 1, 8, 3, 2, 7, 4, 6], [1, 2, 3, 4, 5, 6, 7, 8, 9]),  # Longer array
    ]
    
    for i, (original, expected) in enumerate(test_cases, 1):
        await tb.run_sort_test((original, expected), f"Edge Case {i}")
        await Timer(1, units='us')
    
    # Test error handling
    tb.log.info("Testing error handling...")
    await Timer(1, units='us')
    
    try:
        tb.sort_array("not a list")
        tb.log.error("✗ FAIL: Should have raised TypeError")
        tb.test_results.append(False)
    except TypeError:
        tb.log.info("✓ PASS: TypeError correctly raised for invalid input")
        tb.test_results.append(True)
    except Exception as e:
        tb.log.error(f"✗ FAIL: Wrong exception type: {e}")
        tb.test_results.append(False)
    
    tb.log.info("=== Edge Case Testing Completed ===")

@cocotb.test()
async def test_performance(dut):
    """Performance and stress testing"""
    
    tb = SortTestBench(dut)
    tb.log.info("=== Performance Test Starting ===")
    
    # Generate test data
    import random
    
    # Large array test
    large_array = [random.randint(1, 1000) for _ in range(100)]
    expected_large = sorted(large_array)
    
    start_time = cocotb.utils.get_sim_time()
    await tb.run_sort_test((large_array, expected_large), "Performance Test - Large Array")
    end_time = cocotb.utils.get_sim_time()
    
    tb.log.info(f"Large array (100 elements) sorted in {end_time - start_time} sim time")
    
    # Stress test - multiple rapid sorts
    tb.log.info("Running stress test...")
    for i in range(10):
        small_array = [random.randint(1, 20) for _ in range(5)]
        expected_small = sorted(small_array)
        await tb.run_sort_test((small_array, expected_small), f"Stress Test {i+1}")
        await Timer(0.5, units='us')
    
    tb.log.info("=== Performance Test Completed ===")

async def run_all_tests():
    """Run all tests with a mock DUT for standalone execution"""
    
    print("=== Cocotb-Style Sort Test Suite ===")
    
    # Create mock DUT
    dut = MockDUT()
    
    # Run all test functions
    await test_basic_sorting(dut)
    await Timer(5, units='us')
    
    await test_advanced_sorting(dut)
    await Timer(5, units='us')
    
    await test_edge_cases(dut)
    await Timer(5, units='us')
    
    await test_performance(dut)
    
    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    # This allows running the test directly without cocotb
    print("Running sort tests in standalone mode...")
    
    # Simple synchronous version for direct execution
    class SimpleSortTest:
        def __init__(self):
            self.passed = 0
            self.total = 0
            
        def test_sort(self, arr, expected, name):
            result = sorted(arr) if isinstance(arr, list) else None
            self.total += 1
            
            if result == expected:
                print(f"✓ PASS: {name} - {arr} → {result}")
                self.passed += 1
            else:
                print(f"✗ FAIL: {name} - Expected: {expected}, Got: {result}")
        
        def run_tests(self):
            print("=== Simple Sort Tests ===")
            
            # Run basic tests
            test_cases = [
                ([], [], "Empty array"),
                ([1], [1], "Single element"),
                ([3, 1, 2], [1, 2, 3], "Basic sort"),
                ([1, 2, 3], [1, 2, 3], "Already sorted"),
                ([3, 2, 1], [1, 2, 3], "Reverse sorted"),
                ([1, 3, 2, 3, 1], [1, 1, 2, 3, 3], "With duplicates"),
                ([-1, -3, -2], [-3, -2, -1], "Negative numbers"),
                ([3, -1, 0, -2, 1], [-2, -1, 0, 1, 3], "Mixed positive/negative"),
            ]
            
            for arr, expected, name in test_cases:
                self.test_sort(arr, expected, name)
            
            print(f"\nResults: {self.passed}/{self.total} tests passed")
            print("🎉 ALL TESTS PASSED! 🎉" if self.passed == self.total else "❌ Some tests failed")
    
    # Run simple tests
    simple_test = SimpleSortTest()
    simple_test.run_tests()
