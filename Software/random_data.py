import random
import numpy as np

D0 = 128      
D1 = 128       
D2 = 128       

RANDOM_SEED = 42

OUTPUT_DIR = r"C:\Source_Code\ZigZag\Gemm_RTL\Software"

INPUT_FILE = OUTPUT_DIR + r"\input.hex"
WEIGHT_FILE = OUTPUT_DIR + r"\weight.hex"
GOLDEN_FILE = OUTPUT_DIR + r"\golden_output.hex"


# ============================================================
# 1. GENERATE TEST DATA
# ============================================================

def generate_test_data():
    """
    Generate:
        input.hex
        weight.hex
        bias.hex

    Data format:
        Input  : INT8  -> 1 byte / element
        Weight : INT8  -> 1 byte / element
        Bias   : INT32 -> 4 bytes / element, little-endian

    Mathematical shapes:

        X    = [D0][D2]
        W    = [D2][D1]
    """

    random.seed(RANDOM_SEED)

    input_data = [
        random.randint(-128, 127)
        for _ in range(D0 * D2)
    ]

    weight_data = [
        random.randint(-128, 127)
        for _ in range(D2 * D1)
    ]

    with open(INPUT_FILE, "w") as f:
        for value in input_data:
            value_u8 = value & 0xFF
            f.write(f"{value_u8:02x}\n")

    with open(WEIGHT_FILE, "w") as f:
        for value in weight_data:
            value_u8 = value & 0xFF
            f.write(f"{value_u8:02x}\n")

    print("========================================")
    print("TEST DATA GENERATED")
    print("========================================")

    print(f"D0 = {D0}")
    print(f"D1 = {D1}")
    print(f"D2 = {D2}")
    print(f"Random seed = {RANDOM_SEED}")

    print()
    print(f"Input elements  : {len(input_data)}")
    print(f"Weight elements : {len(weight_data)}")

    print()
    print(f"Input file  : {INPUT_FILE}")
    print(f"Weight file : {WEIGHT_FILE}")

    print()
    print("Input:")
    print(np.array(input_data).reshape(D0, D2))

    print()
    print("Weight:")
    print(np.array(weight_data).reshape(D2, D1))

    print("========================================")


# ============================================================
# 2. READ INT8 HEX
# ============================================================

def read_int8_hex(filename):
    """
    Read a hex file where each line contains 1 byte.

    Convert unsigned byte [0, 255]
    into signed INT8 [-128, 127].
    """

    data = []

    with open(filename, "r") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            value = int(line, 16)

            # Convert 8-bit two's complement
            if value >= 128:
                value -= 256

            data.append(value)

    return data


# ============================================================
# 3. GENERATE GOLDEN OUTPUT
# ============================================================

def generate_golden_output():
    """
    Generate golden output using the mathematical GEMM:

        O[d0][d1] = sum_n X[d0][d2] * W[d2][d1]

    Shapes:

        X    = [d0][d2]
        W    = [d2][d1]
        O    = [d0][d1]

    Input/Weight:
        INT8

    Accumulation:
        INT32

    Output:
        INT32
    """

    input_data = read_int8_hex(INPUT_FILE)
    weight_data = read_int8_hex(WEIGHT_FILE)


    assert len(input_data) == D0 * D2, (
        f"Input size mismatch: "
        f"expected {D0 * D2}, got {len(input_data)}"
    )

    assert len(weight_data) == D2 * D1, (
        f"Weight size mismatch: "
        f"expected {D2 * D1}, got {len(weight_data)}"
    )


    X = np.array(
        input_data,
        dtype=np.int32
    ).reshape(D0, D2)

    W = np.array(
        weight_data,
        dtype=np.int32
    ).reshape(D2, D1)


    Y = X @ W

    print()
    print("========================================")
    print("GOLDEN OUTPUT")
    print("========================================")

    print("X:")
    print(X)

    print()
    print("W:")
    print(W)

    print()
    print("Y = X @ W:")
    print(Y)


    with open(GOLDEN_FILE, "w") as f:

        for value in Y.flatten():

            value_u32 = int(value) & 0xFFFFFFFF

            f.write(f"{value_u32:08x}\n")

    print()
    print(f"Golden output file: {GOLDEN_FILE}")
    print(f"Golden output shape: {Y.shape}")

    print("========================================")


def compare_output(simulator_output, golden_output):
    if len(simulator_output) != len(golden_output):

        print("ERROR: Output size mismatch!")
        print(f"Simulator : {len(simulator_output)}")
        print(f"Golden    : {len(golden_output)}")

        return False

    correct = True

    for i, (sim, golden) in enumerate(
        zip(simulator_output, golden_output)
    ):

        if sim != golden:

            print(
                f"Mismatch at index {i}: "
                f"simulator={sim}, golden={golden}"
            )

            correct = False

    if correct:
        print("PASS: Simulator output == Golden output")
    else:
        print("FAIL: Simulator output != Golden output")

    return correct



if __name__ == "__main__":
    generate_test_data()

    generate_golden_output()