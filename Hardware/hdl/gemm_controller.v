module gemm_controller (
    input  wire clk,
    input  wire rst_n,

    input  wire start,
    
    input  wire input_valid,
    input  wire weight_valid,
    input  wire output_ready,
    
    output reg  input_ready,
    output reg  weight_ready,
    output reg  output_valid,
    
    output reg  compute_en,
    
    output reg  [3:0] t0,
    output reg  [3:0] t1,
    output reg  [3:0] t2,
    
    output reg  [7:0] input_beat,
    output reg  [7:0] weight_beat,
    output reg  [7:0] output_beat,

    output reg  start_accept,
    
    output reg  busy,
    output reg  done
);
    localparam  IDLE=3'd0, 
                LOAD_INPUT=3'd1, 
                LOAD_WEIGHT=3'd2,
                COMPUTE=3'd3, 
                STORE_OUTPUT=3'd4, 
                DONE=3'd5;

    reg [2:0] state;

    always @(*) begin
        input_ready  = (state == LOAD_INPUT);
        weight_ready = (state == LOAD_WEIGHT);
        output_valid = (state == STORE_OUTPUT);
        compute_en   = (state == COMPUTE);
        start_accept = (state == IDLE) && start;
        busy         = (state != IDLE) && (state != DONE);
        done         = (state == DONE);
    end

    // Temporal Ordering: D0 -> D1 -> D2
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; 
            t0 <= 0; 
            t1 <= 0; 
            t2 <= 0;
            input_beat <= 0; 
            weight_beat <= 0; 
            output_beat <= 0;
        end 
        else begin
            case (state)
                IDLE: 
                    if (start) begin 
                        input_beat <= 0; 
                        state <= LOAD_INPUT; 
                    end

                LOAD_INPUT: 
                    if (input_valid && input_ready) begin
                        if (input_beat == 8'd255) begin 
                            weight_beat <= 0; 
                            state <= LOAD_WEIGHT; 
                            end
                        else input_beat <= input_beat + 1'b1;
                    end

                LOAD_WEIGHT: 
                    if (weight_valid && weight_ready) begin
                        if (weight_beat == 8'd255) begin
                            t0 <= 0; 
                            t1 <= 0; 
                            t2 <= 0; 
                            state <= COMPUTE;
                        end 
                        else weight_beat <= weight_beat + 1'b1;
                    end

                COMPUTE: 
                    if (t2 == 4'd15) begin
                        t2 <= 0;
                        if (t1 == 4'd15) begin
                            t1 <= 0;
                            if (t0 == 4'd15) begin 
                                output_beat <= 0; 
                                state <= STORE_OUTPUT; 
                            end

                            else t0 <= t0 + 1'b1;
                        end 
                        else t1 <= t1 + 1'b1;
                    end 
                    else t2 <= t2 + 1'b1;

                STORE_OUTPUT: 
                    if (output_valid && output_ready) begin
                        if (output_beat == 8'd255) state <= DONE;
                        else output_beat <= output_beat + 1'b1;
                    end

                DONE: if (!start) state <= IDLE;

                default: state <= IDLE;
            endcase
        end
    end
endmodule
