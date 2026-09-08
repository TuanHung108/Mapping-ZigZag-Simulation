module l1_weight (
    input  wire clk,

    input  wire write_en,
    input  wire [7:0] write_beat,
    input  wire [511:0] write_data,

    input  wire [3:0] t1,  // t1_tile_temporal
    input  wire [3:0] t2,  // t2_tile_temporal

    output reg  signed [511:0] tile_weight_data
);
    (* ram_style = "block" *)
    
    reg [63:0] mem [0:7][0:255];
    reg [63:0] read_word [0:7];

    wire [7:0] read_addr = {t2, t1};

    genvar bank;
    generate
        for (bank = 0; bank < 8; bank = bank + 1) begin : BANK_WEIGHT
            always @(posedge clk) begin
                if (write_en)
                    mem[bank][write_beat] <= write_data[64*bank +: 64];
                else
                    read_word[bank] <= mem[bank][read_addr];
            end
        end
    endgenerate

    integer lane;
    always @(*) begin
        tile_weight_data = 512'd0;
        for (lane = 0; lane < 8; lane = lane + 1)
            tile_weight_data[64*lane +: 64] = read_word[lane];
    end
endmodule
