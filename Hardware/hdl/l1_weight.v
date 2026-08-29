module l1_weight (
    input  wire clk,

    input  wire write_en,
    input  wire [7:0] write_beat,
    input  wire [511:0] write_data,

    input  wire [3:0] t1,  // t1_tile_temporal
    input  wire [3:0] t2,  // t2_tile_temporal

    output reg  signed [511:0] tile_weight_data
);
    reg signed [7:0] mem [0:16383];
    
    integer i, lane, col;
    
    // 8 elements/D2 x 8 elements/D1 = 64 elements = 1 beat
    always @(posedge clk) begin
        if (write_en)
            for (i = 0; i < 64; i = i + 1)
                mem[write_beat*64+i] <= write_data[8*i +: 8];
    end
    
    // Combinational banked read for one 8x8 weight tile.
    always @(*) begin
        for (lane = 0; lane < 8; lane = lane + 1)
            for (col = 0; col < 8; col = col + 1)
                tile_weight_data[8*(lane*8+col) +: 8] = mem[((t2*8+lane)*128) + (t1*8+col)];
    end
endmodule
