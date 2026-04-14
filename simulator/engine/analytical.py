"""
Analytical simulation engine.

Schedules an OpGraph onto a hardware block (or per-op block assignments)
using the roofline model per op, then uses DAG dynamic programming to find
the total critical-path cycle count.

AnalyticalEngine.run(graph, default_block) -> AnalyticalResult
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from ..workload.graph import OpGraph, OpNode
from .roofline import roofline, RooflineResult


# ---------------------------------------------------------------------------
# Per-op simulation record
# ---------------------------------------------------------------------------

@dataclass
class OpResult:
    """Simulation result for one Op node."""
    name: str
    flops: float
    read_bytes: float
    write_bytes: float
    roofline: RooflineResult
    start_cycle: float   # cycle when this op begins (after all deps done)
    end_cycle: float     # start_cycle + roofline.cycles
    block_name: str      # hardware block used

    @property
    def latency_cycles(self) -> float:
        return self.end_cycle - self.start_cycle


# ---------------------------------------------------------------------------
# AnalyticalResult
# ---------------------------------------------------------------------------

@dataclass
class AnalyticalResult:
    """Aggregate result from AnalyticalEngine.run()."""
    total_cycles: float
    wall_time_s: float
    total_energy_joules: float
    average_power_watts: float
    total_flops: float
    total_bytes: float
    system_bottleneck: str          # 'compute' | 'memory' | 'balanced'
    per_op: List[OpResult] = field(default_factory=list)
    # Optional power breakdown (populated by power model in Phase 5)
    power_breakdown: Optional[Dict[str, Any]] = None

    def summary(self) -> Dict[str, Any]:
        return {
            'total_cycles': self.total_cycles,
            'wall_time_s': self.wall_time_s,
            'total_energy_j': self.total_energy_joules,
            'avg_power_w': self.average_power_watts,
            'total_flops': self.total_flops,
            'total_bytes': self.total_bytes,
            'system_bottleneck': self.system_bottleneck,
            'num_ops': len(self.per_op),
            'ops': [
                {
                    'name': r.name,
                    'flops': r.flops,
                    'cycles': r.latency_cycles,
                    'bottleneck': r.roofline.bottleneck,
                    'arithmetic_intensity': r.roofline.arithmetic_intensity,
                    'block': r.block_name,
                }
                for r in self.per_op
            ],
        }


# ---------------------------------------------------------------------------
# AnalyticalEngine
# ---------------------------------------------------------------------------

class AnalyticalEngine:
    """
    Fast analytical simulation engine based on the roofline model.

    Usage
    -----
    from simulator.workload.graph import OpGraph
    from simulator.hardware.blocks import block_from_module
    from simulator.models.npu import NPU

    npu = NPU('A', mac_units=2048, frequency_ghz=1.0, ...)
    blk = block_from_module(npu)

    graph = OpGraph.from_workload(get_gpt2_workload())
    result = AnalyticalEngine().run(graph, blk)
    print(result.total_cycles, result.system_bottleneck)
    """

    def __init__(self, dtype_bytes: int = 2):
        """
        Parameters
        ----------
        dtype_bytes : default data type width (2 = FP16/BF16, 4 = FP32, 1 = INT8)
        """
        self.dtype_bytes = dtype_bytes

    def run(
        self,
        graph: OpGraph,
        default_block,
        block_map: Optional[Dict[str, Any]] = None,
    ) -> AnalyticalResult:
        """
        Simulate graph on hardware block(s) analytically.

        Parameters
        ----------
        graph         : OpGraph to simulate
        default_block : hardware Block (or Module) for all ops without assignment
        block_map     : optional {op_name: block} override per op

        Returns
        -------
        AnalyticalResult with cycles, energy, per-op breakdown
        """
        block_map = block_map or {}
        order = graph.topological_order()

        # DAG DP: finish_cycle[node] = cycle when this node completes
        finish_cycle: Dict[OpNode, float] = {}
        op_results: List[OpResult] = []

        for node in order:
            # Select block for this op
            blk = block_map.get(node.name, default_block)
            blk_name = getattr(blk, 'name', str(blk))

            op = node.op
            f  = op.flops()
            rb = op.read_bytes(self.dtype_bytes)
            wb = op.write_bytes(self.dtype_bytes)

            # Apply roofline
            rf = roofline(f, rb, wb, blk, self.dtype_bytes)

            # Start after all dependencies finish
            start = max((finish_cycle[dep] for dep in node.inputs), default=0.0)
            end   = start + rf.cycles

            finish_cycle[node] = end
            op_results.append(OpResult(
                name=node.name,
                flops=f,
                read_bytes=rb,
                write_bytes=wb,
                roofline=rf,
                start_cycle=start,
                end_cycle=end,
                block_name=blk_name,
            ))

        total_cycles = max(finish_cycle.values(), default=0.0)

        # --- Derive time and energy
        frequency = _get_frequency(default_block)
        wall_time_s = total_cycles / frequency if frequency > 0 else 0.0

        power = _get_power(default_block)
        total_energy = power * wall_time_s

        avg_power = power  # simplified; Phase 5 power model gives per-block breakdown

        # --- System bottleneck: majority vote among ops by cycle count
        compute_cycles = sum(r.roofline.compute_cycles for r in op_results)
        memory_cycles  = sum(r.roofline.memory_cycles  for r in op_results)
        if compute_cycles > memory_cycles * 1.05:
            system_bottleneck = 'compute'
        elif memory_cycles > compute_cycles * 1.05:
            system_bottleneck = 'memory'
        else:
            system_bottleneck = 'balanced'

        total_flops = sum(r.flops for r in op_results)
        total_bytes = sum(r.read_bytes + r.write_bytes for r in op_results)

        return AnalyticalResult(
            total_cycles=total_cycles,
            wall_time_s=wall_time_s,
            total_energy_joules=total_energy,
            average_power_watts=avg_power,
            total_flops=total_flops,
            total_bytes=total_bytes,
            system_bottleneck=system_bottleneck,
            per_op=op_results,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_frequency(blk) -> float:
    """Extract frequency from a Block or fall back to 1 GHz."""
    if hasattr(blk, 'get_property'):
        f = blk.get_property('frequency')
        if f and f > 0:
            return f
    if hasattr(blk, 'frequency_ghz'):
        return blk.frequency_ghz * 1e9
    return 1e9   # 1 GHz default


def _get_power(blk) -> float:
    """Extract total power from a Block in Watts."""
    if hasattr(blk, 'get_power'):
        return blk.get_power()
    if hasattr(blk, 'get_property'):
        pt = blk.get_property('P_total')
        if pt is not None:
            return pt
    if hasattr(blk, 'tdp_watts'):
        return blk.tdp_watts
    return 0.0
