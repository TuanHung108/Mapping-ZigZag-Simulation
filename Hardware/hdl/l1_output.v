module l1_output (
    input  wire clk,
    input wire rst_n,

    input  wire write_en,

    input  wire [3:0] t0,
    input  wire [3:0] t1,

    input wire read_start,
    input  wire signed [2047:0] write_tile, // 1 tile = 2048 bits = 64 element INT32
    input wire read_ready,
    input  wire [7:0] read_beat,

    output reg signed [2047:0] read_data,
    
    output reg read_valid,
    output reg read_busy
);
    // Eight row banks.  Each word is one 8-element output row of a tile.
    (* ram_style = "block" *)
    reg [255:0] mem [0:7][0:255];
    reg [255:0] bank_read_data [0:7];
    reg [7:0] read_addr;
    reg issue_pending;
    reg capture_pending;

    wire [7:0] write_addr = {t0, t1};
    genvar bank;

    generate
        for (bank = 0; bank < 8; bank = bank + 1) begin : BANK_OUTPUT
            always @(posedge clk) begin
                if (write_en)
                    mem[bank][write_addr] <= write_tile[256*bank +: 256];
                else if (read_busy && issue_pending)
                    bank_read_data[bank] <= mem[bank][read_addr];
            end
        end
    endgenerate

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            read_data    <= 2048'd0;
            read_valid   <= 1'b0;
            read_busy    <= 1'b0;
            read_addr    <= 8'd0;
            issue_pending <= 1'b0;
            capture_pending <= 1'b0;
        end
        else begin
            if (read_valid && read_ready)
                read_valid <= 1'b0;

            if (read_start && !read_busy && !read_valid) begin
                read_addr <= read_beat;
                read_busy <= 1'b1;
                issue_pending <= 1'b1;
            end
            else if (read_busy && issue_pending) begin
                issue_pending <= 1'b0;
                capture_pending <= 1'b1;
            end
            else if (read_busy && capture_pending) begin
                for (i = 0; i < 8; i = i + 1)
                    read_data[256*i +: 256] <= bank_read_data[i];

                read_valid <= 1'b1;
                read_busy <= 1'b0;
                capture_pending <= 1'b0;
            end
        end
    end
endmodule
