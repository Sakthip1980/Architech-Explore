# ============================================================
# LESSON 1: Variables and Data Types
# ============================================================
# Goal: Understand how Python stores and names data.
# This is the foundation of every tool in this repo.
# ============================================================

# --- 1. Variables ---
# A variable is a name that holds a value.
# You create one by writing:  name = value

chip_name = "A100"          # text  (called a "string", or str)
num_cores = 6912            # whole number (called "integer", or int)
frequency_ghz = 1.41        # decimal number (called "float")
is_active = True            # True or False  (called "boolean", or bool)

# --- 2. Print ---
# print() shows a value on screen. You will use this constantly.
print(chip_name)
print(num_cores)
print(frequency_ghz)
print(is_active)

# --- 3. f-strings: putting variables inside text ---
# Put f before the quote, then use { } to embed a variable.
print(f"Chip: {chip_name}")
print(f"Cores: {num_cores}")
print(f"Frequency: {frequency_ghz} GHz")

# --- 4. Basic arithmetic ---
bandwidth_gbps = 2000        # GB/s
bytes_per_transfer = 4       # bytes
total_bytes = bandwidth_gbps * bytes_per_transfer
print(f"Total bytes: {total_bytes}")

latency_ns = 80.0
latency_us = latency_ns / 1000      # divide
print(f"Latency: {latency_us} microseconds")

power_w = 400
voltage = 0.9
current = power_w / voltage          # division gives a float
print(f"Current: {current:.2f} A")   # :.2f means 2 decimal places

# --- 5. Changing a variable ---
temperature = 60
print(f"Temperature before: {temperature}")
temperature = temperature + 10       # add 10 and save back
print(f"Temperature after:  {temperature}")

# Shortcut for the same thing:
temperature += 5
print(f"Temperature after +=: {temperature}")

# --- 6. Type checking ---
# You can always ask Python what type a variable is.
print(type(chip_name))       # <class 'str'>
print(type(num_cores))       # <class 'int'>
print(type(frequency_ghz))   # <class 'float'>
print(type(is_active))       # <class 'bool'>

# --- EXERCISE ---
# Create variables for a GPU:
#   name = "H100"
#   memory_gb = 80
#   bandwidth_tbps = 3.35
#   supports_fp8 = True
# Then print a sentence for each using an f-string.

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - Variables store data; name = value creates one.
# - Main types: str (text), int (whole), float (decimal), bool (True/False).
# - print() shows output; f"text {var}" embeds variables in text.
# - Arithmetic: +  -  *  /  (division always gives float)
# ============================================================
