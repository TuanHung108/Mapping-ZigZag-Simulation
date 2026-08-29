module l1_output (
    input  wire clk,

    input  wire write_en,

    input  wire [3:0] t0,
    input  wire [3:0] t1,

    input  wire signed [2047:0] write_tile, // 1 tile = 2048 bits = 64 element INT32
    input  wire [7:0] read_beat,

    output reg  signed [2047:0] read_data
);
    reg signed [31:0] mem [0:16383];

    integer row, col, i;

    // Tensor 0 [D0][D1]
    always @(posedge clk) begin
        if (write_en)
            for (row = 0; row < 8; row = row + 1)
                for (col = 0; col < 8; col = col + 1)
                    mem[((t0*8+row)*128) + (t1*8+col)] <= write_tile[32*(row*8+col) +: 32];
    end

    // Store stream is row-major O[d0][d1], 64 INT32 values per beat.
    // read_data must also update when the final Reg_O tile writes mem while
    // read_beat remains zero for the first store transfer.
    always @(*) begin
        for (i = 0; i < 64; i = i + 1)
            read_data[32*i +: 32] = mem[read_beat*64+i];
    end
endmodule
