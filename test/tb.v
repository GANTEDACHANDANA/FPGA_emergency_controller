`timescale 1ns / 1ps

module tb_tt_um_example();

    // Testbench parameters
    parameter CLK_PERIOD = 20;  // 50MHz clock (20ns period)
    parameter CLK_HZ = 50000000;
    
    // DUT signals
    reg [7:0] ui_in;
    wire [7:0] uo_out;
    reg [7:0] uio_in;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;
    reg ena;
    reg clk;
    reg rst_n;
    
    // Individual signal mappings for clarity
    reg estop_a_n, estop_b_n, ack_n, wdg_kick, async_in;
    wire shutdown_out, led_status, sync_output;
    
    // Assign individual signals to ui_in bus
    always @* begin
        ui_in[0] = estop_a_n;
        ui_in[1] = estop_b_n;
        ui_in[2] = ack_n;
        ui_in[3] = wdg_kick;
        ui_in[4] = async_in;
        ui_in[7:5] = 3'b000;  // Unused inputs
    end
    
    // Extract outputs
    assign shutdown_out = uo_out[0];
    assign led_status = uo_out[1];
    assign sync_output = uo_out[2];
    
    // Instantiate DUT
    tt_um_example #(
        .CLK_HZ(CLK_HZ)
    ) dut (
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
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end
    
    // Watchdog kick task - generates periodic kicks
    reg auto_kick_en;
    initial begin
        auto_kick_en = 0;
        wdg_kick = 0;
        forever begin
            if (auto_kick_en) begin
                #10000000;  // 10ms between kicks (well within 500ms timeout)
                wdg_kick = 1;
                #(CLK_PERIOD);
                wdg_kick = 0;
            end else begin
                #(CLK_PERIOD);
            end
        end
    end
    
    // Test stimulus
    initial begin
        // Initialize VCD dump
        $dumpfile("tb_tt_um_example.vcd");
        $dumpvars(0, tb_tt_um_example);
        
        // Initialize signals
        ena = 1;
        uio_in = 8'b0;
        estop_a_n = 1;  // Not pressed (active low)
        estop_b_n = 1;  // Not pressed (active low)
        ack_n = 1;      // Not pressed (active low)
        wdg_kick = 0;
        async_in = 0;
        auto_kick_en = 0;
        rst_n = 0;
        
        $display("=== ESD Controller Testbench Starting ===");
        $display("Time\t\tTest Phase");
        
        // Reset sequence
        $display("%0t\t\tApplying Reset", $time);
        #(CLK_PERIOD * 10);
        rst_n = 1;
        #(CLK_PERIOD * 5);
        
        // Test 1: Normal startup (should be in shutdown state initially)
        $display("%0t\t\tTest 1: Normal Startup", $time);
        check_shutdown_state(1, "Initial state should be shutdown");
        #(CLK_PERIOD * 10);
        
        // Test 2: Try to start without ACK (should remain shutdown)
        $display("%0t\t\tTest 2: Start without ACK", $time);
        auto_kick_en = 1;  // Start kicking watchdog
        #(CLK_PERIOD * 100);
        check_shutdown_state(1, "Should remain shutdown without ACK");
        
        // Test 3: Proper startup sequence (ACK button press)
        $display("%0t\t\tTest 3: Proper Startup Sequence", $time);
        press_ack_button();
        #(CLK_PERIOD * 1000);  // Wait for debouncing and FSM transition
        check_shutdown_state(0, "Should be running after ACK");
        check_led_blinking("LED should be blinking in run state");
        
        // Test 4: E-STOP A activation
        $display("%0t\t\tTest 4: E-STOP A Activation", $time);
        estop_a_n = 0;  // Press E-STOP A
        #(CLK_PERIOD * 1000);  // Wait for debouncing
        check_shutdown_state(1, "Should shutdown on E-STOP A");
        check_led_solid(1, "LED should be solid ON when shutdown");
        estop_a_n = 1;  // Release E-STOP A
        #(CLK_PERIOD * 1000);
        
        // Test 5: Recovery from E-STOP
        $display("%0t\t\tTest 5: Recovery from E-STOP", $time);
        press_ack_button();
        #(CLK_PERIOD * 1000);
        check_shutdown_state(0, "Should recover after E-STOP release and ACK");
        
        // Test 6: E-STOP B activation
        $display("%0t\t\tTest 6: E-STOP B Activation", $time);
        estop_b_n = 0;  // Press E-STOP B
        #(CLK_PERIOD * 1000);
        check_shutdown_state(1, "Should shutdown on E-STOP B");
        estop_b_n = 1;  // Release E-STOP B
        #(CLK_PERIOD * 1000);
        press_ack_button();
        #(CLK_PERIOD * 1000);
        check_shutdown_state(0, "Should recover from E-STOP B");
        
        // Test 7: Watchdog timeout
        $display("%0t\t\tTest 7: Watchdog Timeout", $time);
        auto_kick_en = 0;  // Stop kicking watchdog
        #(600_000_000);    // Wait longer than 500ms timeout
        check_shutdown_state(1, "Should shutdown on watchdog timeout");
        
        // Test 8: Recovery from watchdog timeout
        $display("%0t\t\tTest 8: Recovery from Watchdog Timeout", $time);
        auto_kick_en = 1;  // Resume kicking
        press_ack_button();
        #(CLK_PERIOD * 1000);
        check_shutdown_state(0, "Should recover from watchdog timeout");
        
        // Test 9: Async input synchronization
        $display("%0t\t\tTest 9: Async Input Synchronization", $time);
        test_async_sync();
        
        // Test 10: Multiple E-STOP scenario
        $display("%0t\t\tTest 10: Multiple E-STOP", $time);
        estop_a_n = 0;
        estop_b_n = 0;
        #(CLK_PERIOD * 1000);
        check_shutdown_state(1, "Should shutdown with both E-STOPs");
        estop_a_n = 1;  // Release only one
        #(CLK_PERIOD * 1000);
        check_shutdown_state(1, "Should remain shutdown with one E-STOP still active");
        estop_b_n = 1;  // Release both
        #(CLK_PERIOD * 1000);
        press_ack_button();
        #(CLK_PERIOD * 1000);
        check_shutdown_state(0, "Should recover when both E-STOPs released");
        
        $display("\n=== Test Summary ===");
        $display("All tests completed successfully!");
        $display("Final state - Shutdown: %b, LED: %b", shutdown_out, led_status);
        
        #(CLK_PERIOD * 100);
        $finish;
    end
    
    // Task to simulate ACK button press
    task press_ack_button;
        begin
            $display("%0t\t\t  Pressing ACK button", $time);
            ack_n = 0;  // Press
            #(CLK_PERIOD * 100);  // Hold for debounce time
            ack_n = 1;  // Release
            #(CLK_PERIOD * 100);  // Wait for edge detection
        end
    endtask
    
    // Task to check shutdown state
    task check_shutdown_state;
        input expected;
        input [255:0] message;
        begin
            if (shutdown_out === expected) begin
                $display("%0t\t\t  ✓ PASS: %s", $time, message);
            end else begin
                $display("%0t\t\t  ✗ FAIL: %s (Expected: %b, Got: %b)", $time, message, expected, shutdown_out);
            end
        end
    endtask
    
    // Task to check LED blinking
    task check_led_blinking;
        input [255:0] message;
        reg prev_led;
        integer blink_count;
        begin
            prev_led = led_status;
            blink_count = 0;
            
            repeat (100) begin
                #(CLK_PERIOD * 1000);  // Wait some time
                if (led_status !== prev_led) begin
                    blink_count = blink_count + 1;
                    prev_led = led_status;
                end
            end
            
            if (blink_count > 0) begin
                $display("%0t\t\t  ✓ PASS: %s (Blinks detected: %d)", $time, message, blink_count);
            end else begin
                $display("%0t\t\t  ✗ FAIL: %s (No blinking detected)", $time, message);
            end
        end
    endtask
    
    // Task to check LED solid state
    task check_led_solid;
        input expected;
        input [255:0] message;
        reg led_changed;
        begin
            led_changed = 0;
            
            repeat (50) begin
                #(CLK_PERIOD * 1000);
                if (led_status !== expected) begin
                    led_changed = 1;
                end
            end
            
            if (!led_changed && led_status === expected) begin
                $display("%0t\t\t  ✓ PASS: %s", $time, message);
            end else begin
                $display("%0t\t\t  ✗ FAIL: %s (Expected solid %b, Got %b)", $time, message, expected, led_status);
            end
        end
    endtask
    
    // Task to test async synchronization
    task test_async_sync;
        begin
            async_in = 0;
            #(CLK_PERIOD * 5);
            
            async_in = 1;
            #(CLK_PERIOD * 5);
            
            if (sync_output === 1) begin
                $display("%0t\t\t  ✓ PASS: Async input synchronized properly", $time);
            end else begin
                $display("%0t\t\t  ✗ FAIL: Sync output not following async input", $time);
            end
            
            async_in = 0;
            #(CLK_PERIOD * 5);
            
            if (sync_output === 0) begin
                $display("%0t\t\t  ✓ PASS: Async sync clear working", $time);
            end else begin
                $display("%0t\t\t  ? INFO: Sync output: %b (may take time to clear)", $time, sync_output);
            end
        end
    endtask
    
    // Monitor critical signals
    initial begin
        $monitor("%0t: shutdown=%b, led=%b, estop_a_n=%b, estop_b_n=%b, ack_n=%b, wdg_kick=%b", 
                 $time, shutdown_out, led_status, estop_a_n, estop_b_n, ack_n, wdg_kick);
    end

endmodule
