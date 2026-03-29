# ============================================================
# LESSON 3: Functions
# ============================================================
# Goal: Write reusable blocks of code.
# Every calculation in the simulator is wrapped in a function.
# ============================================================

# ============================================================
# PART A: DEFINING AND CALLING A FUNCTION
# ============================================================
# Syntax:
#   def function_name(parameter1, parameter2):
#       # indented body
#       return result

def calculate_bandwidth(data_bytes, time_ns):
    """Calculate bandwidth in GB/s given bytes moved and time in nanoseconds."""
    bandwidth_bps = data_bytes / (time_ns * 1e-9)   # bytes per second
    bandwidth_gbps = bandwidth_bps / 1e9              # convert to GB/s
    return bandwidth_gbps

# Call the function:
bw = calculate_bandwidth(data_bytes=1024, time_ns=10)
print(f"Bandwidth: {bw:.2f} GB/s")

# ============================================================
# PART B: DEFAULT PARAMETERS
# ============================================================
# Give a parameter a default value so it's optional when calling.

def dram_latency(frequency_mhz, tcl=16, trcd=16, trp=16):
    """Calculate DRAM row access latency in nanoseconds."""
    cycle_time_ns = 1000 / frequency_mhz   # one cycle duration
    latency_ns = (tcl + trcd + trp) * cycle_time_ns
    return latency_ns

# Using all defaults:
lat1 = dram_latency(frequency_mhz=3200)
print(f"DDR4-3200 latency: {lat1:.1f} ns")

# Overriding defaults for DDR5:
lat2 = dram_latency(frequency_mhz=4800, tcl=32, trcd=32, trp=32)
print(f"DDR5-4800 latency: {lat2:.1f} ns")

# ============================================================
# PART C: RETURNING MULTIPLE VALUES
# ============================================================
# Python can return several values at once as a tuple.

def compute_metrics(ops, time_ns, energy_pj):
    """Return throughput (TOPS) and efficiency (TOPS/W) together."""
    throughput_tops = ops / (time_ns * 1e-9) / 1e12
    power_w = energy_pj * 1e-12 / (time_ns * 1e-9)
    efficiency = throughput_tops / power_w if power_w > 0 else 0
    return throughput_tops, efficiency

tops, eff = compute_metrics(ops=312e12, time_ns=1e9, energy_pj=400e12)
print(f"Throughput: {tops:.1f} TOPS")
print(f"Efficiency: {eff:.2f} TOPS/W")

# ============================================================
# PART D: FUNCTIONS THAT CALL OTHER FUNCTIONS
# ============================================================
# Build complex logic by composing simple functions.

def cycles_to_ns(cycles, frequency_mhz):
    return cycles * (1000 / frequency_mhz)

def memory_access_latency(row_hit, frequency_mhz, tcl=16, trcd=16):
    """Return latency for a DRAM access depending on row-buffer hit or miss."""
    if row_hit:
        cycles = tcl                    # only CAS latency needed
    else:
        cycles = tcl + trcd             # must also activate the row
    return cycles_to_ns(cycles, frequency_mhz)

print(f"Row hit   latency: {memory_access_latency(True,  3200):.1f} ns")
print(f"Row miss  latency: {memory_access_latency(False, 3200):.1f} ns")

# ============================================================
# PART E: DOCSTRINGS
# ============================================================
# The text in triple quotes right after def is a docstring.
# It documents what the function does. Always write them!
# You can read them with help():

help(calculate_bandwidth)

# ============================================================
# PART F: SAFE TYPE CONVERSION (used in simulator_api.py)
# ============================================================
# When reading values from user input or JSON, they might be
# strings. These helper functions convert safely with a fallback.

def safe_int(value, default=0):
    """Convert value to int; return default if conversion fails."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """Convert value to float; return default if conversion fails."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

print(safe_int("6912"))          # 6912
print(safe_int("bad_input"))     # 0
print(safe_float("1.41"))        # 1.41
print(safe_float(None, 1.0))     # 1.0

# ============================================================
# PART G: SCOPE (where variables live)
# ============================================================
# Variables created inside a function only exist inside it.

def show_scope():
    local_var = "I only exist inside this function"
    print(local_var)

show_scope()
# print(local_var)   # This would crash - local_var doesn't exist here

# --- EXERCISE ---
# Write a function called peak_memory_bandwidth that:
#   - Takes: channels (int), bus_width_bits (int), frequency_mhz (float)
#   - Calculates: bandwidth_gbps = channels * (bus_width_bits / 8) * frequency_mhz * 2 / 1000
#   - Returns bandwidth_gbps
#   - Has a docstring
# Test it with DDR4: channels=2, bus_width_bits=64, frequency_mhz=3200

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - def name(params): ... return value   defines a function.
# - Default params make arguments optional.
# - return a, b  returns multiple values (unpack with a, b = ...).
# - Compose small functions into larger ones.
# - try/except handles errors gracefully (lesson 6 has more).
# ============================================================
