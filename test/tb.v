`timescale 1ns / 1ps

module tb;
    // Timing parameters - makes testbench more maintainable
    parameter CLK_PERIOD = 20;          // 20ns = 50MHz
    parameter CLK_FREQ_HZ = 50_000_000; // 50MHz
    parameter DEBOUNCE_CYCLES = 1000;   // Debounce wait time
    parameter WDG_KICK_INTERVAL_MS = 200; // Watchdog kick every 200ms
    parameter WDG_TIMEOUT_MS = 500;     // Watchdog timeout at 500ms
    parameter STARTUP_CYCLES = 100;     // Startup delay cycles
    
    // Calculated timing values
    parameter WDG_KICK_CYCLES = (WDG_KICK_INTERVAL_MS * CLK_FREQ_HZ) / 1000;
    parameter WDG_TIMEOUT_CYCLES = (WDG_TIMEOUT_MS * CLK_FREQ_HZ) / 1000;
    
    // Clock and reset
    reg clk = 0;
    reg rst_n = 0;
    
    // TinyTapeout interface signals
    reg [7:0] ui_in = 8'h00;    // Dedicated inputs
    wire [7:0] uo_out;          // Dedicated outputs  
    reg [7:0] uio_in = 8'h00;   // IOs: Input path
    wire [7:0] uio_out;         // IOs: Output path
    wire [7:0] uio_oe;          // IOs: Enable path
    reg ena = 1'b1;             // Always 1 when design is powered
    
    // Individual input signals for clarity
    reg estop_a_n = 1'b1;       // E-STOP A (active-low)
    reg estop_b_n = 1'b1;       // E-STOP B (active-low)
    reg ack_n = 1'b1;           // ACK button (active-low)
    reg wdg_kick = 1'b0;        // Watchdog kick
    
    // Output signals for monitoring
    wire shutdown_out;
    wire led_status;
    
    // Watchdog control
    reg wdg_enable = 0;         // Enable automatic watchdog kicking
    
    // Test control
    integer test_number = 0;
    integer pass_count = 0;
    integer fail_count = 0;
    
    // Assign inputs to ui_in bus
    always @(*) begin
        ui_in[0] = estop_a_n;
        ui_in[1] = estop_b_n;
        ui_in[2] = ack_n;
        ui_in[3] = wdg_kick;
        ui_in[7:4] = 4'b0000;   // Unused inputs
    end
    
    // Extract outputs from uo_out bus
    assign shutdown_out = uo_out[0];
    assign led_status = uo_out[1];
    
    // Instantiate the Device Under Test (DUT)
    tt_um_example dut (
        .ui_in(ui_in),
        .uo_out(uo_out),
        .uio_in(uio_in),
        .uio_out(uio_out),
        .uio_oe(uio_oe),
        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );
    
    // Clock generation
    always #(CLK_PERIOD/2) clk = ~clk;
    
    // Background watchdog kicking process
    initial begin
        forever begin
            if (wdg_enable) begin
                wdg_kick = 1'b1;
                #(CLK_PERIOD * 2);
                wdg_kick = 1'b0;
                wait_cycles(WDG_KICK_CYCLES - 2);
            end else begin
                wait_cycles(100); // Small delay when disabled
            end
        end
    end
    
    // Task to wait for clock cycles
    task wait_cycles;
        input integer cycles;
        integer i;
        begin
            for (i = 0; i < cycles; i = i + 1) begin
                @(posedge clk);
            end
        end
    endtask
    
    // Task to wait for time in milliseconds
    task wait_ms;
        input integer ms;
        begin
            wait_cycles((ms * CLK_FREQ_HZ) / 1000);
        end
    endtask
    
    // Task to pulse ACK button
    task pulse_ack;
        begin
            $display("[%0t] Pulsing ACK button", $time);
            ack_n = 1'b0;
            wait_cycles(10);
            ack_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask
    
    // Task to press E-STOP A
    task press_estop_a;
        begin
            $display("[%0t] Pressing E-STOP A", $time);
            estop_a_n = 1'b0;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask
    
    // Task to release E-STOP A  
    task release_estop_a;
        begin
            $display("[%0t] Releasing E-STOP A", $time);
            estop_a_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask
    
    // Task to press E-STOP B
    task press_estop_b;
        begin
            $display("[%0t] Pressing E-STOP B", $time);
            estop_b_n = 1'b0;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask
    
    // Task to release E-STOP B
    task release_estop_b;
        begin
            $display("[%0t] Releasing E-STOP B", $time);
            estop_b_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask
    
    // Task to start watchdog kicking
    task start_watchdog;
        begin
            $display("[%0t] Starting automatic watchdog kicks", $time);
            wdg_enable = 1;
        end
    endtask
    
    // Task to stop watchdog kicking
    task stop_watchdog;
        begin
            $display("[%0t] Stopping automatic watchdog kicks", $time);
            wdg_enable = 0;
        end
    endtask
    
    // Task for test assertions
    task check_outputs;
        input expected_shutdown;
        input expected_led;
        input [255:0] test_name;
        begin
            if (shutdown_out === expected_shutdown && led_status === expected_led) begin
                $display("✓ PASS: %s - SHUTDOWN=%b, LED=%b", test_name, shutdown_out, led_status);
                pass_count = pass_count + 1;
            end else begin
                $display("✗ FAIL: %s - Expected SHUTDOWN=%b, LED=%b, Got SHUTDOWN=%b, LED=%b", 
                        test_name, expected_shutdown, expected_led, shutdown_out, led_status);
                fail_count = fail_count + 1;
            end
        end
    endtask
    
    // Task to print test header
    task test_header;
        input [255:0] test_name;
        begin
            test_number = test_number + 1;
            $display("\n=== Test %0d: %s ===", test_number, test_name);
        end
    endtask
    
    // Monitor outputs for debugging
    reg prev_shutdown = 1'bx;
    reg prev_led = 1'bx;
    
    always @(posedge clk) begin
        if ($time > 1000 && rst_n) begin // Skip initial transients and reset
            if (shutdown_out !== prev_shutdown) begin
                $display("[%0t] SHUTDOWN changed to %b", $time, shutdown_out);
                prev_shutdown = shutdown_out;
            end
            if (led_status !== prev_led) begin
                $display("[%0t] LED_STATUS changed to %b", $time, led_status);
                prev_led = led_status;
            end
        end
    end
    
    // Main test sequence
    initial begin
        $display("=== ESD Controller Testbench Starting ===");
        $display("Clock Frequency: %0d Hz", CLK_FREQ_HZ);
        $display("Watchdog Kick Interval: %0d ms (%0d cycles)", WDG_KICK_INTERVAL_MS, WDG_KICK_CYCLES);
        $display("Watchdog Timeout: %0d ms (%0d cycles)", WDG_TIMEOUT_MS, WDG_TIMEOUT_CYCLES);
        
        $dumpfile("sim_build/rtl/tb.vcd");
        $dumpvars(0, tb);
        
        // Initialize all signals
        estop_a_n = 1'b1;
        estop_b_n = 1'b1;
        ack_n = 1'b1;
        wdg_kick = 1'b0;
        wdg_enable = 0;
        
        // Test 1: Reset behavior
        test_header("Reset Behavior");
        rst_n = 1'b0;
        wait_cycles(STARTUP_CYCLES);
        rst_n = 1'b1;
        wait_cycles(STARTUP_CYCLES);
        
        // Check safe startup state (should be in shutdown mode)
        check_outputs(1'b1, 1'b1, "Safe startup state");
        
        // Test 2: ACK button without releasing E-STOPs
        test_header("ACK Button Without E-STOP Release");
        pulse_ack();
        
        // System should remain in shutdown (E-STOPs still considered active)
        check_outputs(1'b1, 1'b1, "System remains in shutdown after ACK only");
        
        // Test 3: Transition to normal operation
        test_header("Transition to Normal Operation");
        start_watchdog();
        wait_ms(600); // Wait longer than one watchdog cycle
        
        // System should now be in normal operation
        check_outputs(1'b0, 1'b0, "Normal operation mode");
        
        // Test 4: E-STOP A functionality
        test_header("E-STOP A Functionality");
        press_estop_a();
        
        // Should trigger shutdown immediately
        check_outputs(1'b1, 1'b1, "E-STOP A triggered shutdown");
        
        // Recovery from E-STOP A
        release_estop_a();
        pulse_ack();
        wait_ms(600); // Wait for system to stabilize
        
        check_outputs(1'b0, 1'b0, "Recovery from E-STOP A");
        
        // Test 5: E-STOP B functionality  
        test_header("E-STOP B Functionality");
        press_estop_b();
        
        // Should trigger shutdown immediately
        check_outputs(1'b1, 1'b1, "E-STOP B triggered shutdown");
        
        // Recovery from E-STOP B
        release_estop_b();
        pulse_ack();
        wait_ms(600); // Wait for system to stabilize
        
        check_outputs(1'b0, 1'b0, "Recovery from E-STOP B");
        
        // Test 6: Dual E-STOP functionality
        test_header("Dual E-STOP Functionality");
        press_estop_a();
        wait_cycles(100);
        press_estop_b();
        
        check_outputs(1'b1, 1'b1, "Both E-STOPs pressed");
        
        // Release one E-STOP - should still be in shutdown
        release_estop_a();
        pulse_ack();
        wait_cycles(DEBOUNCE_CYCLES);
        
        check_outputs(1'b1, 1'b1, "One E-STOP still pressed");
        
        // Release second E-STOP and recover
        release_estop_b();
        pulse_ack();
        wait_ms(600);
        
        check_outputs(1'b0, 1'b0, "Recovery from dual E-STOP");
        
        // Test 7: Watchdog timeout
        test_header("Watchdog Timeout");
        stop_watchdog();
        wait_ms(WDG_TIMEOUT_MS + 100); // Wait longer than timeout
        
        check_outputs(1'b1, 1'b1, "Watchdog timeout triggered shutdown");
        
        // Recovery from watchdog timeout
        pulse_ack();
        start_watchdog();
        wait_ms(600);
        
        check_outputs(1'b0, 1'b0, "Recovery from watchdog timeout");
        
        // Test 8: Multiple rapid E-STOP presses
        test_header("Rapid E-STOP Operations");
        press_estop_a();
        wait_cycles(50);
        release_estop_a();
        wait_cycles(50);
        press_estop_b();
        wait_cycles(50);
        release_estop_b();
        
        check_outputs(1'b1, 1'b1, "Rapid E-STOP operations");
        
        pulse_ack();
        wait_ms(600);
        
        check_outputs(1'b0, 1'b0, "Recovery from rapid E-STOP operations");
        
        // Clean shutdown
        stop_watchdog();
        wait_cycles(1000);
        
        // Test summary
        $display("\n=== Test Summary ===");
        $display("Total Tests: %0d", pass_count + fail_count);
        $display("Passed: %0d", pass_count);
        $display("Failed: %0d", fail_count);
        
        if (fail_count == 0) begin
            $display("🎉 ALL TESTS PASSED! 🎉");
        end else begin
            $display("❌ %0d TESTS FAILED", fail_count);
        end
        
        $display("\n=== ESD Controller Testbench Complete ===");
        wait_cycles(100);
        $finish;
    end
    
    // Simulation timeout watchdog
    initial begin
        #100_000_000; // 100ms timeout
        $display("ERROR: Simulation timeout!");
        $finish;
    end
    
endmodule
