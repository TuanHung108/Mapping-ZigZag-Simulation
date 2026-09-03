// On-chip data-movement instrumentation for the fixed 8x8x8 GEMM mapping.
// All counters track clocked architectural events, never combinational toggles.
module memory_access_counter (
    input  wire clk,
    input  wire rst_n,

    input  wire start_accept,
    input  wire compute_tile_en,
    input  wire [3:0] t2,

    output reg  [31:0] pe_input_operand_uses,
    output reg  [31:0] pe_weight_operand_uses,

    output reg  [31:0] l1_input_to_pe_payload_elements,
    output reg  [31:0] l1_weight_to_pe_payload_elements,
    
    output reg  [31:0] l1_input_to_pe_beats,
    output reg  [31:0] l1_weight_to_pe_beats,

    output reg  [31:0] pe_to_reg_o_writes,
    
    output reg  [31:0] l1_output_to_reg_o_reads,
    output reg  [31:0] reg_o_to_l1_output_elements,
    output reg  [31:0] reg_o_to_l1_output_beats
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n || start_accept) begin
            pe_input_operand_uses           <= 32'd0;
            pe_weight_operand_uses          <= 32'd0;
            l1_input_to_pe_payload_elements <= 32'd0;
            l1_weight_to_pe_payload_elements <= 32'd0;
            l1_input_to_pe_beats            <= 32'd0;
            l1_weight_to_pe_beats           <= 32'd0;
            pe_to_reg_o_writes              <= 32'd0;
            l1_output_to_reg_o_reads        <= 32'd0;
            reg_o_to_l1_output_elements     <= 32'd0;
            reg_o_to_l1_output_beats        <= 32'd0;
        end 
        else if (compute_tile_en) begin
            pe_input_operand_uses           <= pe_input_operand_uses + 32'd512;
            pe_weight_operand_uses          <= pe_weight_operand_uses + 32'd512;
            l1_input_to_pe_payload_elements <= l1_input_to_pe_payload_elements + 32'd64;    
            l1_weight_to_pe_payload_elements <= l1_weight_to_pe_payload_elements + 32'd64;  
            l1_input_to_pe_beats            <= l1_input_to_pe_beats + 32'd1;    // I/L1 rd_out_to_low
            l1_weight_to_pe_beats           <= l1_weight_to_pe_beats + 32'd1;   // W/L1 rd_out_to_low
            pe_to_reg_o_writes              <= pe_to_reg_o_writes + 32'd64;     // O/Reg_O wr_in_by_low

            // No L1 Output -> Reg_O event exists in this dataflow.
            // The old PSUM stays inside Reg_O between D2 tiles.
            if (t2 == 4'd15) begin
                reg_o_to_l1_output_elements <= reg_o_to_l1_output_elements + 32'd64;
                reg_o_to_l1_output_beats    <= reg_o_to_l1_output_beats + 32'd1;    // O/L1 wr_in_by_low
            end
        end
    end
endmodule
