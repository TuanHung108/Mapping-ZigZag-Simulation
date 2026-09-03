import numpy as np

IDLE = 0
LOAD = 1
COMPUTE = 2
STORE = 3
DONE = 4

# ============================================================
# CONFIGURATION
# ============================================================

def create_config(
    D0_SIZE=128,
    D1_SIZE=128,
    D2_SIZE=128,

    # Spatial mapping
    SPATIAL_TILE_D0=8,
    SPATIAL_TILE_D1=8,
    SPATIAL_TILE_D2=8,

    # Temporal mapping
    NUM_TEMPORAL_TILES_D0=16,
    NUM_TEMPORAL_TILES_D1=16,
    NUM_TEMPORAL_TILES_D2=16,

    # Datatype
    INPUT_BYTES=1,
    WEIGHT_BYTES=1,
    ACC_BYTES=4,

    # Memory Bandwidth
    L1_INPUT_BW_BITS=512,
    L1_WEIGHT_BW_BITS=512,
    L1_OUTPUT_BW_BITS=2048
):
    cfg = {
        # Problem dimensions
        "D0_SIZE": D0_SIZE,
        "D1_SIZE": D1_SIZE,
        "D2_SIZE": D2_SIZE,

        # Spatial mapping
        "SPATIAL_TILE_D0": SPATIAL_TILE_D0,
        "SPATIAL_TILE_D1": SPATIAL_TILE_D1,
        "SPATIAL_TILE_D2": SPATIAL_TILE_D2,

        # Temporal mapping
        "NUM_TEMPORAL_TILES_D0": NUM_TEMPORAL_TILES_D0,
        "NUM_TEMPORAL_TILES_D1": NUM_TEMPORAL_TILES_D1,
        "NUM_TEMPORAL_TILES_D2": NUM_TEMPORAL_TILES_D2,

        # Datatypes
        "INPUT_BYTES": INPUT_BYTES,
        "WEIGHT_BYTES": WEIGHT_BYTES,
        "ACC_BYTES": ACC_BYTES,

        # Bandwidth
        "L1_INPUT_BW_BITS": L1_INPUT_BW_BITS,
        "L1_WEIGHT_BW_BITS": L1_WEIGHT_BW_BITS,
        "L1_OUTPUT_BW_BITS": L1_OUTPUT_BW_BITS
    }

    # --------------------------------------------------------
    # Check mapping
    # --------------------------------------------------------

    assert D0_SIZE % SPATIAL_TILE_D0 == 0
    assert D1_SIZE % SPATIAL_TILE_D1 == 0
    assert D2_SIZE % SPATIAL_TILE_D2 == 0

    assert D0_SIZE // SPATIAL_TILE_D0 == NUM_TEMPORAL_TILES_D0
    assert D1_SIZE // SPATIAL_TILE_D1 == NUM_TEMPORAL_TILES_D1
    assert D2_SIZE // SPATIAL_TILE_D2 == NUM_TEMPORAL_TILES_D2

    cfg["NUM_PE"] = SPATIAL_TILE_D0 * SPATIAL_TILE_D1 * SPATIAL_TILE_D2
    cfg["NUM_REG_O"] = SPATIAL_TILE_D0 * SPATIAL_TILE_D1

    cfg["OUTPUT_SIZE"] = D0_SIZE * D1_SIZE
    cfg["INPUT_SIZE"] = D0_SIZE * D2_SIZE
    cfg["WEIGHT_SIZE"] = D2_SIZE * D1_SIZE

    cfg["L1_INPUT_ELEMENTS_PER_TRANSFER"] = (cfg["L1_INPUT_BW_BITS"] // (INPUT_BYTES * 8))   # 64 elements/transfer
    cfg["L1_WEIGHT_ELEMENTS_PER_TRANSFER"] = (cfg["L1_WEIGHT_BW_BITS"] // (WEIGHT_BYTES * 8)) # 64 elements/transfer
    cfg["L1_OUTPUT_ELEMENTS_PER_TRANSFER"] = (cfg["L1_OUTPUT_BW_BITS"] // (ACC_BYTES * 8)) # 64 elements/transfer

    return cfg


# ============================================================
# STATE
# ============================================================

def create_state(cfg):

    stats = {
        # Compute
        "total_macs": 0,
        "total_ops": 0,
        "compute_events": 0,

        # External memory
        "dram_read_input": 0,
        "dram_read_weight": 0,
        "dram_write_output": 0,

        "ddr_read_bytes": 0,
        "ddr_write_bytes": 0,

        # Element-level data movement
        "l1_to_pe_input_reads": 0,
        "l1_to_pe_weight_reads": 0,

        "l1_to_reg_output_reads": 0,

        "pe_to_reg_output_writes": 0,
        
        "reg_to_l1_output_writes": 0,    
    }

    memory_access = {
        "O": [
            {
                "memory": "Reg_O",
                "rd_out_to_low": 0,
                "wr_in_by_low": 0,
                "rd_out_to_high": 0,
                "wr_in_by_high": 0,
            },
            {
                "memory": "L1",
                "rd_out_to_low": 0,
                "wr_in_by_low": 0,
                "rd_out_to_high": 0,
                "wr_in_by_high": 0,
            },
        ],

        "I": [
            {
                "memory": "L1",
                "rd_out_to_low": 0,
                "wr_in_by_low": 0,
                "rd_out_to_high": 0,
                "wr_in_by_high": 0,
            }
        ],

        "W": [
            {
                "memory": "L1",
                "rd_out_to_low": 0,
                "wr_in_by_low": 0,
                "rd_out_to_high": 0,
                "wr_in_by_high": 0,
            }
        ],
    }

    dram_input = []
    dram_weight = []

    dram_output = [0 for _ in range(cfg["OUTPUT_SIZE"])]

    l1_input = np.zeros((cfg["D0_SIZE"], cfg["D2_SIZE"]), dtype=np.int32)
    l1_weight = np.zeros((cfg["D2_SIZE"], cfg["D1_SIZE"]), dtype=np.int32)
    l1_output = np.zeros((cfg["D0_SIZE"], cfg["D1_SIZE"]), dtype=np.int32)


    reg_o = np.zeros((cfg["SPATIAL_TILE_D0"], cfg["SPATIAL_TILE_D1"]), dtype=np.int32)

    state = {
        "cfg": cfg,
        "stats": stats,
        "memory_access": memory_access,

        "dram_input": dram_input,
        "dram_weight": dram_weight,
        "dram_output": dram_output,

        "l1_input": l1_input,
        "l1_weight": l1_weight,
        "l1_output": l1_output,

        "reg_o": reg_o,

        "fsm_state": IDLE,
    }

    return state

# ============================================================
# LOADING DATA
# ============================================================

def read_int8_hex(filename):
    data = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            
            if not line:
                continue

            value = int(line, 16)

            # unsigned byte -> signed INT8
            if value >= 128:
                value -= 256

            data.append(value)

    return data


def load_data_from_file(
    state,
    input_path,
    weight_path,
):

    cfg = state["cfg"]

    input_data = read_int8_hex(input_path)

    expected_input = (cfg["D0_SIZE"] * cfg["D2_SIZE"])

    assert len(input_data) == expected_input, (
        f"Input size mismatch: "
        f"expected {expected_input}, "
        f"got {len(input_data)}"
    )

    # load input into DRAM
    state["dram_input"] = input_data

    weight_data = read_int8_hex(weight_path)

    expected_weight = (cfg["D2_SIZE"] * cfg["D1_SIZE"])

    assert len(weight_data) == expected_weight, (
        f"Weight size mismatch: "
        f"expected {expected_weight}, "
        f"got {len(weight_data)}"
    )

    # load weight into DRAM
    state["dram_weight"] = weight_data

    print("\n" + "═" * 78)
    print(" DATA LOADING ".center(78, "═"))
    print("═" * 78)
    print(f"Input  : {len(input_data)} INT8")
    print(f"Weight : {len(weight_data)} INT8")



# ============================================================
# DRAM -> L1
# ============================================================

def load_input_to_l1(state):
    cfg = state["cfg"]
    stats = state["stats"]

    for d0 in range(cfg["D0_SIZE"]):
        for d2 in range(cfg["D2_SIZE"]):

            addr = (d0 * cfg["D2_SIZE"] + d2)

            state["l1_input"][d0][d2] = state["dram_input"][addr]

            stats["dram_read_input"] += 1
            stats["ddr_read_bytes"] += cfg["INPUT_BYTES"]

    # stats["load_events"] += 1


def load_weight_to_l1(state):
    cfg = state["cfg"]
    stats = state["stats"]

    for d2 in range(cfg["D2_SIZE"]):
        for d1 in range(cfg["D1_SIZE"]):

            addr = (d2 * cfg["D1_SIZE"] + d1)

            state["l1_weight"][d2][d1] = state["dram_weight"][addr]

            stats["dram_read_weight"] += 1
            stats["ddr_read_bytes"] += cfg["WEIGHT_BYTES"]


# ============================================================
# PE ARRAY
# ============================================================

def pe(input_value, weight_value):
    return input_value * weight_value


def pe_array(state, d0, d1, d2_start):
    cfg = state["cfg"]
    stats = state["stats"]
    memory_access = state["memory_access"]

    spatial_tile_d2 = cfg["SPATIAL_TILE_D2"]

    spatial_reduction = 0

    for d2_s in range(spatial_tile_d2):

        d2 = d2_start + d2_s

        input_value = state["l1_input"][d0][d2]
        weight_value = state["l1_weight"][d2][d1]

        stats["l1_to_pe_input_reads"] += 1
        stats["l1_to_pe_weight_reads"] += 1

        product = pe(input_value, weight_value)

        spatial_reduction += product

        state["stats"]["total_macs"] += 1
        state["stats"]["total_ops"] += 2

    return spatial_reduction



# ============================================================
# SPATIAL TILE
# ============================================================

def compute_spatial_tile(state, t0, t2, t1):
    cfg = state["cfg"]
    stats = state["stats"]
    memory_access = state["memory_access"]
    reg_o = state["reg_o"]

    spatial_tile_d0 = cfg["SPATIAL_TILE_D0"]
    spatial_tile_d1 = cfg["SPATIAL_TILE_D1"]
    spatial_tile_d2 = cfg["SPATIAL_TILE_D2"]

    stats["compute_events"] += 1

    d2_start = t2 * spatial_tile_d2

    for d0_s in range(spatial_tile_d0):
        for d1_s in range(spatial_tile_d1):

            d0 = (t0 * spatial_tile_d0 + d0_s)
            d1 = (t1 * spatial_tile_d1 + d1_s)

            spatial_reduction = pe_array(state, d0, d1, d2_start)

            if t2 == 0:
                previous_psum = 0
            else:
                previous_psum = state["l1_output"][d0][d1]

                stats["l1_to_reg_output_reads"] += 1

            reg_o[d0_s][d1_s] = (previous_psum + spatial_reduction)
            stats["pe_to_reg_output_writes"] += 1

            # Reg_O -> L1
            state["l1_output"][d0][d1] = reg_o[d0_s][d1_s]
            stats["reg_to_l1_output_writes"] += 1


# ============================================================
# L1 -> DRAM
# ============================================================

def store_output_to_dram(state):
    cfg = state["cfg"]
    stats = state["stats"]

    for d0 in range(cfg["D0_SIZE"]):
        for d1 in range(cfg["D1_SIZE"]):

            addr = (d0 * cfg["D1_SIZE"]+ d1)

            state["dram_output"][addr] = int(state["l1_output"][d0][d1])

            stats["dram_write_output"] += 1
            stats["ddr_write_bytes"] += cfg["ACC_BYTES"]


def calculate_memory_access(state):

    cfg = state["cfg"]
    stats = state["stats"]
    access = state["memory_access"]

    # L1 I
    i_raw_element_reads = (stats["l1_to_pe_input_reads"])
    i_reuse_factor = (cfg["SPATIAL_TILE_D0"])
    # i_stationary_factor = (cfg["NUM_TEMPORAL_TILES_D1"])
    i_element_reads = (i_raw_element_reads // i_reuse_factor)
    i_transfer_reads = int(np.ceil(i_element_reads / cfg["L1_INPUT_ELEMENTS_PER_TRANSFER"]))

    access["I"][0]["rd_out_to_low"] = (i_transfer_reads)

    # L1 W
    w_raw_element_reads = (stats["l1_to_pe_weight_reads"])
    w_reuse_factor = (cfg["SPATIAL_TILE_D0"])
    w_element_reads = (w_raw_element_reads // w_reuse_factor)
    w_transfer_reads = int(np.ceil(w_element_reads / cfg["L1_WEIGHT_ELEMENTS_PER_TRANSFER"]))

    access["W"][0]["rd_out_to_low"] = (w_transfer_reads)


    # Output
    o_pe_to_reg = (stats["pe_to_reg_output_writes"])
    o_l1_to_reg = (stats["l1_to_reg_output_reads"])
    o_reg_to_l1 = (stats["reg_to_l1_output_writes"])
    
    # --------------------------------------------------------
    # Reg_O
    # --------------------------------------------------------

    access["O"][0]["rd_out_to_low"] = 0
    access["O"][0]["wr_in_by_low"] = (o_pe_to_reg)
    access["O"][0]["rd_out_to_high"] = (o_reg_to_l1)
    access["O"][0]["wr_in_by_high"] = (o_l1_to_reg)

    # --------------------------------------------------------
    # L1 O
    # --------------------------------------------------------

    o_l1_elements_per_transfer = (cfg["L1_OUTPUT_ELEMENTS_PER_TRANSFER"])
    o_l1_read_transfers = int(np.ceil(o_l1_to_reg / o_l1_elements_per_transfer))
    o_l1_write_transfers = int(np.ceil(o_reg_to_l1 / o_l1_elements_per_transfer))

    access["O"][1]["rd_out_to_low"] = (o_l1_read_transfers)
    access["O"][1]["wr_in_by_low"] = (o_l1_write_transfers)
    access["O"][1]["rd_out_to_high"] = 0
    access["O"][1]["wr_in_by_high"] = 0


# ============================================================
# MAPPING EXECUTION
# ============================================================

def run_zigzag_mapping(state):

    cfg = state["cfg"]

    # Reset statistics
    for key in state["stats"]:
        state["stats"][key] = 0

    for tensor in state["memory_access"]:
        for level in state["memory_access"][tensor]:
            for access in level:
                if access != "memory":
                    level[access] = 0


    state["fsm_state"] = LOAD

    load_input_to_l1(state)
    load_weight_to_l1(state)


    for t0 in range(cfg["NUM_TEMPORAL_TILES_D0"]):
        for t2 in range(cfg["NUM_TEMPORAL_TILES_D2"]):
            for t1 in range(cfg["NUM_TEMPORAL_TILES_D1"]):
                state["fsm_state"] = COMPUTE

                compute_spatial_tile(state, t0, t2, t1)


    state["fsm_state"] = STORE

    store_output_to_dram(state)

    state["fsm_state"] = DONE


# ============================================================
# GOLDEN OUTPUT
# ============================================================

def load_golden_output(filename, cfg):

    data = []

    with open(filename, "r") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            value = int(line, 16)

            # signed INT32
            if value >= 0x80000000:
                value -= 0x100000000

            data.append(value)

    expected = (cfg["D0_SIZE"] * cfg["D1_SIZE"])

    assert len(data) == expected, (
        f"Golden output size mismatch: "
        f"expected {expected}, "
        f"got {len(data)}"
    )

    return np.array(data, dtype=np.int32).reshape(cfg["D0_SIZE"], cfg["D1_SIZE"])


# ============================================================
# GOLDEN CHECK
# ============================================================

def check_golden(state, golden_path):
    cfg = state["cfg"]

    hw_output = np.array(state["dram_output"], dtype=np.int32).reshape(cfg["D0_SIZE"], cfg["D1_SIZE"])
    golden_output = load_golden_output(golden_path, cfg)

    if np.array_equal(hw_output, golden_output):

        print("\n" + "═" * 78)
        print(" GOLDEN MATCH (Python Hardware Simulation Output Correct!) ".center(78, "═"))
        print("═" * 78)

        return True

    print()
    print("=" * 60)
    print("GOLDEN MISMATCH")
    print("=" * 60)

    mismatch = np.argwhere(hw_output != golden_output)

    print(f"Number of mismatched elements: {len(mismatch)}")

    # Print first 20 mismatches
    print()
    print("First mismatches:")

    for idx in mismatch[:20]:

        d0, d1 = idx

        print(
            f"O[{d0}][{d1}] : "
            f"HW={hw_output[d0][d1]} "
            f"Golden={golden_output[d0][d1]}"
        )

    return False


# ============================================================
# REPORT
# ============================================================

def print_table(headers, rows, widths, aligns=None):
    """In bảng chuẩn khung viền Box Drawing với căn lề linh hoạt.
    
    aligns: danh sách 'L' (left) hoặc 'R' (right) cho từng cột.
    """
    if aligns is None:
        aligns = ["L"] * len(headers)

    # Các đường viền khung
    top_line    = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    header_sep  = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    bottom_line = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

    # In đường viền trên cùng
    print(top_line)

    # In Header
    header_str = "│ " + " │ ".join(
        f"{h:<{w}}" if a == "L" else f"{h:>{w}}"
        for h, w, a in zip(headers, widths, aligns)
    ) + " │"
    print(header_str)
    print(header_sep)

    # In từng dòng Dữ liệu (Rows)
    for row in rows:
        row_str = "│ " + " │ ".join(
            f"{str(val):<{w}}" if a == "L" else f"{str(val):>{w}}"
            for val, w, a in zip(row, widths, aligns)
        ) + " │"
        print(row_str)

    # In đường viền dưới cùng
    print(bottom_line)


def print_section_header(title, width=78):
    """In tiêu đề section gạch ngang 2 đầu."""
    print(f"\n┌── {title} " + "─" * (width - 5 - len(title)) + "┐")


def report(state):
    cfg = state["cfg"]
    stats = state["stats"]
    access = state["memory_access"]

    calculate_memory_access(state)

    print("\n" + "═" * 78)
    print(" GEMM MAPPING HARDWARE SIMULATION REPORT ".center(78, "═"))
    print("═" * 78)

    # ========================================================
    # MAPPING
    # ========================================================
    print_section_header("1. HARDWARE & MAPPING CONFIGURATION")
    
    print_table(
        ["Dimension", "Problem Size", "Spatial Tile", "Temporal Tile"],
        [
            ["D0", cfg["D0_SIZE"], cfg["SPATIAL_TILE_D0"], cfg["NUM_TEMPORAL_TILES_D0"]],
            ["D1", cfg["D1_SIZE"], cfg["SPATIAL_TILE_D1"], cfg["NUM_TEMPORAL_TILES_D1"]],
            ["D2", cfg["D2_SIZE"], cfg["SPATIAL_TILE_D2"], cfg["NUM_TEMPORAL_TILES_D2"]],
        ],
        [11, 14, 14, 15],
        ["L", "R", "R", "R"]
    )

    print(f"  • Temporal Order : D0 -> D2 -> D1")
    print(f"  • PEs            : {cfg['NUM_PE']:,}")
    print(f"  • Reg_O          : {cfg['NUM_REG_O']:,}")

    # ========================================================
    # COMPUTE
    # ========================================================
    print_section_header("2. COMPUTE METRICS")

    print_table(
        ["Metric", "Value"],
        [
            ["Total MACs", f"{stats['total_macs']:,}"],
            ["Total OPs", f"{stats['total_ops']:,}"],
            ["Compute Events", f"{stats['compute_events']:,}"],
        ],
        [30, 20],
        ["L", "R"]
    )

    # ========================================================
    # EXTERNAL MEMORY
    # ========================================================
    print_section_header("3. EXTERNAL MEMORY (DRAM)")

    print_table(
        ["Access Type", "Elements", "Bytes"],
        [
            ["Input Read", f"{stats['dram_read_input']:,}", f"{stats['dram_read_input'] * cfg['INPUT_BYTES']:,}"],
            ["Weight Read", f"{stats['dram_read_weight']:,}", f"{stats['dram_read_weight'] * cfg['WEIGHT_BYTES']:,}"],
            ["Output Write", f"{stats['dram_write_output']:,}", f"{stats['ddr_write_bytes']:,}"],
        ],
        [20, 18, 18],
        ["L", "R", "R"]
    )

    # ========================================================
    # MEMORY ACCESS (Gộp chung I, W, O)
    # ========================================================
    print_section_header("4. ON-CHIP MEMORY ACCESS")

    memory_rows = [
        ["I", 0, access["I"][0]["memory"], f"{access['I'][0]['rd_out_to_low']:,}", f"{access['I'][0]['wr_in_by_low']:,}", f"{access['I'][0]['rd_out_to_high']:,}", f"{access['I'][0]['wr_in_by_high']:,}"],
        ["W", 0, access["W"][0]["memory"], f"{access['W'][0]['rd_out_to_low']:,}", f"{access['W'][0]['wr_in_by_low']:,}", f"{access['W'][0]['rd_out_to_high']:,}", f"{access['W'][0]['wr_in_by_high']:,}"],
        ["O", 0, access["O"][0]["memory"], f"{access['O'][0]['rd_out_to_low']:,}", f"{access['O'][0]['wr_in_by_low']:,}", f"{access['O'][0]['rd_out_to_high']:,}", f"{access['O'][0]['wr_in_by_high']:,}"],
        ["O", 1, access["O"][1]["memory"], f"{access['O'][1]['rd_out_to_low']:,}", f"{access['O'][1]['wr_in_by_low']:,}", f"{access['O'][1]['rd_out_to_high']:,}", f"{access['O'][1]['wr_in_by_high']:,}"],
    ]

    print_table(
        ["Type", "Level", "Memory", "rd_out_to_low", "wr_in_by_low", "rd_out_to_high", "wr_in_by_high"],
        memory_rows,
        [6, 7, 8, 15, 15, 16, 16],
        ["L", "R", "L", "R", "R", "R", "R"]
    )

    # ========================================================
    # ELEMENT ACCESS
    # ========================================================
    print_section_header("5. ELEMENT ACCESS")

    print_table(
        ["Operand", "Memory", "Direction", "Elements"],
        [
            ["I", "L1", "L1 -> PE", f"{stats['l1_to_pe_input_reads']:,}"],
            ["W", "L1", "L1 -> PE", f"{stats['l1_to_pe_weight_reads']:,}"],
            ["O", "Reg_O", "L1 -> Reg_O", f"{stats['l1_to_reg_output_reads']:,}"],
            ["O", "Reg_O", "PE -> Reg_O", f"{stats['pe_to_reg_output_writes']:,}"],
            ["O", "L1", "Reg_O -> L1", f"{stats['reg_to_l1_output_writes']:,}"],
        ],
        [9, 8, 18, 18],
        ["L", "L", "L", "R"]
    )

    # ========================================================
    # MEMORY TRANSFER
    # ========================================================
    print_section_header("6. MEMORY TRANSFER")

    print_table(
        ["Operand", "Memory", "Transfer Width", "Elem / Transfer", "Read Transfers", "Write Transfers"],
        [
            ["I", "L1", f"{cfg['L1_INPUT_BW_BITS']} bit", cfg["L1_INPUT_ELEMENTS_PER_TRANSFER"], f"{access['I'][0]['rd_out_to_low']:,}", "0"],
            ["W", "L1", f"{cfg['L1_WEIGHT_BW_BITS']} bit", cfg["L1_WEIGHT_ELEMENTS_PER_TRANSFER"], f"{access['W'][0]['rd_out_to_low']:,}", "0"],
            ["O", "Reg_O", f"{cfg['ACC_BYTES'] * 8} bit", 1, f"{access['O'][0]['rd_out_to_low']:,}", f"{access['O'][0]['wr_in_by_low']:,}"],
            ["O", "L1", f"{cfg['L1_OUTPUT_BW_BITS']} bit", cfg["L1_OUTPUT_ELEMENTS_PER_TRANSFER"], f"{access['O'][1]['rd_out_to_low']:,}", f"{access['O'][1]['wr_in_by_low']:,}"],
        ],
        [8, 8, 15, 15, 15, 15],
        ["L", "L", "R", "R", "R", "R"]
    )

    

# ============================================================
# DEBUG ONE OUTPUT
# ============================================================

def debug_single_output(state, output_d0=0, output_d1=0):
    """
    Debug one output element:

        O[d0][d1]

    Show all 16 temporal D2 partial sums.
    """

    cfg = state["cfg"]

    print()
    print("=" * 60)
    print(f"DEBUG O[{output_d0}][{output_d1}]")
    print("=" * 60)

    result = 0

    for t2 in range(cfg["NUM_TEMPORAL_TILES_D2"]):

        start_d2 = (t2 * cfg["SPATIAL_TILE_D2"])

        end_d2 = (start_d2 + cfg["SPATIAL_TILE_D2"])

        spatial_psum = 0

        for d2 in range(start_d2,end_d2):

            x = state["l1_input"][output_d0][d2]

            w = state["l1_weight"][d2][output_d1]

            spatial_psum += (int(x) * int(w))

        previous = result
        result += spatial_psum

        print(
            f"t2={t2:2d} | "
            f"D2=[{start_d2:3d}:{end_d2:3d}) | "
            f"PSUM={spatial_psum:8d} | "
            f"Previous={previous:8d} | "
            f"Accumulated={result:8d}"
        )

    print("-" * 60)
    print(f"Final O[{output_d0}][{output_d1}] = {result}")


# ============================================================
# MAIN
# ============================================================
def main():
    directory = (r"C:\Source_Code\ZigZag\Gemm_RTL\Software")

    input_path = (directory + r"\input.hex")
    weight_path = (directory + r"\weight.hex")
    golden_path = (directory + r"\golden_output.hex")


    cfg = create_config(
        D0_SIZE=128,
        D1_SIZE=128,
        D2_SIZE=128,

        SPATIAL_TILE_D0=8,
        SPATIAL_TILE_D1=8,
        SPATIAL_TILE_D2=8,

        NUM_TEMPORAL_TILES_D0=16,
        NUM_TEMPORAL_TILES_D1=16,
        NUM_TEMPORAL_TILES_D2=16,
    )

    state = create_state(cfg)


    load_data_from_file(state, input_path, weight_path)


    print()
    print("\n" + "═" * 78)
    print(" START GEMM MAPPING HARDWARE SIMULATION ".center(78, "═"))
    print("═" * 78)   

    run_zigzag_mapping(state)

    check_golden(
        state,
        golden_path
    )

    report(state)
    #debug_single_output(state, 0, 0)


if __name__ == "__main__":
    main()

