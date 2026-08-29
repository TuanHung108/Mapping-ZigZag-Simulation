`timescale 1ns/1ps

module tb_gemm_top;
    reg clk, rst_n, start;
    reg input_wr_valid, weight_wr_valid;
    reg [511:0] input_wr_data, weight_wr_data;
    wire input_wr_ready, weight_wr_ready, output_rd_valid, busy, done;
    wire signed [2047:0] output_rd_data;
    wire output_rd_ready;
    wire [31:0] stat_pe_input_operand_uses, stat_pe_weight_operand_uses;
    wire [31:0] stat_l1_input_to_pe_payload_elements, stat_l1_weight_to_pe_payload_elements;
    wire [31:0] stat_l1_input_to_pe_beats, stat_l1_weight_to_pe_beats;
    wire [31:0] stat_pe_to_reg_o_writes;
    wire [31:0] stat_l1_output_to_reg_o_reads;
    wire [31:0] stat_reg_o_to_l1_output_elements, stat_reg_o_to_l1_output_beats;
    reg signed [7:0] input_file [0:16383];
    reg signed [7:0] weight_file [0:16383];
    reg signed [31:0] golden [0:16383];
    integer input_index, weight_index, output_index, errors;
    integer lane, beat_errors;

    gemm_top dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .input_wr_valid(input_wr_valid), .input_wr_data(input_wr_data), .input_wr_ready(input_wr_ready),
        .weight_wr_valid(weight_wr_valid), .weight_wr_data(weight_wr_data), .weight_wr_ready(weight_wr_ready),
        .output_rd_valid(output_rd_valid), .output_rd_data(output_rd_data), .output_rd_ready(output_rd_ready),
        .busy(busy), .done(done),
        .stat_pe_input_operand_uses(stat_pe_input_operand_uses),
        .stat_pe_weight_operand_uses(stat_pe_weight_operand_uses),
        .stat_l1_input_to_pe_payload_elements(stat_l1_input_to_pe_payload_elements),
        .stat_l1_weight_to_pe_payload_elements(stat_l1_weight_to_pe_payload_elements),
        .stat_l1_input_to_pe_beats(stat_l1_input_to_pe_beats),
        .stat_l1_weight_to_pe_beats(stat_l1_weight_to_pe_beats),
        .stat_pe_to_reg_o_writes(stat_pe_to_reg_o_writes),
        .stat_l1_output_to_reg_o_reads(stat_l1_output_to_reg_o_reads),
        .stat_reg_o_to_l1_output_elements(stat_reg_o_to_l1_output_elements),
        .stat_reg_o_to_l1_output_beats(stat_reg_o_to_l1_output_beats)
    );

    initial begin clk = 0; forever #5 clk = ~clk; end
    assign output_rd_ready = 1'b1;

    // Input and Weight DRAM sources send data in the same row-major order as
    // input.hex and weight.hex: 64 INT8 values in each 512-bit transfer.
    always @(*) begin
        input_wr_valid = input_wr_ready && (input_index < 16384);
        weight_wr_valid = weight_wr_ready && (weight_index < 16384);
        input_wr_data = 512'd0;
        weight_wr_data = 512'd0;
        for (lane = 0; lane < 64; lane = lane + 1) begin
            if (input_index + lane < 16384)
                input_wr_data[8*lane +: 8] = input_file[input_index + lane];
            if (weight_index + lane < 16384)
                weight_wr_data[8*lane +: 8] = weight_file[weight_index + lane];
        end
    end

    // Sink and compare all 256 output beats = 16384 signed INT32 results.
    always @(posedge clk) begin
        if (!rst_n) begin
            input_index <= 0; weight_index <= 0; output_index <= 0; errors <= 0;
        end else begin
            if (input_wr_valid && input_wr_ready) input_index <= input_index + 64;
            if (weight_wr_valid && weight_wr_ready) weight_index <= weight_index + 64;
            if (output_rd_valid && output_rd_ready) begin
                beat_errors = 0;
                for (lane = 0; lane < 64; lane = lane + 1)
                    if ($signed(output_rd_data[32*lane +: 32]) !== golden[output_index + lane]) begin
                        if ((errors + beat_errors) < 10)
                            $display("FAIL: index=%0d expected=%0d actual=%0d", output_index + lane,
                                golden[output_index + lane], $signed(output_rd_data[32*lane +: 32]));
                        beat_errors = beat_errors + 1;
                    end
                errors <= errors + beat_errors;
                output_index <= output_index + 64;
            end
        end
    end

    initial begin
        $readmemh("C:/Source_Code/ZigZag/Gemm_RTL/Software/input.hex", input_file);
        $readmemh("C:/Source_Code/ZigZag/Gemm_RTL/Software/weight.hex", weight_file);
        $readmemh("C:/Source_Code/ZigZag/Gemm_RTL/Software/golden_output.hex", golden);
        rst_n = 0; start = 0;
        repeat (2) @(posedge clk);
        rst_n = 1;
        @(posedge clk); start = 1;
        @(posedge clk); start = 0;
        @(posedge done);
        $display("ACCESS: L1 I/W payload=%0d/%0d, beats=%0d/%0d, PE uses=%0d/%0d",
            stat_l1_input_to_pe_payload_elements, stat_l1_weight_to_pe_payload_elements,
            stat_l1_input_to_pe_beats, stat_l1_weight_to_pe_beats,
            stat_pe_input_operand_uses, stat_pe_weight_operand_uses);
        
        $display("ACCESS: PE->Reg_O=%0d, L1->Reg_O=%0d, Reg_O->L1=%0d elements / %0d beats",
            stat_pe_to_reg_o_writes,
            stat_l1_output_to_reg_o_reads, stat_reg_o_to_l1_output_elements,
            stat_reg_o_to_l1_output_beats);

        if ((errors == 0) && (output_index == 16384) &&
            (stat_pe_input_operand_uses == 32'd2097152) &&
            (stat_pe_weight_operand_uses == 32'd2097152) &&
            (stat_l1_input_to_pe_payload_elements == 32'd262144) &&
            (stat_l1_weight_to_pe_payload_elements == 32'd262144) &&
            (stat_l1_input_to_pe_beats == 32'd4096) &&
            (stat_l1_weight_to_pe_beats == 32'd4096) &&
            (stat_pe_to_reg_o_writes == 32'd262144) &&
            (stat_l1_output_to_reg_o_reads == 32'd0) &&
            (stat_reg_o_to_l1_output_elements == 32'd16384) &&
            (stat_reg_o_to_l1_output_beats == 32'd256))
            $display("PASS: All 16384 outputs match golden result.");
        else
            $display("FAIL: output or on-chip access counters do not match expected values.");
        $finish;
    end
endmodule
