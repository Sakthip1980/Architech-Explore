# ============================================================
# LESSON 5: Classes and Objects (Object-Oriented Programming)
# ============================================================
# Goal: Bundle data + behaviour into reusable blueprints.
# The ENTIRE simulator is built from classes:
#   Module, DRAM, GPU, NPU, SystolicArray, etc.
# ============================================================

# ============================================================
# PART A: YOUR FIRST CLASS
# ============================================================
# A class is a blueprint. An object is one instance of it.

class MemoryModule:
    """Represents a generic memory component."""

    # __init__ runs automatically when you create an object.
    # 'self' refers to the specific object being created.
    def __init__(self, name, capacity_gb, bandwidth_gbps, latency_ns):
        self.name          = name
        self.capacity_gb   = capacity_gb
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns    = latency_ns
        self.total_requests = 0         # internal counter, starts at 0

    # A method is a function that belongs to the class.
    def process_request(self, size_bytes):
        """Simulate one memory request. Return time taken in ns."""
        self.total_requests += 1
        transfer_time = (size_bytes / (self.bandwidth_gbps * 1e9)) * 1e9
        return self.latency_ns + transfer_time

    def utilisation(self, active_bw_gbps):
        """Return bandwidth utilisation as a fraction 0..1."""
        return min(active_bw_gbps / self.bandwidth_gbps, 1.0)

    def summary(self):
        """Print a short summary of this module."""
        print(f"[{self.name}] {self.capacity_gb} GB | "
              f"{self.bandwidth_gbps} GB/s | {self.latency_ns} ns | "
              f"requests served: {self.total_requests}")

# --- Creating objects from the class ---
dram = MemoryModule("DRAM", capacity_gb=32, bandwidth_gbps=51.2, latency_ns=80)
hbm  = MemoryModule("HBM2", capacity_gb=80, bandwidth_gbps=2000, latency_ns=10)

# --- Calling methods ---
t_dram = dram.process_request(size_bytes=4096)
t_hbm  = hbm.process_request(size_bytes=4096)
print(f"DRAM time for 4KB: {t_dram:.2f} ns")
print(f"HBM  time for 4KB: {t_hbm:.2f} ns")

dram.summary()
hbm.summary()

# ============================================================
# PART B: INHERITANCE — extend a class
# ============================================================
# A child class reuses everything from the parent and adds more.

class DRAMModule(MemoryModule):
    """DRAM with detailed timing and row-buffer awareness."""

    def __init__(self, name, capacity_gb, bandwidth_gbps, frequency_mhz,
                 tcl=16, trcd=16, trp=16):
        # Call parent __init__ first
        cycle_time_ns = 1000 / frequency_mhz
        base_latency  = (tcl + trcd) * cycle_time_ns
        super().__init__(name, capacity_gb, bandwidth_gbps, base_latency)

        # Extra attributes specific to DRAM
        self.frequency_mhz = frequency_mhz
        self.tcl  = tcl
        self.trcd = trcd
        self.trp  = trp
        self.row_buffer_hits  = 0
        self.row_buffer_misses = 0

    def process_request(self, size_bytes, row_hit=False):
        """Override parent: use row-hit or row-miss latency."""
        cycle_time_ns = 1000 / self.frequency_mhz
        if row_hit:
            self.row_buffer_hits += 1
            latency = self.tcl * cycle_time_ns
        else:
            self.row_buffer_misses += 1
            latency = (self.tcl + self.trcd) * cycle_time_ns
        transfer_time = (size_bytes / (self.bandwidth_gbps * 1e9)) * 1e9
        self.total_requests += 1
        return latency + transfer_time

    def hit_rate(self):
        total = self.row_buffer_hits + self.row_buffer_misses
        if total == 0:
            return 0.0
        return self.row_buffer_hits / total

ddr4 = DRAMModule("DDR4-3200", capacity_gb=32, bandwidth_gbps=51.2,
                  frequency_mhz=3200, tcl=16, trcd=16)

# Simulate 10 requests: mix of hits and misses
for i in range(10):
    hit = (i % 3 != 0)     # 2 out of 3 are hits
    ddr4.process_request(4096, row_hit=hit)

print(f"Row-buffer hit rate: {ddr4.hit_rate():.0%}")
ddr4.summary()

