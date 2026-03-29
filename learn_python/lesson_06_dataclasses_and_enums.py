# ============================================================
# LESSON 6: Dataclasses and Enums
# ============================================================
# Goal: Write cleaner data containers and fixed choice sets.
# simulator/base.py uses @dataclass for SimulationMetrics.
# simulator/models/ use Enum for DataflowMode, PrecisionMode, etc.
# ============================================================

# ============================================================
# PART A: DATACLASS — automatic __init__, __repr__, etc.
# ============================================================
# A dataclass is a regular class but Python auto-generates:
#   - __init__  (constructor)
#   - __repr__  (nice print output)
#   - __eq__    (equality comparison)
# You just declare fields with type hints.

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SimulationMetrics:
    """Results produced by one simulation run (mirrors simulator/base.py)."""
    latency_ns:        float = 0.0
    bandwidth_gbps:    float = 0.0
    power_watts:       float = 0.0
    throughput_tops:   float = 0.0
    memory_util:       float = 0.0
    compute_util:      float = 0.0

# Create an instance — no need to write __init__:
metrics = SimulationMetrics(
    latency_ns=80.0,
    bandwidth_gbps=2000.0,
    power_watts=400.0,
    throughput_tops=312.0,
    memory_util=0.75,
    compute_util=0.92,
)

print(metrics)               # readable output automatically
print(f"Latency: {metrics.latency_ns} ns")
print(f"Compute util: {metrics.compute_util:.0%}")

# --- Modifying fields ---
metrics.power_watts = 380.0
print(f"Updated power: {metrics.power_watts} W")

# ============================================================
# PART B: DATACLASS WITH DEFAULT FACTORY
# ============================================================
# For mutable defaults (lists, dicts) use field(default_factory=...)

@dataclass
class WorkloadLayer:
    """One layer in a neural network workload."""
    name:        str
    op_type:     str          # "gemm", "conv", "attention"
    M:           int = 1
    K:           int = 1
    N:           int = 1
    batch_size:  int = 1

    def flops(self):
        """Compute total floating-point operations for this GEMM layer."""
        return 2 * self.M * self.K * self.N * self.batch_size

    def arithmetic_intensity(self):
        """Flops / bytes assuming FP16 (2 bytes per element)."""
        total_flops = self.flops()
        bytes_accessed = 2 * (self.M * self.K + self.K * self.N + self.M * self.N)
        return total_flops / bytes_accessed

@dataclass
class Workload:
    """A collection of layers representing one model's workload."""
    name:   str
    layers: List[WorkloadLayer] = field(default_factory=list)

    def add_layer(self, layer: WorkloadLayer):
        self.layers.append(layer)

    def total_flops(self):
        return sum(l.flops() for l in self.layers)

    def summary(self):
        print(f"\nWorkload: {self.name}  ({len(self.layers)} layers)")
        for layer in self.layers:
            print(f"  {layer.name:20s} | {layer.op_type:10s} | "
                  f"{layer.flops()/1e9:.1f} GFLOPs | "
                  f"AI={layer.arithmetic_intensity():.1f}")
        print(f"  {'TOTAL':20s} | {'':10s} | {self.total_flops()/1e9:.1f} GFLOPs")

# Build a simple transformer workload:
llama_7b = Workload("Llama-7B-forward")
llama_7b.add_layer(WorkloadLayer("attn_qkv",   "gemm", M=2048, K=4096,  N=3*4096))
llama_7b.add_layer(WorkloadLayer("attn_proj",  "gemm", M=2048, K=4096,  N=4096))
llama_7b.add_layer(WorkloadLayer("ffn_gate",   "gemm", M=2048, K=4096,  N=11008))
llama_7b.add_layer(WorkloadLayer("ffn_down",   "gemm", M=2048, K=11008, N=4096))
llama_7b.summary()

# ============================================================
# PART C: ENUM — fixed set of named choices
# ============================================================
# Use an Enum when a variable can only be one of a fixed list.
# This prevents typos like "wight_stationary" from silently passing.

from enum import Enum

class DataflowMode(Enum):
    WEIGHT_STATIONARY  = "ws"    # weights stay in the array, inputs stream
    OUTPUT_STATIONARY  = "os"    # partial sums stay, inputs/weights stream
    INPUT_STATIONARY   = "is"    # inputs stay, weights stream

class PrecisionMode(Enum):
    FP32  = 32
    FP16  = 16
    BF16  = 16
    INT8  = 8
    FP8   = 8

# --- Using enums ---
mode = DataflowMode.WEIGHT_STATIONARY
print(f"Dataflow: {mode}")
print(f"Dataflow name:  {mode.name}")
print(f"Dataflow value: {mode.value}")

precision = PrecisionMode.BF16
print(f"Bytes per element: {precision.value // 8}")

# --- Switch-like dispatch with enums ---
def peak_compute_scaling(precision: PrecisionMode, fp32_tflops: float) -> float:
    """Return peak compute TFLOPS scaled for the given precision."""
    if precision == PrecisionMode.FP32:
        return fp32_tflops
    elif precision in (PrecisionMode.FP16, PrecisionMode.BF16):
        return fp32_tflops * 2
    elif precision in (PrecisionMode.INT8, PrecisionMode.FP8):
        return fp32_tflops * 4
    return fp32_tflops

a100_fp32_tflops = 19.5
for prec in PrecisionMode:
    scaled = peak_compute_scaling(prec, a100_fp32_tflops)
    print(f"  A100 {prec.name:5s}: {scaled:.1f} TFLOPS")

# ============================================================
# PART D: Optional type hint
# ============================================================
# Optional[X] means the value can be X or None.

@dataclass
class HardwareConfig:
    name:           str
    compute_tflops: float
    memory_gb:      int
    # Optional fields — may or may not be provided:
    model_preset:   Optional[str]  = None
    notes:          Optional[str]  = None

cfg = HardwareConfig("H100", compute_tflops=989, memory_gb=80)
print(cfg)

cfg2 = HardwareConfig("A100", compute_tflops=312, memory_gb=80,
                       model_preset="Llama-7B", notes="baseline run")
print(cfg2)

# --- EXERCISE ---
# 1. Create an Enum called MemoryType with values: SRAM, DRAM, HBM, NVM
# 2. Create a @dataclass called MemorySpec with fields:
#       mem_type: MemoryType
#       capacity_gb: int
#       bandwidth_gbps: float
#       latency_ns: float
# 3. Instantiate one for HBM3 (80 GB, 3200 GB/s, 8 ns) and print it.

# YOUR CODE HERE:


# ============================================================
# KEY TAKEAWAYS
# ============================================================
# - @dataclass auto-generates __init__, __repr__, __eq__.
# - Declare fields as: name: type = default_value
# - field(default_factory=list) for mutable defaults.
# - Enum gives named constants that are type-safe and readable.
# - Optional[T] means a field can be T or None.
# ============================================================
