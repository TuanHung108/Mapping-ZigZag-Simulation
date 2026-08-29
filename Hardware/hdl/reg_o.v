// 64 INT32 registers for the 8x8 output tile.  PSUM never returns to L1
// between D2 tiles; completed_tile is valid only on t2 == 15.
module reg_o (
    input  wire clk,
    input  wire rst_n,

    input  wire compute_en,
    
    input  wire [3:0] t2,
    input  wire signed [2047:0] psum_tile,
    
    output reg  signed [2047:0] completed_tile
);
    reg signed [31:0] psum [0:63];  // 64 reg_o instances
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 64; i = i + 1)
                psum[i] <= 32'sd0;
        end 
        else if (compute_en) begin
            for (i = 0; i < 64; i = i + 1) begin
                if (t2 == 4'd0)
                    psum[i] <= psum_tile[32*i +: 32];  // tile 0
                else
                    psum[i] <= $signed(psum[i]) + $signed(psum_tile[32*i +: 32]); // accumulate
            end
        end
    end

    // last D2 tile (t2 = 15) => reg_o -> L1 
    // psum changes on every accumulation clock, so it must be part of the
    // combinational sensitivity set for the final completed tile.
    always @(*) begin
        completed_tile = 2048'sd0;
        if (compute_en && (t2 == 4'd15)) begin
            for (i = 0; i < 64; i = i + 1)
                completed_tile[32*i +: 32] = $signed(psum[i]) + $signed(psum_tile[32*i +: 32]);
        end
    end

    
endmodule
