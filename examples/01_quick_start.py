"""
Example 1 — Quick Start
=======================
Define a hardware block, load a workload, simulate it, print the results.
Run from the repo root:
    python examples/01_quick_start.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 1. Define the hardware ────────────────────────────────────────────────────
from simulator.hardware import block_from_module
from simulator.models.npu import NPU

# Create an NPU with specific parameters.
# block_from_module() reads these parameters and builds a self-consistent
# property block (bandwidth, power, frequency all derived together).
npu = NPU(
    name               = 'MyNPU',
    mac_units          = 1024,          # multiply-accumulate units
    frequency_ghz      = 1.0,           # clock frequency
    precision          = 'INT8',        # data type
    on_chip_sram_mb    = 32,            # on-chip scratchpad
    memory_bandwidth_gbps = 256,        # off-chip memory bandwidth
    tdp_watts          = 15,            # thermal design power
)
hw = block_from_module(npu)

print("=== Hardware Block ===")
print(f"  Frequency : {hw.get_property('frequency') / 1e9:.1f} GHz")
print(f"  Bandwidth : {hw.get_property('BW') / 1e9:.0f} GB/s")
print(f"  Power     : {hw.get_property('P_total'):.0f} W")
print()

# ── 2. Load a workload ───────────────────────────────────────────────────────
from simulator.workload import OpGraph
from simulator.models.workload import get_resnet50_workload

graph = OpGraph.from_workload(get_resnet50_workload())

print("=== Workload: ResNet-50 ===")
print(f"  Ops       : {len(graph)}")
print(f"  FLOPs     : {graph.total_flops() / 1e9:.2f} GFLOPs")
print(f"  Memory    : {graph.total_read_bytes() / 1e6:.1f} MB read  "
      f"/ {graph.total_write_bytes() / 1e6:.1f} MB write")
print()

# ── 3. Simulate ──────────────────────────────────────────────────────────────
from simulator.engine import AnalyticalEngine

result = AnalyticalEngine(dtype_bytes=1).run(graph, hw)   # INT8 = 1 byte/element

print("=== Simulation Result ===")
print(f"  Total cycles  : {result.total_cycles:,.0f}")
print(f"  Wall time     : {result.wall_time_s * 1000:.2f} ms")
print(f"  Bottleneck    : {result.system_bottleneck}")
print(f"  Total energy  : {result.total_energy_joules:.4f} J")
print()

# ── 4. Per-op breakdown (top 5 slowest ops) ──────────────────────────────────
print("=== Top 5 Slowest Ops ===")
sorted_ops = sorted(result.per_op, key=lambda r: r.latency_cycles, reverse=True)
for r in sorted_ops[:5]:
    print(f"  {r.name:<35}  "
          f"{r.latency_cycles:>12,.0f} cycles  "
          f"AI={r.roofline.arithmetic_intensity:>6.1f}  "
          f"{r.roofline.bottleneck}")
