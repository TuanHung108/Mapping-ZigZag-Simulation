module pe (
    input  wire signed [7:0] a,
    input  wire signed [7:0] b,
    output wire signed [15:0] product
);
    assign product = a * b;
endmodule


// 8 D0 x 8 D1 x 8 D2 = 512 PE instances.
module pe_array (
    input  wire signed [511:0] input_tile,
    input  wire signed [511:0] weight_tile,

    output reg  signed [2047:0] psum_tile  // partial sum of 64 output positions
);
    wire signed [8191:0] products; // 16 bits x 512 products = 8192

    genvar gr, gc, gl;
    generate
        for (gr = 0; gr < 8; gr = gr + 1) begin: GEN_ROW
            for (gc = 0; gc < 8; gc = gc + 1) begin: GEN_COL
                for (gl = 0; gl < 8; gl = gl + 1) begin: GEN_LANE
                    pe pe_inst (
                        .a(input_tile[8*(gr*8+gl) +: 8]),
                        .b(weight_tile[8*(gl*8+gc) +: 8]),
                        .product(products[16*((gr*8+gc)*8+gl) +: 16])
                    );
                end
            end
        end
    endgenerate

    // Spatiall Reduction D2
    integer r, c, k;
    always @(*) begin
        for (r = 0; r < 8; r = r + 1) begin
            for (c = 0; c < 8; c = c + 1) begin

                psum_tile[32*(r*8+c) +: 32] = 32'sd0;

                for (k = 0; k < 8; k = k + 1)
                    psum_tile[32*(r*8+c) +: 32] =
                        $signed(psum_tile[32*(r*8+c) +: 32]) +
                        $signed(products[16*((r*8+c)*8+k) +: 16]);
            end
        end
    end
endmodule
