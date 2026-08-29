module gemm_top (
    input  wire clk,
    input  wire rst_n,

    input  wire start,

    input  wire input_wr_valid,
    input  wire [511:0] input_wr_data,
    output wire input_wr_ready,
    
    input  wire weight_wr_valid,
    input  wire [511:0] weight_wr_data,
    output wire weight_wr_ready,
    
    output wire output_rd_valid,
    output wire signed [2047:0] output_rd_data,
    input  wire output_rd_ready,
    
    output wire busy,
    output wire done,

    // On-chip access; DRAM <-> L1 traffic is excluded.
    output wire [31:0] stat_pe_input_operand_uses,
    output wire [31:0] stat_pe_weight_operand_uses,
    output wire [31:0] stat_l1_input_to_pe_payload_elements,
    output wire [31:0] stat_l1_weight_to_pe_payload_elements,
    output wire [31:0] stat_l1_input_to_pe_beats,
    output wire [31:0] stat_l1_weight_to_pe_beats,
    output wire [31:0] stat_pe_to_reg_o_writes,
    output wire [31:0] stat_l1_output_to_reg_o_reads,
    output wire [31:0] stat_reg_o_to_l1_output_elements,
    output wire [31:0] stat_reg_o_to_l1_output_beats
);
    wire compute_en;
    wire [3:0] t0, t1, t2;

    wire [7:0] input_beat, weight_beat, output_beat;

    wire signed [511:0] input_tile, weight_tile;
    wire signed [2047:0] psum_tile, completed_tile;
    
    wire start_accept;

    gemm_controller u_controller (
        .clk(clk), 
        .rst_n(rst_n), 
        .start(start),
        .input_valid(input_wr_valid), 
        .weight_valid(weight_wr_valid),
        .output_ready(output_rd_ready), 
        .input_ready(input_wr_ready),
        .weight_ready(weight_wr_ready), 
        .output_valid(output_rd_valid),
        .compute_en(compute_en), 
        .t0(t0), .t1(t1), .t2(t2),
        .input_beat(input_beat), 
        .weight_beat(weight_beat), 
        .output_beat(output_beat),
        .start_accept(start_accept),
        .busy(busy), 
        .done(done)
    );
    
    l1_input u_l1_input (
        .clk(clk), 
        .write_en(input_wr_valid && input_wr_ready),
        .write_beat(input_beat), 
        .write_data(input_wr_data), 
        .t0(t0), 
        .t2(t2), 
        .tile_input_data(input_tile)
    );
    
    l1_weight u_l1_weight (
        .clk(clk), 
        .write_en(weight_wr_valid && weight_wr_ready),
        .write_beat(weight_beat), 
        .write_data(weight_wr_data), 
        .t1(t1), 
        .t2(t2), 
        .tile_weight_data(weight_tile)
    );
    
    pe_array u_pe_array (
        .input_tile(input_tile), 
        .weight_tile(weight_tile), 
        .psum_tile(psum_tile)
    );
    
    reg_o u_reg_o (
        .clk(clk), 
        .rst_n(rst_n), 
        .compute_en(compute_en), 
        .t2(t2),
        .psum_tile(psum_tile), 
        .completed_tile(completed_tile)
    );
    
    l1_output u_l1_output (
        .clk(clk), 
        .write_en(compute_en && (t2 == 4'd15)),
        .t0(t0), 
        .t1(t1), 
        .write_tile(completed_tile), 
        .read_beat(output_beat),
        .read_data(output_rd_data)
    );

    memory_access_counter u_memory_access_counter (
        .clk(clk),
        .rst_n(rst_n),
        .start_accept(start_accept),
        .compute_tile_en(compute_en),
        .t2(t2),
        .pe_input_operand_uses(stat_pe_input_operand_uses),
        .pe_weight_operand_uses(stat_pe_weight_operand_uses),
        .l1_input_to_pe_payload_elements(stat_l1_input_to_pe_payload_elements),
        .l1_weight_to_pe_payload_elements(stat_l1_weight_to_pe_payload_elements),
        .l1_input_to_pe_beats(stat_l1_input_to_pe_beats),
        .l1_weight_to_pe_beats(stat_l1_weight_to_pe_beats),
        .pe_to_reg_o_writes(stat_pe_to_reg_o_writes),
        .l1_output_to_reg_o_reads(stat_l1_output_to_reg_o_reads),
        .reg_o_to_l1_output_elements(stat_reg_o_to_l1_output_elements),
        .reg_o_to_l1_output_beats(stat_reg_o_to_l1_output_beats)
    );


endmodule
