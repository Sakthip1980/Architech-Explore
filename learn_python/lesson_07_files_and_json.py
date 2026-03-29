# ============================================================
# LESSON 7: File I/O and JSON
# ============================================================
# Goal: Read and write data to disk.
# The simulator saves/loads state as JSON and reads CSV workloads.
# ============================================================

import json
import csv
import os

# ============================================================
# PART A: WRITING AND READING TEXT FILES
# ============================================================

# --- Writing a file ---
# 'w' = write mode (creates or overwrites)
with open("/tmp/simulation_log.txt", "w") as f:
    f.write("Simulation started\n")
    f.write("Loading hardware config: A100\n")
    f.write("Workload: Llama-7B\n")

# The 'with' block closes the file automatically when done.

# --- Reading a file ---
with open("/tmp/simulation_log.txt", "r") as f:
    contents = f.read()        # entire file as one string

print(contents)

# --- Reading line by line ---
with open("/tmp/simulation_log.txt", "r") as f:
    for line in f:
        print(f"  Line: {line.rstrip()}")   # rstrip() removes trailing newline

# --- Appending to a file ---
# 'a' = append mode (adds to end, doesn't overwrite)
with open("/tmp/simulation_log.txt", "a") as f:
    f.write("Simulation completed\n")

# ============================================================
# PART B: JSON — the simulator's main data format
# ============================================================
# JSON looks like Python dicts and lists. It's the standard
# format for saving configs and transferring data between
# the frontend (JavaScript) and backend (Python).

# --- dict -> JSON string ---
config = {
    "name": "A100",
    "memory_gb": 80,
    "bandwidth_gbps": 2000,
    "supported_precisions": ["FP32", "FP16", "BF16", "INT8"],
    "memory_hierarchy": {
        "L1_cache_kb": 192,
        "L2_cache_mb": 40,
        "HBM_gb": 80,
    }
}

json_string = json.dumps(config, indent=2)   # indent=2 for pretty print
print(json_string)

# --- JSON string -> dict ---
parsed = json.loads(json_string)
print(f"Name: {parsed['name']}")
print(f"L2 cache: {parsed['memory_hierarchy']['L2_cache_mb']} MB")

# --- Save dict to a .json file ---
with open("/tmp/hardware_config.json", "w") as f:
    json.dump(config, f, indent=2)

# --- Load dict from a .json file ---
with open("/tmp/hardware_config.json", "r") as f:
    loaded_config = json.load(f)

print(f"Loaded: {loaded_config['name']}")

# --- Handling missing file gracefully ---
def load_config(filepath, default=None):
    """Load a JSON config file; return default if file doesn't exist."""
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}, using default.")
        return default or {}
    with open(filepath, "r") as f:
        return json.load(f)

cfg = load_config("/tmp/hardware_config.json")
cfg_missing = load_config("/tmp/does_not_exist.json", default={"name": "unknown"})
print(f"Loaded name: {cfg.get('name')}")
print(f"Missing cfg: {cfg_missing}")

# ============================================================
# PART C: CSV — reading workload layer files
# ============================================================
# simulator/models/workload.py reads CSV files like this.

# --- Write a sample CSV ---
workload_rows = [
    ["layer_name", "op_type", "M", "K", "N"],
    ["attn_qkv",   "gemm",    2048, 4096, 12288],
    ["attn_proj",  "gemm",    2048, 4096,  4096],
    ["ffn_gate",   "gemm",    2048, 4096, 11008],
    ["ffn_down",   "gemm",    2048, 11008, 4096],
]

with open("/tmp/workload.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(workload_rows)

# --- Read CSV into list of dicts ---
layers = []
with open("/tmp/workload.csv", "r") as f:
    reader = csv.DictReader(f)   # first row becomes the dict keys
    for row in reader:
        layers.append({
            "name":    row["layer_name"],
            "op_type": row["op_type"],
            "M":       int(row["M"]),
            "K":       int(row["K"]),
            "N":       int(row["N"]),
        })

print(f"\nLoaded {len(layers)} layers from CSV:")
for layer in layers:
    flops = 2 * layer["M"] * layer["K"] * layer["N"]
    print(f"  {layer['name']:15s}  {flops/1e9:.1f} GFLOPs")

# ============================================================
# PART D: SIMULATING THE SIMULATOR STATE FILE PATTERN
# ============================================================
# simulator_api.py saves graph state to .simulator_state.json
# Here is how that pattern works:

STATE_FILE = "/tmp/.simulator_state.json"

def save_state(modules, connections):
    state = {
        "modules":     modules,
        "connections": connections,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"State saved to {STATE_FILE}")

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"modules": [], "connections": []}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

# Simulate a frontend graph:
modules = [
    {"id": "gpu0", "type": "GPU",  "params": {"memory_gb": 80}},
    {"id": "hbm0", "type": "HBM",  "params": {"capacity_gb": 80}},
]
connections = [
    {"source": "gpu0", "target": "hbm0"},
]

save_state(modules, connections)
state = load_state()
print(f"Loaded modules: {[m['id'] for m in state['modules']]}")

# ============================================================
# PART E: WORKING WITH FILE PATHS
# ============================================================

# os.path — cross-platform path manipulation
base_dir = "/tmp/sim_results"
os.makedirs(base_dir, exist_ok=True)    # create directory, no error if exists

result_path = os.path.join(base_dir, "run_001.json")
print(f"Result path: {result_path}")

# Check existence:
print(f"Exists: {os.path.exists(result_path)}")

# --- EXERCISE ---
# 1. Create a dict describing a simulation run:
#       run_id, hardware, workload, metrics (a nested dict with latency_ns, bandwidth_gbps)
# 2. Save it to /tmp/run_001.json using json.dump
# 3. Load it back and print the latency_ns from metrics.

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - open(path, mode) + with block = safe file I/O.
# - Modes: "r" read, "w" write, "a" append.
# - json.dumps / json.loads  : dict <-> string.
# - json.dump  / json.load   : dict <-> file.
# - csv.DictReader turns each CSV row into a dict.
# - os.path.exists, os.path.join, os.makedirs for paths.
# ============================================================
