# ============================================================
# LESSON 4: Control Flow (if / elif / else / for / while)
# ============================================================
# Goal: Make decisions and repeat actions in your code.
# Simulators are full of decision points and loops.
# ============================================================

# ============================================================
# PART A: IF / ELIF / ELSE
# ============================================================
# Python uses indentation (4 spaces) to define blocks.

def classify_latency(latency_ns):
    """Categorise a memory latency value."""
    if latency_ns < 10:
        return "ultra-low (on-chip cache)"
    elif latency_ns < 100:
        return "low (SRAM / HBM)"
    elif latency_ns < 500:
        return "medium (DDR DRAM)"
    else:
        return "high (NVM / SSD)"

print(classify_latency(5))
print(classify_latency(80))
print(classify_latency(300))
print(classify_latency(10000))

# --- Comparison operators ---
# ==  equal          !=  not equal
# >   greater than   <   less than
# >=  >=             <=  <=

# --- Boolean operators ---
# and   both must be True
# or    at least one must be True
# not   flips True/False

bandwidth_gbps = 2000
frequency_ghz = 1.41

if bandwidth_gbps > 1000 and frequency_ghz > 1.0:
    print("High-performance GPU")

# ============================================================
# PART B: FOR LOOPS
# ============================================================

# --- Loop over a list ---
layers = ["embed", "attn", "ffn", "norm", "lm_head"]
for layer in layers:
    print(f"  Processing layer: {layer}")

# --- range(): generate numbers ---
# range(n)       -> 0, 1, 2, ..., n-1
# range(a, b)    -> a, a+1, ..., b-1
# range(a, b, s) -> a, a+s, a+2s, ... < b

print("Tile sizes:")
for tile_size in range(8, 65, 8):    # 8, 16, 24, 32, 40, 48, 56, 64
    print(f"  {tile_size}x{tile_size}")

# --- Loop with enumerate (index + value together) ---
memory_levels = ["L1_cache", "L2_cache", "DRAM", "NVM"]
latencies_ns  = [1, 5, 80, 500]

for idx, level in enumerate(memory_levels):
    print(f"  Level {idx}: {level} = {latencies_ns[idx]} ns")

# --- Loop over dictionary items ---
gpu_config = {"name": "A100", "cores": 6912, "memory_gb": 80}
for key, value in gpu_config.items():
    print(f"  {key}: {value}")

# --- zip(): loop two lists together ---
for level, latency in zip(memory_levels, latencies_ns):
    print(f"  {level}: {latency} ns")

# ============================================================
# PART C: WHILE LOOPS
# ============================================================
# Keep looping as long as a condition is True.
# Used in simulators for cycle-by-cycle execution.

def simulate_drain(queue_size, drain_rate_per_cycle):
    """Simulate draining a request queue over cycles."""
    cycle = 0
    remaining = queue_size
    while remaining > 0:
        drained = min(drain_rate_per_cycle, remaining)
        remaining -= drained
        cycle += 1
        if cycle <= 3 or remaining == 0:   # print first 3 + final
            print(f"  Cycle {cycle}: {remaining} requests remaining")
    return cycle

total_cycles = simulate_drain(queue_size=20, drain_rate_per_cycle=4)
print(f"Queue drained in {total_cycles} cycles")

# ============================================================
# PART D: break AND continue
# ============================================================

# break: exit the loop immediately
bandwidths = [200, 50, 20, 2, 0.5]
for bw in bandwidths:
    if bw < 1:
        print(f"  Skipping very slow link ({bw} GB/s)")
        break           # stop as soon as we hit something < 1 GB/s
    print(f"  Usable bandwidth: {bw} GB/s")

# continue: skip the rest of this iteration, go to next
print("Non-zero bandwidths:")
for bw in bandwidths:
    if bw == 0:
        continue        # skip zeros
    print(f"  {bw}")

# ============================================================
# PART E: LIST COMPREHENSION (compact loop to build a list)
# ============================================================
# result = [expression for item in iterable if condition]

raw_sizes = ["8", "16", "32", "bad", "64"]

# Long form:
valid_sizes = []
for s in raw_sizes:
    try:
        valid_sizes.append(int(s))
    except ValueError:
        pass

# Short form (list comprehension):
valid_sizes2 = [int(s) for s in raw_sizes if s.isdigit()]

print(f"Valid tile sizes: {valid_sizes2}")

# Double each valid size:
doubled = [s * 2 for s in valid_sizes2]
print(f"Doubled: {doubled}")

# ============================================================
# PART F: REAL SIMULATOR EXAMPLE — bottleneck detection
# ============================================================

def detect_bottleneck(compute_util, memory_util):
    """Identify the system bottleneck from utilisation percentages."""
    THRESHOLD = 0.85   # 85 %

    if compute_util >= THRESHOLD and memory_util >= THRESHOLD:
        return "BOTH: roofline boundary"
    elif compute_util >= THRESHOLD:
        return "COMPUTE-bound"
    elif memory_util >= THRESHOLD:
        return "MEMORY-bound"
    else:
        return "UNDERUTILISED"

workloads = [
    {"name": "GEMM 4096",    "compute": 0.92, "memory": 0.55},
    {"name": "AllReduce",    "compute": 0.30, "memory": 0.91},
    {"name": "Embedding",    "compute": 0.20, "memory": 0.40},
    {"name": "Transformer",  "compute": 0.88, "memory": 0.87},
]

for wl in workloads:
    bottleneck = detect_bottleneck(wl["compute"], wl["memory"])
    print(f"  {wl['name']:15s} -> {bottleneck}")

# --- EXERCISE ---
# Write a function find_fastest_memory(levels) that:
#   - Takes a list of dicts, each with keys "name" and "latency_ns"
#   - Loops through them and returns the dict with the smallest latency_ns

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - if / elif / else : make decisions based on conditions.
# - for item in iterable : iterate over any sequence.
# - range(start, stop, step) : generate integer sequences.
# - while condition : loop until condition is False.
# - break / continue : exit or skip inside a loop.
# - [expr for x in list if cond] : concise list building.
# ============================================================
