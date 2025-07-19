`timescale 1ns / 1ps

module tb;
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
    
    // Clock generation (50MHz)
    always #10 clk = ~clk;  // 20ns period = 50MHz
    
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
    
    // Task to pulse ACK button
    task pulse_ack;
        begin
            $display("[%0t] Pulsing ACK button", $time);
            ack_n = 1'b0;
            wait_cycles(10);
            ack_n = 1'b1;
            wait_cycles(10);
        end
    endtask
    
    // Task to pulse watchdog kick
    task pulse_wdg_kick;
        begin
            wdg_kick = 1'b1;
            wait_cycles(2);
            wdg_kick = 1'b0;
        end
    endtask
    
    // Task to press and hold E-STOP A
    task press_estop_a;
        begin
            $display("[%0t] Pressing E-STOP A", $time);
            estop_a_n = 1'b0;
        end
    endtask
    
    // Task to release E-STOP A  
    task release_estop_a;
        begin
            $display("[%0t] Releasing E-STOP A", $time);
            estop_a_n = 1'b1;
        end
    endtask
    
    // Task to press and hold E-STOP B
    task press_estop_b;
        begin
            $display("[%0t] Pressing E-STOP B", $time);
            estop_b_n = 1'b0;
        end
    endtask
    
    // Task to release E-STOP B
    task release_estop_b;
        begin
            $display("[%0t] Releasing E-STOP B", $time);
            estop_b_n = 1'b1;
        end
    endtask
    
    // Task to generate periodic watchdog kicks
    task automatic_wdg_kicks;
        input integer duration_ms;
        integer cycles_per_kick;
        integer total_cycles;
        integer i;
        begin
            cycles_per_kick = 10000000; // 200ms at 50MHz (kick every 200ms)
            total_cycles = duration_ms * 50000; // Convert ms to cycles
            
            for (i = 0; i < total_cycles; i = i + cycles_per_kick) begin
                pulse_wdg_kick();
                wait_cycles(cycles_per_kick - 2);
            end
        end
    endtask
    
    // Monitor outputs
    reg prev_shutdown = 1'bx;
    reg prev_led = 1'bx;
    
    always @(posedge clk) begin
        if ($time > 100) begin // Skip initial transients
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
    
    // Test sequence
    initial begin
        $display("=== ESD Controller Testbench Starting ===");
        $dumpfile("sim_build/rtl/tb.vcd");
        $dumpvars(0, tb);
        
        // Initialize signals
        estop_a_n = 1'b1;
        estop_b_n = 1'b1;
        ack_n = 1'b1;
        wdg_kick = 1'b0;
        
        // Test 1: Reset behavior
        $display("\n=== Test 1: Reset Behavior ===");
        rst_n = 1'b0;
        wait_cycles(100);
        rst_n = 1'b1;
        wait_cycles(100);
        
        // Check safe startup state
        if (shutdown_out == 1'b1 && led_status == 1'b1) begin
            $display("✓ PASS: Safe startup state - SHUTDOWN=1, LED=1");
        end else begin
            $display("✗ FAIL: Safe startup state - SHUTDOWN=%b, LED=%b", shutdown_out, led_status);
        end
        
        // Test 2: ACK button functionality
        $display("\n=== Test 2: ACK Button Functionality ===");
        pulse_ack();
        wait_cycles(1000); // Wait for debouncing
        
        if (shutdown_out == 1'b1) begin
            $display("✓ PASS: System remains in shutdown after ACK (E-STOPs not released)");
        end else begin
            $display("✗ FAIL: Unexpected shutdown state after ACK");
        end
        
        // Test 3: Normal operation with watchdog
        $display("\n=== Test 3: Normal Operation with Watchdog ===");
        // Start automatic watchdog kicking
        fork
            automatic_wdg_kicks(2000); // Kick for 2 seconds
        join_none
        
        wait_cycles(50000); // Wait a bit for system to stabilize
        
        // System should be in normal operation mode now
        if (shutdown_out == 1'b0) begin
            $display("✓ PASS: System in normal operation mode");
        end else begin
            $display("✗ FAIL: System not in normal operation mode");
        end
        
        // Test 4: E-STOP A functionality
        $display("\n=== Test 4: E-STOP A Functionality ===");
        press_estop_a();
        wait_cycles(1000); // Wait for debouncing
        
        if (shutdown_out == 1'b1 && led_status == 1'b1) begin
            $display("✓ PASS: E-STOP A triggered shutdown");
        end else begin
            $display("✗ FAIL: E-STOP A did not trigger shutdown properly");
        end
        
        // Release E-STOP A and ACK
        release_estop_a();
        wait_cycles(1000);
        pulse_ack();
        wait_cycles(1000);
        
        // Resume watchdog kicking
        fork
            automatic_wdg_kicks(1000); // Kick for 1 second
        join_none
        
        wait_cycles(50000);
        
        if (shutdown_out == 1'b0) begin
            $display("✓ PASS: Recovery from E-STOP A successful");
        end else begin
            $display("✗ FAIL: Recovery from E-STOP A failed");
        end
        
        // Test 5: E-STOP B functionality  
        $display("\n=== Test 5: E-STOP B Functionality ===");
        press_estop_b();
        wait_cycles(1000);
        
        if (shutdown_out == 1'b1 && led_status == 1'b1) begin
            $display("✓ PASS: E-STOP B triggered shutdown");
        end else begin
            $display("✗ FAIL: E-STOP B did not trigger shutdown properly");
        end
        
        // Release E-STOP B and ACK
        release_estop_b();
        wait_cycles(1000);
        pulse_ack();
        wait_cycles(1000);
        
        // Resume watchdog kicking
        fork
            automatic_wdg_kicks(1000); // Kick for 1 second  
        join_none
        
        wait_cycles(50000);
        
        if (shutdown_out == 1'b0) begin
            $display("✓ PASS: Recovery from E-STOP B successful");
        end else begin
            $display("✗ FAIL: Recovery from E-STOP B failed");
        end
        
        // Test 6: Watchdog timeout
        $display("\n=== Test 6: Watchdog Timeout ===");
        // Stop kicking watchdog
        wait_cycles(30000000); // Wait ~600ms (longer than 500ms timeout)
        
        if (shutdown_out == 1'b1 && led_status == 1'b1) begin
            $display("✓ PASS: Watchdog timeout triggered shutdown");
        end else begin
            $display("✗ FAIL: Watchdog timeout did not trigger shutdown");
        end
        
        // Recover from watchdog timeout
        pulse_ack();
        wait_cycles(1000);
        
        // Resume watchdog kicking
        fork
            automatic_wdg_kicks(1000); // Kick for 1 second
        join_none
        
        wait_cycles(50000);
        
        if (shutdown_out == 1'b0) begin
            $display("✓ PASS: Recovery from watchdog timeout successful");
        end else begin
            $display("✗ FAIL: Recovery from watchdog timeout failed");
        end
        
        $display("\n=== ESD Controller Testbench Complete ===");
        wait_cycles(1000);
        $finish;
    end
    
    // Timeout watchdog for simulation
    initial begin
        #100000000; // 100ms timeout for entire simulation
        $display("ERROR: Simulation timeout!");
        $finish;
    end
    
endmodule