# ============================================================
# PART C: ABSTRACT BASE CLASS (how the simulator does it)
# ============================================================
# An abstract class defines an interface that all subclasses MUST implement.
# It prevents you from accidentally creating an incomplete module.

from abc import ABC, abstractmethod

class Module(ABC):
    """Abstract base for all hardware modules (mirrors simulator/base.py)."""

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def process_request(self, size_bytes):
        """Every subclass MUST implement this."""
        pass

    @abstractmethod
    def get_bandwidth(self):
        """Every subclass MUST implement this."""
        pass

    def describe(self):
        print(f"Module: {self.name}")

class SRAMCache(Module):
    """Simple SRAM cache module."""

    def __init__(self, name, size_mb, bandwidth_gbps, latency_ns, hit_rate=0.9):
        super().__init__(name)
        self.size_mb        = size_mb
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns     = latency_ns
        self.hit_rate       = hit_rate

    def process_request(self, size_bytes):
        import random
        if random.random() < self.hit_rate:
            return self.latency_ns              # cache hit
        return self.latency_ns * 10             # cache miss -> go to next level

    def get_bandwidth(self):
        return self.bandwidth_gbps

# Trying to instantiate the abstract Module directly would crash:
# m = Module("test")   # TypeError: Can't instantiate abstract class

l1 = SRAMCache("L1", size_mb=0.032, bandwidth_gbps=200, latency_ns=1)
l1.describe()
print(f"L1 bandwidth: {l1.get_bandwidth()} GB/s")

# ============================================================
# PART D: CLASS METHODS AS FACTORIES (preset configs)
# ============================================================
# @classmethod lets you create objects via named constructors.
# Used heavily in configs/hardware_presets.py.

class GPUConfig:
    def __init__(self, name, memory_gb, bandwidth_gbps, compute_tflops, tdp_w):
        self.name            = name
        self.memory_gb       = memory_gb
        self.bandwidth_gbps  = bandwidth_gbps
        self.compute_tflops  = compute_tflops
        self.tdp_w           = tdp_w

    @classmethod
    def a100_80gb(cls):
        """Factory: return a pre-configured A100 80GB object."""
        return cls("A100-80GB", memory_gb=80, bandwidth_gbps=2000,
                   compute_tflops=312, tdp_w=400)

    @classmethod
    def h100_sxm(cls):
        return cls("H100-SXM", memory_gb=80, bandwidth_gbps=3350,
                   compute_tflops=989, tdp_w=700)

    def roofline_intensity(self, flops, bytes_accessed):
        """Arithmetic intensity: flops per byte."""
        return flops / bytes_accessed

    def is_compute_bound(self, flops, bytes_accessed):
        intensity = self.roofline_intensity(flops, bytes_accessed)
        ridge_point = self.compute_tflops * 1e12 / (self.bandwidth_gbps * 1e9)
        return intensity > ridge_point

a100 = GPUConfig.a100_80gb()
h100 = GPUConfig.h100_sxm()

print(f"\n{a100.name}: {a100.compute_tflops} TFLOPS, {a100.bandwidth_gbps} GB/s")
print(f"{h100.name}: {h100.compute_tflops} TFLOPS, {h100.bandwidth_gbps} GB/s")

# GEMM is typically compute-bound on modern GPUs:
gemm_flops = 2 * 4096**3        # ~134 GFLOPS for 4096 GEMM
gemm_bytes = 3 * 4096**2 * 2    # three matrices, FP16
print(f"A100 GEMM compute-bound: {a100.is_compute_bound(gemm_flops, gemm_bytes)}")

# --- EXERCISE ---
# Create a class NetworkInterface with:
#   __init__(self, name, bandwidth_gbps, latency_us)
#   method: transfer_time_us(size_bytes) -> latency + transfer time in microseconds
#   classmethod: pcie_gen4() -> return PCIe Gen 4 (64 GB/s, 1 µs latency)
# Instantiate using the factory and print transfer time for 1 MB.

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - class Name:  defines a blueprint.
# - __init__(self, ...) initialises attributes when object is created.
# - self.attr = value stores per-object data.
# - Methods are functions that operate on self.
# - Inheritance: class Child(Parent) reuses and extends.
# - super().__init__() calls the parent constructor.
# - ABC + @abstractmethod enforces a required interface.
# - @classmethod creates named constructors / factory methods.
# ============================================================
