# Modular GEMM RTL

The RTL mirrors `Software/gemm_simulation_1.py`: signed INT8 `I` and `W`,
signed INT32 accumulation, 8x8x8 spatial tiles, and temporal order
`D0 -> D1 -> D2`.

`gemm_top.v` accepts 256 input then 256 weight transfers. Each is 512 bits
(64 INT8 values). During `COMPUTE`, one clock evaluates a full 8x8x8 spatial
tile: 64 output positions each reduce eight D2 products. `reg_o` keeps the
64 PSUMs from `t2=0` through `t2=15`; its final values are written to
`l1_output` only at `t2==15`. The controller then emits 256 2048-bit output
transfers, each containing 64 INT32 values.

The L1 input and weight arrays make 64 parallel byte reads, and L1 output has
a 64-word INT32 path. This is the explicit banking assumption required to
sustain the specified 512-bit / 512-bit / 2048-bit bandwidths. For silicon,
implement them as appropriately banked SRAM/BRAM, not a single-port RAM.

## QuestaSim / ModelSim

From `Gemm_RTL/Hardware/test`:

```tcl
vlib work
vlog ../hdl/pe.v ../hdl/pe_array.v ../hdl/reg_o.v ../hdl/l1_input.v ../hdl/l1_weight.v ../hdl/l1_output.v ../hdl/memory_access_counter.v ../hdl/gemm_controller.v ../hdl/gemm_top.v tb_gemm_top.v
vsim -c work.tb_gemm_top -do "run -all; quit -f"
```

Expected result:

```text
PASS: All 16384 outputs match golden result.
```
