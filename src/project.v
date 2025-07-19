`timescale 1ns / 1ps

module debounce_button(
 input clk,
    input rst_n,
    input noisy_btn,
    output clean_btn
	 );
	 
   parameter CNT_WIDTH = 20;
    reg [CNT_WIDTH-1:0] count;
    reg btn_sync_0, btn_sync_1;
    reg btn_out;
	  always @(posedge clk) begin
        btn_sync_0 <= noisy_btn;
        btn_sync_1 <= btn_sync_0;
    end
	 always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count   <= 0;
            btn_out <= 0;
        end else if (btn_sync_1 == btn_out) begin
            count <= 0;
        end else begin
            count <= count + 1;
            if (count == {CNT_WIDTH{1'b1}})
                btn_out <= btn_sync_1;
        end
    end
	  assign clean_btn = btn_out;
	 
endmodule

module Rising_edge_detector(
	input  wire clk,
    input  wire sig_in,
    output wire rise_pulse
    );
	 reg d;

    always @(posedge clk) begin
        d <= sig_in;
    end
    assign rise_pulse = sig_in & ~d;
endmodule
module watchdogtimer(
input  wire clk,
    input  wire rst_n,
    input  wire kick,         // Rising edge resets the counter
    output reg  timeout

    );
	  parameter integer CLK_HZ     = 24000000;     // Clock frequency (default 24 MHz)
    parameter integer TIMEOUT_MS = 500;  
	 localparam integer CNT_MAX = (CLK_HZ / 1000) * TIMEOUT_MS;
	  localparam integer CNT_WIDTH = 25;
	  reg [CNT_WIDTH-1:0] cnt;
    reg kick_d;
  wire kick_pulse = kick & ~kick_d;
  always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt     <= 0;
            timeout <= 1'b0;
            kick_d  <= 1'b0;
        end else begin
            kick_d <= kick;
				 if (kick_pulse) begin
                cnt     <= 0;
                timeout <= 1'b0;
            end else if (cnt >= CNT_MAX) begin
                timeout <= 1'b1;
            end else begin
                cnt <= cnt + 1;
            end
        end
    end

endmodule
module shutdown_FSM(
    input  wire clk,
    input  wire rst_n,
    input  wire estop,          // active‑high (after debouncing)
    input  wire ack_pulse,      // 1‑cycle pulse from ACK button
    input  wire wdg_to,         // watchdog timeout
    output reg  shutdown,       // HIGH = machine should be stopped
    output reg  latched_fault 
    );
	  localparam [1:0] S_RUN        = 2'b00,
                     S_SHUTDOWN   = 2'b01,
                     S_WAIT_ACK   = 2'b10;

    reg [1:0] state, nxt;
	  always @(posedge clk or negedge rst_n)
        if (!rst_n)
            state <= S_SHUTDOWN;   // Safe startup state
        else
            state <= nxt;
				  always @(*) begin
        nxt = state;
        case (state)
            S_RUN:      if (estop | wdg_to) nxt = S_SHUTDOWN;
            S_SHUTDOWN: if (~estop && ack_pulse) nxt = S_WAIT_ACK;
            S_WAIT_ACK: if (~latched_fault) nxt = S_RUN;
        endcase
    end
	 always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shutdown      <= 1'b1;
            latched_fault <= 1'b1;
        end else begin
            case (nxt)
                S_RUN: begin
                    shutdown      <= 1'b0;
                    latched_fault <= 1'b0;
                end
					  S_SHUTDOWN: begin
                    shutdown      <= 1'b1;
                    latched_fault <= 1'b1;
                end
                S_WAIT_ACK: begin
                    shutdown      <= 1'b1;
                    // latched_fault remains until estop is released
                end
            endcase
        end
    end
endmodule
module slow_blinker(
 clk,
    rst_n,
    led
    );
	 input  clk;
    input  rst_n;
    output led;
    reg    led;
	 parameter CLK_HZ = 24000000;
	 function integer C_LOG2;
        input integer value;
        integer i;
        begin
            value = value - 1;
            for (i = 0; value > 0; i = i + 1)
                value = value >> 1;
            C_LOG2 = i;
        end
    endfunction
	 localparam integer CNT_MAX   = (CLK_HZ / 2 > 0) ? CLK_HZ / 2 : 1;  // 0.5 s
    localparam integer CNT_WIDTH = C_LOG2(CNT_MAX) + 1;
	 reg [CNT_WIDTH-1:0] cnt; 
	 always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 0;
            led <= 1'b0;
        end else if (cnt >= CNT_MAX) begin
            cnt <= 0;
            led <= ~led;
        end else begin
		   cnt <= cnt + 1'b1;
        end
    end

endmodule



module Esd_controller(
    input  clk,             // System clock
    input  rst_n,           // Asynchronous, active-low reset
    input  estop_a_n,       // E-STOP A (active-low)
    input  estop_b_n,       // E-STOP B (active-low)
    input  ack_n,           // ACK / Reset button (active-low)
    input  wdg_kick,  // Watchdog kick input
    output shutdown_o,      // Shutdown output
    output led_stat_o       // Status LED
);
reg sync_o;
parameter CLK_HZ = 24000000;
  wire estop_a, estop_b, ack_btn;
   debounce_button #(.CNT_WIDTH(20)) db_a (
        .clk(clk),
        .rst_n(rst_n),
        .noisy_btn(estop_a_n),
        .clean_btn(estop_a)
    );
debounce_button #(.CNT_WIDTH(20)) db_b (
        .clk(clk),
        .rst_n(rst_n),
        .noisy_btn(estop_b_n),
        .clean_btn(estop_b)
    );
 debounce_button #(.CNT_WIDTH(20)) db_ack (
        .clk(clk),
        .rst_n(rst_n),
        .noisy_btn(ack_n),
        .clean_btn(ack_btn)
    );
 wire estop_any = ~estop_a | ~estop_b;
  wire ack_pulse;
    Rising_edge_detector ed_ack (
        .clk(clk),
        .sig_in(~ack_btn),       // detect rising edge (btn released)
        .rise_pulse(ack_pulse)
    );
	  wire wdg_timeout;
    watchdogtimer #(
        .CLK_HZ(CLK_HZ),
        .TIMEOUT_MS(500)
    ) wdg_inst (
        .clk(clk),
        .rst_n(rst_n),
        .kick(wdg_kick),
        .timeout(wdg_timeout)
    );
	  wire shutdown, latched_fault;
    shutdown_FSM fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .estop(estop_any),
        .ack_pulse(ack_pulse),
        .wdg_to(wdg_timeout),
        .shutdown(shutdown),
        .latched_fault(latched_fault)
    );
assign shutdown_o = shutdown;

    // Status LED blinker (active only if no fault)
    wire blink_led;
slow_blinker #(.CLK_HZ(CLK_HZ)) blink_inst (
    .clk(clk),
    .rst_n(rst_n & ~latched_fault),  // Proper reset when rst_n is low OR fault exists
    .led(blink_led)
);

    assign led_stat_o = latched_fault ? 1'b1 : blink_led;
	 
 
endmodule


module tt_um_example (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    // Parameter for clock frequency (adjust based on your TinyTapeout clock)
    parameter CLK_HZ = 50000000; // 50MHz - adjust as needed for your actual clock
    
    // Input assignments from TinyTapeout pins
    wire estop_a_n   = ui_in[0];    // E-STOP A (active-low)
    wire estop_b_n   = ui_in[1];    // E-STOP B (active-low) 
    wire ack_n       = ui_in[2];    // ACK button (active-low)
    wire wdg_kick    = ui_in[3];    // Watchdog kick input
    wire async_in    = ui_in[4];    // Async input (if needed)
    
    // Internal wires for ESD controller outputs
    wire shutdown_out;
    wire led_status;
    wire sync_output;
    
    // Instantiate the ESD controller
    Esd_controller #(
        .CLK_HZ(CLK_HZ)
    ) esd_ctrl_inst (
        .clk(clk),
        .rst_n(rst_n),
        .estop_a_n(estop_a_n),
        .estop_b_n(estop_b_n),
        .ack_n(ack_n),
        .wdg_kick(wdg_kick),
        .async_in(async_in),
        .shutdown_o(shutdown_out),
        .led_stat_o(led_status),
        .sync_out(sync_output)
    );
    
    // Output assignments to TinyTapeout pins
    assign uo_out[0] = shutdown_out;    // Shutdown signal
    assign uo_out[1] = led_status;      // Status LED
    assign uo_out[2] = sync_output;     // Sync output
    assign uo_out[3] = 1'b0;            // Unused
    assign uo_out[4] = 1'b0;            // Unused  
    assign uo_out[5] = 1'b0;            // Unused
    assign uo_out[6] = 1'b0;            // Unused
    assign uo_out[7] = 1'b0;            // Unused
    
    // Bidirectional IOs - not used in this design
    assign uio_out = 8'b0;              // All outputs driven low
    assign uio_oe  = 8'b0;              // All pins set as inputs

    // List unused inputs to prevent warnings
    wire _unused = &{ena, ui_in[7:5], uio_in, 1'b0};

endmodule
