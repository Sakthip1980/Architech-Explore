"""
Example 3 — Sensitivity Sweep & Pareto Front
=============================================
Answer the question: "Which hardware property matters most?"

Sweep each of these properties independently while holding all others fixed:
  - Memory bandwidth  (32 → 1024 GB/s)
  - Frequency         (0.25 → 4 GHz)
  - MAC units         (256 → 16384)

Then build a Pareto front on cycles vs energy to find the best
trade-off configurations.

Saves four plots to examples/plots/ (requires matplotlib).
Run from the repo root:
    python examples/03_sensitivity_sweep.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')   # headless / no display required

from simulator.hardware import ComputeBlock
from simulator.workload import OpGraph
from simulator.models.workload import get_resnet50_workload
from simulator.engine import AnalyticalEngine
from simulator.results import SimResult, SensitivitySweep
from simulator.results import plot_sensitivity, plot_pareto_front

# ── Shared setup ──────────────────────────────────────────────────────────────

graph = OpGraph.from_workload(get_resnet50_workload())
engine = AnalyticalEngine(dtype_bytes=2)

os.makedirs('examples/plots', exist_ok=True)

# ── Helper: build a baseline ComputeBlock ────────────────────────────────────

def baseline_block(name='BaseNPU'):
    """A mid-range NPU: 2048 MACs, 1 GHz, 256 GB/s, FP16."""
    blk = ComputeBlock(name)
    blk.set_property('frequency',    '1GHz')
    blk.set_property('ops_per_cycle', 2048 * 2)   # 2048 MACs × 2 FLOPs/MAC
    blk.set_property('BW',            256e9)        # 256 GB/s
    blk.set_property('P_total',       100.0)        # 100 W TDP
    blk.set_property('voltage',       '0.9V')
    return blk

# ── Sweep 1: bandwidth ────────────────────────────────────────────────────────

print("Sweeping bandwidth (32 → 1024 GB/s)...")
bw_values = [32e9, 64e9, 128e9, 256e9, 512e9, 1024e9]
bw_results = []
for bw in bw_values:
    blk = baseline_block()
    blk.set_property('BW', bw)
    raw = engine.run(graph, blk)
    sr  = SimResult.from_analytical(raw)
    sr.metadata['BW'] = bw
    sr.metadata['BW_label'] = f"{bw/1e9:.0f} GB/s"
    bw_results.append(sr)
    print(f"  {bw/1e9:>6.0f} GB/s  →  {raw.total_cycles:>12,.0f} cycles  "
          f"[{raw.system_bottleneck}]")

# ── Sweep 2: frequency ────────────────────────────────────────────────────────

print("\nSweeping frequency (0.25 → 4 GHz)...")
freq_values = [0.25e9, 0.5e9, 1e9, 2e9, 4e9]
freq_results = []
for f in freq_values:
    blk = baseline_block()
    blk.set_property('frequency', f)
    # Re-derive throughput = ops_per_cycle * frequency
    # (ops_per_cycle stays fixed; higher freq → higher throughput)
    raw = engine.run(graph, blk)
    sr  = SimResult.from_analytical(raw)
    sr.metadata['frequency'] = f
    sr.metadata['freq_label'] = f"{f/1e9:.2f} GHz"
    freq_results.append(sr)
    print(f"  {f/1e9:.2f} GHz  →  {raw.total_cycles:>12,.0f} cycles  "
          f"[{raw.system_bottleneck}]  "
          f"wall={raw.wall_time_s*1000:.2f} ms")

# ── Sweep 3: compute (ops_per_cycle = mac_units × 2) ─────────────────────────

print("\nSweeping compute (256 → 16384 MACs)...")
mac_values = [256, 512, 1024, 2048, 4096, 8192, 16384]
mac_results = []
for macs in mac_values:
    blk = baseline_block()
    blk.set_property('ops_per_cycle', macs * 2)
    raw = engine.run(graph, blk)
    sr  = SimResult.from_analytical(raw)
    sr.metadata['ops_per_cycle'] = macs * 2
    sr.metadata['macs']          = macs
    mac_results.append(sr)
    print(f"  {macs:>5} MACs  →  {raw.total_cycles:>12,.0f} cycles  "
          f"[{raw.system_bottleneck}]")

# ── Pareto front: cycles vs energy across all BW configs ─────────────────────

print("\nPareto front (bandwidth sweep):")
pareto = SensitivitySweep.pareto_front(bw_results, 'total_cycles', 'total_energy_j')
for r in pareto:
    print(f"  BW={r.metadata['BW']/1e9:.0f} GB/s  "
          f"cycles={r.total_cycles:.3g}  "
          f"energy={r.total_energy_j:.3f} J")

# ── Save plots ────────────────────────────────────────────────────────────────

print("\nSaving plots to examples/plots/ ...")

fig = plot_sensitivity(bw_results, 'BW', 'total_cycles',
                       title='Cycles vs Memory Bandwidth')
fig.savefig('examples/plots/sensitivity_bandwidth.png', dpi=150, bbox_inches='tight')

fig = plot_sensitivity(freq_results, 'frequency', 'total_cycles',
                       title='Cycles vs Clock Frequency')
fig.savefig('examples/plots/sensitivity_frequency.png', dpi=150, bbox_inches='tight')

fig = plot_sensitivity(mac_results, 'ops_per_cycle', 'total_cycles',
                       title='Cycles vs Compute (ops/cycle)')
fig.savefig('examples/plots/sensitivity_compute.png', dpi=150, bbox_inches='tight')

fig = plot_pareto_front(bw_results, 'total_cycles', 'total_energy_j',
                        title='Pareto Front: Cycles vs Energy (BW sweep)')
fig.savefig('examples/plots/pareto_bandwidth.png', dpi=150, bbox_inches='tight')

print("  sensitivity_bandwidth.png")
print("  sensitivity_frequency.png")
print("  sensitivity_compute.png")
print("  pareto_bandwidth.png")
print("\nDone.")
