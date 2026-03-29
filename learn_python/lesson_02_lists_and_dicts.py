# ============================================================
# LESSON 2: Lists and Dictionaries
# ============================================================
# Goal: Store many values together.
# In this repo: module configs, workload layers, hardware presets
# are all stored with these structures.
# ============================================================

# ============================================================
# PART A: LISTS
# ============================================================
# A list holds an ordered sequence of items.
# Defined with square brackets: [item1, item2, ...]

memory_levels = ["L1", "L2", "L3", "DRAM"]
bandwidths_gbps = [200, 50, 20, 2]

# --- Accessing items by position (index starts at 0) ---
print(memory_levels[0])   # "L1"
print(memory_levels[1])   # "L2"
print(memory_levels[-1])  # "DRAM"  (-1 = last item)

# --- Length of a list ---
print(f"Number of levels: {len(memory_levels)}")

# --- Looping through a list ---
for level in memory_levels:
    print(f"  Level: {level}")

# --- Loop with index using enumerate() ---
for i, level in enumerate(memory_levels):
    bw = bandwidths_gbps[i]
    print(f"  {level}: {bw} GB/s")

# --- Adding items ---
memory_levels.append("HBM")
bandwidths_gbps.append(3200)
print(f"After append: {memory_levels}")

# --- Removing items ---
memory_levels.remove("HBM")
print(f"After remove: {memory_levels}")

# --- Slicing: get a portion of a list ---
top_two = memory_levels[0:2]   # items at index 0 and 1
print(f"Top two: {top_two}")

# --- Check if something is in a list ---
if "DRAM" in memory_levels:
    print("DRAM is present")

# ============================================================
# PART B: DICTIONARIES
# ============================================================
# A dictionary maps a KEY to a VALUE.
# Defined with curly braces: {key: value, ...}
# Think of it like a lookup table.
# In this repo: hardware configs are stored as dictionaries.

gpu_config = {
    "name": "A100",
    "memory_gb": 80,
    "bandwidth_gbps": 2000,
    "frequency_ghz": 1.41,
    "num_cores": 6912,
    "supports_fp16": True,
}

# --- Accessing values by key ---
print(gpu_config["name"])
print(gpu_config["memory_gb"])

# --- Safer access with .get() (returns None if key missing) ---
tdp = gpu_config.get("tdp_watts", "unknown")
print(f"TDP: {tdp}")

# --- Adding or updating a key ---
gpu_config["tdp_watts"] = 400
print(f"TDP now: {gpu_config['tdp_watts']}")

# --- Looping through a dictionary ---
for key, value in gpu_config.items():
    print(f"  {key}: {value}")

# --- Checking if a key exists ---
if "bandwidth_gbps" in gpu_config:
    print(f"Bandwidth: {gpu_config['bandwidth_gbps']} GB/s")

# ============================================================
# PART C: LIST OF DICTIONARIES
# ============================================================
# This pattern is everywhere in the simulator:
# a list where each item is a dictionary describing one thing.

hardware_presets = [
    {"name": "A100", "memory_gb": 80,  "bandwidth_gbps": 2000},
    {"name": "H100", "memory_gb": 80,  "bandwidth_gbps": 3350},
    {"name": "V100", "memory_gb": 32,  "bandwidth_gbps": 900},
]

for hw in hardware_presets:
    print(f"{hw['name']}: {hw['memory_gb']}GB @ {hw['bandwidth_gbps']} GB/s")

# --- Find the one with most memory ---
best = max(hardware_presets, key=lambda hw: hw["memory_gb"])
print(f"Most memory: {best['name']}")

# ============================================================
# PART D: NESTED DICTIONARIES
# ============================================================
# Dictionaries can contain other dictionaries (like JSON configs).

dram_timing = {
    "DDR4": {"tCL": 16, "tRCD": 16, "tRP": 16, "tRAS": 39},
    "DDR5": {"tCL": 32, "tRCD": 32, "tRP": 32, "tRAS": 52},
}

gen = "DDR4"
print(f"{gen} tCL = {dram_timing[gen]['tCL']} cycles")

# --- EXERCISE ---
# Create a dictionary for an NPU with keys:
#   name, mac_units, on_chip_sram_mb, precision (a list: ["INT8","FP16","BF16"])
# Then:
#   1. Print each key-value pair.
#   2. Loop through the precision list and print each mode.

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - List  = ordered collection, use [ ]  access by index.
# - Dict  = key->value lookup,  use { }  access by key.
# - len() gives count; append() adds to list; key in dict checks existence.
# - Loop: for item in list  /  for key, value in dict.items()
# ============================================================
