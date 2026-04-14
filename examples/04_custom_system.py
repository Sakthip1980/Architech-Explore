"""
Example 4 — Custom System with Memory Hierarchy and Connections
==============================================================
Build a system with three hardware blocks wired together:

  DRAM  ──(512 GB/s bus)──▶  L2 Scratchpad  ──(2 TB/s bus)──▶  NPU

Show:
  - PowerDomain / ClockDomain inheritance
  - Property propagation through the hierarchy
  - Per-block energy breakdown using SystemPowerModel
  - Transaction lifecycle on a Connection
  - AnalyticalEngine with a custom block_map (some ops run on NPU,
    others on the scratchpad acting as a small compute unit)

Run from the repo root:
    python examples/04_custom_system.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.hardware import (
    ComputeBlock, MemoryBlock, InterconnectBlock,
    PowerDomain, ClockDomain, Connection, make_transaction,
)
from simulator.workload import OpGraph
from simulator.workload.ops import GEMMOp, Conv2DOp, AddOp
from simulator.engine import AnalyticalEngine
from simulator.power.model import SystemPowerModel

# ── 1. Create hardware blocks ──────────────────────────────────────────────────

# Off-chip DRAM — large bandwidth, high capacity
dram = MemoryBlock('DRAM')
dram.set_property('BW',           512e9)    # 512 GB/s (e.g. HBM2e)
dram.set_property('P_total',       40.0)    # 40 W
dram.set_property('frequency',   1.6e9)    # 1.6 GHz transfer rate
dram.set_property('capacity_bytes', 8 * 1024**3)  # 8 GB

# On-chip scratchpad (L2 SRAM) — very fast, small
spad = MemoryBlock('L2_Scratchpad')
spad.set_property('BW',          2000e9)   # 2 TB/s
spad.set_property('P_total',       10.0)   # 10 W
spad.set_property('frequency',    2.0e9)   # 2 GHz
spad.set_property('capacity_bytes', 32 * 1024**2)  # 32 MB

# NPU compute block
npu = ComputeBlock('NPU')
npu.set_property('frequency',    1.5e9)    # 1.5 GHz
npu.set_property('ops_per_cycle', 8192)    # 4096 MACs × 2 FLOPs/MAC
npu.set_property('P_total',       120.0)   # 120 W TDP
npu.set_property('voltage',       '0.85V')

# ── 2. Power and clock domains ────────────────────────────────────────────────

# All compute blocks share one power domain at 0.85 V
compute_pwr = PowerDomain('ComputePowerDomain', voltage_str='0.85V')
npu.set_power_domain(compute_pwr)
spad.set_power_domain(compute_pwr)

# NPU and scratchpad share a 1.5 GHz clock domain
compute_clk = ClockDomain('ComputeClockDomain', frequency_str='1.5GHz')
npu.set_clock_domain(compute_clk)
spad.set_clock_domain(compute_clk)

print("=== Hardware Blocks ===")
for blk in [dram, spad, npu]:
    freq = blk.get_property('frequency')
    bw   = blk.get_property('BW')
    opc  = blk.get_property('ops_per_cycle')
    pwr  = blk.get_property('P_total')
    freq_str = f"{freq/1e9:.1f} GHz" if freq else "—"
    bw_str   = f"{bw/1e9:.0f} GB/s" if bw   else f"opc={int(opc)}" if opc else "—"
    print(f"  {blk.name:<18}  "
          f"freq={freq_str}  "
          f"BW/ops={bw_str}  "
          f"P={pwr:.0f} W")
print()

# ── 3. Connections (bus topology) ─────────────────────────────────────────────

# DRAM → scratchpad: wide HBM-style bus
dram_to_spad = Connection(
    src_block=dram, dst_block=spad,
    bandwidth_bytes_per_cycle=512e9 / 1.5e9,  # at 1.5 GHz
    latency_cycles=80,
    energy_per_bit=3.2e-12,   # 3.2 pJ/bit (off-chip)
    protocol='HBM2e',
)

# scratchpad → NPU: on-chip NoC, ultra-wide
spad_to_npu = Connection(
    src_block=spad, dst_block=npu,
    bandwidth_bytes_per_cycle=2000e9 / 1.5e9,  # at 1.5 GHz
    latency_cycles=4,
    energy_per_bit=0.2e-12,   # 0.2 pJ/bit (on-chip)
    protocol='NoC',
)

print("=== Connections ===")
for conn in [dram_to_spad, spad_to_npu]:
    print(f"  {conn.src_block.name} → {conn.dst_block.name}  "
          f"protocol={conn.protocol}  "
          f"latency={conn.latency_cycles} cycles  "
          f"BW={conn.bandwidth_bytes_per_cycle:.0f} B/cycle")
print()

# ── 4. Simulate a transaction lifecycle ───────────────────────────────────────

print("=== Transaction Lifecycle ===")
tx = make_transaction(src=dram.name, dst=spad.name,
                      size_bytes=4096, current_cycle=0)  # 4 KB DMA burst
dram_to_spad.enqueue(tx, current_cycle=0)
print(f"  Created  : tx #{tx.id}  size={tx.size_bytes/1024**2:.0f} MB  state={tx.state.name}")

dram_to_spad.tick(current_cycle=0)
print(f"  After tick(0): state={tx.state.name}")

# Advance until completion
for cyc in range(1, 500):
    dram_to_spad.tick(current_cycle=cyc)
    if tx.state.name == 'COMPLETED':
        latency = tx.cycle_completed - tx.cycle_created
        print(f"  Completed at cycle {cyc}  (latency={latency} cycles)")
        break
else:
    print(f"  Still in state {tx.state.name} after 500 cycles")
print()

# ── 5. Build a custom workload graph ──────────────────────────────────────────
#
# A two-branch graph:
#
#   conv1 ──┐
#            ├──▶ add ──▶ gemm_out
#   conv2 ──┘
#
# conv1 and conv2 run in parallel (no dependency between them).
# 'add' depends on both.  'gemm_out' depends on 'add'.

graph = OpGraph()

# add_op(op, inputs=[...]) wires dependency edges and returns the new OpNode
conv1_op = Conv2DOp(N=1, C=256, H=28, W=28, K=256, R=3, S=3, stride=1, pad=1, name='conv1')
conv2_op = Conv2DOp(N=1, C=256, H=28, W=28, K=256, R=3, S=3, stride=1, pad=1, name='conv2')
add_op   = AddOp(elements=1 * 256 * 28 * 28, name='add')
gemm_op  = GEMMOp(M=784, K=256, N=1024, name='gemm_out')

node_conv1 = graph.add_op(conv1_op)
node_conv2 = graph.add_op(conv2_op)
node_add   = graph.add_op(add_op,  inputs=[node_conv1, node_conv2])
node_gemm  = graph.add_op(gemm_op, inputs=[node_add])

print("=== Custom Workload Graph ===")
print(f"  Nodes : {len(graph)}")
print(f"  FLOPs : {graph.total_flops() / 1e9:.3f} GFLOPs")
print(f"  Read  : {graph.total_read_bytes() / 1e6:.1f} MB")
print()

# ── 6. Simulate with block map ────────────────────────────────────────────────
#
# Assign conv ops to the NPU; the add and gemm also run on the NPU.
# (A real system would route ops differently, but this demos the block_map API.)

block_map = {
    'conv1':    npu,
    'conv2':    npu,
    'add':      npu,
    'gemm_out': npu,
}

engine = AnalyticalEngine(dtype_bytes=2)
result = engine.run(graph, default_block=npu, block_map=block_map)

print("=== Simulation Results ===")
print(f"  Total cycles  : {result.total_cycles:,.0f}")
print(f"  Wall time     : {result.wall_time_s * 1000:.3f} ms")
print(f"  Bottleneck    : {result.system_bottleneck}")
print(f"  Total FLOPs   : {result.total_flops / 1e9:.3f} GFLOPs")
print(f"  Total energy  : {result.total_energy_joules:.5f} J")
print()

print("=== Per-Op Breakdown ===")
print(f"  {'Op':<18}  {'Cycles':>12}  {'Bottleneck':>10}  {'AI':>8}")
print(f"  {'-'*18}  {'-'*12}  {'-'*10}  {'-'*8}")
for op_res in result.per_op:
    print(f"  {op_res.name:<18}  {op_res.latency_cycles:>12,.0f}  "
          f"{op_res.roofline.bottleneck:>10}  "
          f"{op_res.roofline.arithmetic_intensity:>8.2f}")
print()

# ── 7. Power breakdown ────────────────────────────────────────────────────────

power_model = SystemPowerModel()
# Register all blocks with their cycle budgets (frequency_hz used for wall-time energy)
power_model.add_block(npu,  active_cycles=result.total_cycles, idle_cycles=0,
                      ops=result.total_flops, bytes_transferred=result.total_bytes,
                      frequency_hz=1.5e9)
power_model.add_block(spad, active_cycles=result.total_cycles // 4,
                      idle_cycles=3 * result.total_cycles // 4,
                      ops=0, bytes_transferred=result.total_bytes,
                      frequency_hz=1.5e9)
power_model.add_block(dram, active_cycles=result.total_cycles // 8,
                      idle_cycles=7 * result.total_cycles // 8,
                      ops=0, bytes_transferred=result.total_bytes,
                      frequency_hz=1.5e9)

breakdown = power_model.aggregate()

print("=== Power Breakdown ===")
for stats in breakdown['per_block']:
    print(f"  {stats['block']:<18}  "
          f"E_dynamic={stats['dynamic_energy_j']:.5f} J  "
          f"E_static={stats['static_energy_j']:.5f} J  "
          f"total={stats['total_energy_j']:.5f} J")
sys_e = breakdown['system']['total_energy_j']
sys_p = breakdown['system']['avg_power_w']
print(f"\n  System total  : {sys_e:.5f} J  avg {sys_p:.2f} W")
