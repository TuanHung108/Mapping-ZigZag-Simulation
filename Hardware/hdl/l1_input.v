module l1_input (
    input  wire clk,
    
    input  wire write_en,
    input  wire [7:0] write_beat,
    input  wire [511:0] write_data,

    input  wire [3:0] t0,  // t0_count_tile_temporal
    input  wire [3:0] t2,  // t2_count_tile_temporal

    output reg  signed [511:0] tile_input_data
);

    // 8 bank = 8 hàng - mỗi bank lưu 8 phần tử = 8 cột
    (* ram_style = "block" *)
    reg [63:0] mem [0:7][0:255];
    reg [63:0] read_word [0:7];

    wire [7:0] read_addr = {t0, t2};

    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : BANK_INPUT
            always @(posedge clk) begin
                if (write_en) begin
                    mem[i][write_beat] <= write_data[64*i +: 64];
                end
                else begin
                    read_word[i] <= mem[i][read_addr];
                end
            end
        end
    endgenerate

    integer row;
    always @(*) begin
        tile_input_data = 512'd0;

        for (row = 0; row < 8; row = row + 1)
            tile_input_data[64*row +: 64] = read_word[row];
    end
endmodule
