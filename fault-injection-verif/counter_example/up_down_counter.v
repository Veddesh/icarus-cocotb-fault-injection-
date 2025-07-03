`timescale 1ns/1ps

module up_down_counter (
    input  wire       clk,
    input  wire       rst,
    input  wire       up,       // 1 = count up, 0 = count down
    output reg  [3:0] count
);

    // Synchronous up/down counter with asynchronous reset
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= 4'd0;
        end else if (up) begin
            count <= count + 1;
        end else begin
            count <= count - 1;
        end
    end

`ifdef COCOTB_SIM
    initial begin
        $dumpfile("sim_build/up_down_counter.vcd");
        $dumpvars(0, up_down_counter);
    end
`endif

endmodule
