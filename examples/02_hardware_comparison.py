"""
Example 2 — Hardware Comparison
================================
Simulate the same workloads on three different hardware configurations
and print a side-by-side comparison table.

Run from the repo root:
    python examples/02_hardware_comparison.py

Configs compared
----------------
  1. Edge NPU     — low-power device (mobile / IoT)
  2. Cloud NPU    — high-end datacenter accelerator
  3. Systolic Array — classic weight-stationary matrix engine

Workloads
---------
  - ResNet-50   (image classification, compute-heavy convolutions)
  - GPT-2       (transformer inference, large matrix multiplies)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.hardware import ComputeBlock, block_from_module
from simulator.models.npu import NPU
from simulator.models.systolic_array import SystolicArray
from simulator.workload import OpGraph
from simulator.models.workload import get_resnet50_workload, get_gpt2_workload
from simulator.engine import AnalyticalEngine


# ── 1. Define hardware configurations ────────────────────────────────────────

configs = {
    'Edge NPU (INT8, 15W)': block_from_module(NPU(
        name='EdgeNPU',
        mac_units=512,
        frequency_ghz=0.5,
        precision='INT8',
        on_chip_sram_mb=4,
        memory_bandwidth_gbps=32,
        tdp_watts=15,
    )),

    'Cloud NPU (FP16, 300W)': block_from_module(NPU(
        name='CloudNPU',
        mac_units=4096,
        frequency_ghz=1.5,
        precision='FP16',
        on_chip_sram_mb=128,
        memory_bandwidth_gbps=900,
        tdp_watts=300,
    )),

    'Systolic 256x256 (FP16, 200W)': block_from_module(SystolicArray(
        name='SA256',
        array_height=256,
        array_width=256,
        frequency_ghz=1.0,
        dataflow='ws',
        tdp_watts=200,
    )),
}

# ── 2. Define workloads ───────────────────────────────────────────────────────

workloads = {
    'ResNet-50  (1.55 GFLOPs)': (OpGraph.from_workload(get_resnet50_workload()), 1),
    'GPT-2     (136  GFLOPs)': (OpGraph.from_workload(get_gpt2_workload()),     2),
}

# ── 3. Run simulation for every (workload × config) combination ───────────────

engine = AnalyticalEngine()

results = {}   # (workload_name, config_name) → AnalyticalResult
for wl_name, (graph, dtype_bytes) in workloads.items():
    for cfg_name, hw in configs.items():
        r = AnalyticalEngine(dtype_bytes=dtype_bytes).run(graph, hw)
        results[(wl_name, cfg_name)] = r

# ── 4. Print comparison table ─────────────────────────────────────────────────

COL_W = 38   # config column width

for wl_name, (graph, _) in workloads.items():
    print(f"\n{'='*90}")
    print(f"  Workload: {wl_name}")
    print(f"{'='*90}")
    print(f"  {'Metric':<22}", end='')
    for cfg_name in configs:
        print(f"  {cfg_name:<{COL_W}}", end='')
    print()
    print(f"  {'-'*22}", end='')
    for _ in configs:
        print(f"  {'-'*COL_W}", end='')
    print()

    rows = [
        ('Cycles',       lambda r: f"{r.total_cycles:>14,.0f}"),
        ('Wall time',    lambda r: f"{r.wall_time_s*1000:>10.2f} ms"),
        ('Bottleneck',   lambda r: f"{r.system_bottleneck:>14}"),
        ('Energy (J)',   lambda r: f"{r.total_energy_joules:>14.3f}"),
        ('Avg power (W)',lambda r: f"{r.average_power_watts:>12.1f} W"),
    ]

    for label, fmt in rows:
        print(f"  {label:<22}", end='')
        for cfg_name in configs:
            r = results[(wl_name, cfg_name)]
            print(f"  {fmt(r):<{COL_W}}", end='')
        print()

# ── 5. Find the fastest config per workload ───────────────────────────────────

print(f"\n{'='*90}")
print("  Summary: fastest hardware per workload")
print(f"{'='*90}")
for wl_name in workloads:
    best = min(configs.keys(),
               key=lambda c: results[(wl_name, c)].total_cycles)
    r = results[(wl_name, best)]
    print(f"  {wl_name}  →  {best}")
    print(f"    {r.total_cycles:,.0f} cycles  |  "
          f"{r.wall_time_s*1000:.2f} ms  |  "
          f"{r.system_bottleneck}-bound  |  "
          f"{r.total_energy_joules:.3f} J")
