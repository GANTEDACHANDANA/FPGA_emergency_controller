`timescale 1ns / 1ps
`default_nettype none

module tb;
    // Timing parameters
    parameter CLK_PERIOD = 20;          // 20ns = 50MHz
    parameter CLK_FREQ_HZ = 50_000_000; // 50MHz
    parameter DEBOUNCE_CYCLES = 100;
    parameter WDG_KICK_INTERVAL_MS = 10;
    parameter WDG_TIMEOUT_MS = 50;
    parameter STARTUP_CYCLES = 50;

    // Calculated timing values
    parameter WDG_KICK_CYCLES = (WDG_KICK_INTERVAL_MS * CLK_FREQ_HZ) / 1000;
    parameter WDG_TIMEOUT_CYCLES = (WDG_TIMEOUT_MS * CLK_FREQ_HZ) / 1000;

    // Clock and reset
    reg clk = 0;
    reg rst_n = 0;

    // TinyTapeout interface signals
    reg [7:0] ui_in = 8'h00;
    wire [7:0] uo_out;
    reg [7:0] uio_in = 8'h00;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;
    reg ena = 1'b1;

    // Individual input signals
    reg estop_a_n = 1'b1;
    reg estop_b_n = 1'b1;
    reg ack_n = 1'b1;
    reg wdg_kick = 1'b0;

    // Output monitoring
    wire shutdown_out = uo_out[0];
    wire led_status = uo_out[1];

    reg manual_wdg_mode = 1;
    integer test_number = 0;
    integer pass_count = 0;
    integer fail_count = 0;

    // Assign inputs to ui_in
    always @(*) begin
        ui_in[0] = estop_a_n;
        ui_in[1] = estop_b_n;
        ui_in[2] = ack_n;
        ui_in[3] = wdg_kick;
        ui_in[7:4] = 4'b0000;
    end

    // Instantiate DUT
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
    always #(CLK_PERIOD / 2) clk = ~clk;

    // Tasks
    task wait_cycles(input integer cycles);
        integer i;
        begin
            for (i = 0; i < cycles; i = i + 1) @(posedge clk);
        end
    endtask

    task wait_ms(input integer ms);
        integer cycles;
        begin
            cycles = (ms * 1000);
            wait_cycles(cycles);
        end
    endtask

    task pulse_ack;
        begin
            $display("[%0t] Pulsing ACK button", $time);
            ack_n = 1'b0;
            wait_cycles(5);
            ack_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask

    task kick_watchdog;
        begin
            wdg_kick = 1'b1;
            wait_cycles(2);
            wdg_kick = 1'b0;
            wait_cycles(2);
        end
    endtask

    task kick_watchdog_times(input integer count);
        integer i;
        begin
            for (i = 0; i < count; i = i + 1) begin
                kick_watchdog();
                wait_cycles(100);
            end
        end
    endtask

    task press_estop_a;
        begin
            $display("[%0t] Pressing E-STOP A", $time);
            estop_a_n = 1'b0;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask

    task release_estop_a;
        begin
            $display("[%0t] Releasing E-STOP A", $time);
            estop_a_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask

    task press_estop_b;
        begin
            $display("[%0t] Pressing E-STOP B", $time);
            estop_b_n = 1'b0;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask

    task release_estop_b;
        begin
            $display("[%0t] Releasing E-STOP B", $time);
            estop_b_n = 1'b1;
            wait_cycles(DEBOUNCE_CYCLES);
        end
    endtask

    task check_outputs(input expected_shutdown, input expected_led, input [255:0] test_name);
        begin
            if (shutdown_out === expected_shutdown && led_status === expected_led) begin
                $display("✓ PASS: %s - SHUTDOWN=%b, LED=%b", test_name, shutdown_out, led_status);
                pass_count = pass_count + 1;
