"""
Roofline model — written once, works for every Op type forever.

roofline(flops, read_bytes, write_bytes, hw_block) -> RooflineResult

The roofline equation:
  compute_cycles = flops / throughput_per_cycle
  memory_cycles  = (read_bytes + write_bytes) / BW_bytes_per_cycle
  total_cycles   = max(compute_cycles, memory_cycles)

hw_block is any object with .get_property(name) — typically a Block from
simulator.hardware, but the function works with any duck-typed object that
exposes 'throughput_per_cycle' and 'BW_bytes_per_cycle'.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RooflineResult:
    """Roofline analysis result for one Op on one hardware block."""
    cycles: float              # total cycles (max of compute and memory)
    compute_cycles: float      # cycles if compute-bound
    memory_cycles: float       # cycles if memory-bound
    bottleneck: str            # 'compute' | 'memory' | 'balanced'
    arithmetic_intensity: float  # FLOPs per byte (x-axis of roofline plot)
    achieved_throughput: float   # actual FLOPs per cycle achieved
    peak_throughput: float       # hardware peak FLOPs per cycle
    peak_bandwidth: float        # hardware peak bytes per cycle
    ridge_point: float           # AI at which compute = memory bottleneck


def roofline(
    flops: float,
    read_bytes: float,
    write_bytes: float,
    hw_block,
    dtype_bytes: int = 2,
) -> RooflineResult:
    """
    Apply the roofline model for one operation on one hardware block.

    Parameters
    ----------
    flops       : total FLOPs for this operation
    read_bytes  : bytes read from off-chip memory
    write_bytes : bytes written to off-chip memory
    hw_block    : Block (or duck-typed object) exposing get_property()
    dtype_bytes : data type width in bytes (used for arithmetic intensity)

    Returns
    -------
    RooflineResult with cycles, bottleneck, achieved_throughput, etc.
    """
    # --- Pull hardware parameters (all in per-cycle units)
    tp_per_cycle = _get_hw(hw_block, 'throughput_per_cycle',
                            fallback_keys=['ops_per_cycle'])   # FLOP/cycle
    bw_per_cycle = _get_hw(hw_block, 'BW_bytes_per_cycle',
                            fallback_keys=['width_bytes'])     # bytes/cycle

    # Guard: avoid division by zero for blocks with no properties set
    if tp_per_cycle is None or tp_per_cycle <= 0:
        tp_per_cycle = 1.0   # 1 FLOP/cycle fallback
    if bw_per_cycle is None or bw_per_cycle <= 0:
        bw_per_cycle = 1.0   # 1 byte/cycle fallback

    total_bytes = read_bytes + write_bytes

    # --- Roofline computation
    compute_cycles = flops / tp_per_cycle if flops > 0 else 0.0
    memory_cycles  = total_bytes / bw_per_cycle if total_bytes > 0 else 0.0
    total_cycles   = max(compute_cycles, memory_cycles, 1.0)

    # --- Bottleneck classification
    ratio = compute_cycles / memory_cycles if memory_cycles > 0 else float('inf')
    if ratio > 1.05:
        bottleneck = 'compute'
    elif ratio < 0.95:
        bottleneck = 'memory'
    else:
        bottleneck = 'balanced'

    # --- Arithmetic intensity (FLOPs / byte)
    ai = flops / total_bytes if total_bytes > 0 else float('inf')

    # --- Ridge point: AI where compute_cycles == memory_cycles
    #     tp_per_cycle / bw_per_cycle = FLOP/byte at balance
    ridge_point = tp_per_cycle / bw_per_cycle

    # --- Achieved throughput
    achieved_throughput = flops / total_cycles if total_cycles > 0 else 0.0

    return RooflineResult(
        cycles=total_cycles,
        compute_cycles=compute_cycles,
        memory_cycles=memory_cycles,
        bottleneck=bottleneck,
        arithmetic_intensity=ai,
        achieved_throughput=achieved_throughput,
        peak_throughput=tp_per_cycle,
        peak_bandwidth=bw_per_cycle,
        ridge_point=ridge_point,
    )


def _get_hw(hw_block, primary: str, fallback_keys=()) -> Optional[float]:
    """Try get_property(primary), then fallback keys, then None."""
    val = None
    if hasattr(hw_block, 'get_property'):
        val = hw_block.get_property(primary)
        if val is None:
            for key in fallback_keys:
                val = hw_block.get_property(key)
                if val is not None:
                    break
    elif hasattr(hw_block, primary):
        val = getattr(hw_block, primary)
    return val
