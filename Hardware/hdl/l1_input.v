module l1_input (
    input  wire clk,
    
    input  wire write_en,
    input  wire [7:0] write_beat,
    input  wire [511:0] write_data,

    input  wire [3:0] t0,  // t0_count_tile_temporal
    input  wire [3:0] t2,  // t2_count_tile_temporal

    output reg  signed [511:0] tile_input_data
);
    (*ram_style = "block"*)
    reg signed [7:0] mem [0:16383];  // 128 x 128 = 16384 INT8
    
    integer i, row, lane;

    // 1 beat = 64 elements = 8 elements/D0 x 8 elements/D2 
    always @(posedge clk) begin
        if (write_en)
            for (i = 0; i < 64; i = i + 1)
                mem[write_beat*64+i] <= write_data[8*i +: 8];
    end

    // Include address and memory changes.  A sensitivity list containing the
    // loop variables is incorrect: it leaves tile_input_data stale/X after
    // the sequential load updates mem.
    always @(*) begin
        for (row = 0; row < 8; row = row + 1)
            for (lane = 0; lane < 8; lane = lane + 1)
                tile_input_data[8*(row*8+lane) +: 8] = mem[((t0*8+row)*128) + (t2*8+lane)];
    end
endmodule
