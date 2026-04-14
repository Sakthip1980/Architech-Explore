"""
Dataflow modes as LoopNest presets.

DataflowMode enum: WEIGHT_STATIONARY, OUTPUT_STATIONARY, INPUT_STATIONARY, BEST
get_loop_nest(mode, M, K, N, ...) -> LoopNest

'BEST' tries all three and returns the one with lowest memory traffic.
"""

from enum import Enum
from typing import Optional, Dict
from .loop_nest import LoopNest


class DataflowMode(Enum):
    WEIGHT_STATIONARY  = 'ws'
    OUTPUT_STATIONARY  = 'os'
    INPUT_STATIONARY   = 'is'
    BEST               = 'best'   # auto-select lowest traffic


def get_loop_nest(
    mode: DataflowMode,
    M: int, K: int, N: int,
    tile_m: int = 32, tile_k: int = 32, tile_n: int = 32,
    dtype_bytes: int = 2,
    memory_sizes: Optional[Dict[int, int]] = None,
) -> LoopNest:
    """
    Construct a LoopNest for a GEMM op given a dataflow mode.

    If mode is BEST, all three presets are evaluated and the one
    with the lowest tiled_read_bytes + tiled_write_bytes is returned.
    Optionally, feasibility is checked against memory_sizes.
    """
    candidates = {
        DataflowMode.WEIGHT_STATIONARY: LoopNest.weight_stationary,
        DataflowMode.OUTPUT_STATIONARY: LoopNest.output_stationary,
        DataflowMode.INPUT_STATIONARY:  LoopNest.input_stationary,
    }

    if mode != DataflowMode.BEST:
        fn = candidates[mode]
        return fn(M, K, N, tile_m, tile_k, tile_n, dtype_bytes)

    # BEST: try all, return lowest-traffic feasible option
    best_nest: Optional[LoopNest] = None
    best_traffic = float('inf')
    for m, fn in candidates.items():
        nest = fn(M, K, N, tile_m, tile_k, tile_n, dtype_bytes)
        if memory_sizes and not nest.fits_in_memory(memory_sizes):
            continue
        traffic = nest.tiled_read_bytes() + nest.tiled_write_bytes()
        if traffic < best_traffic:
            best_traffic = traffic
            best_nest = nest

    # Fallback: weight stationary if no feasible candidate
    return best_nest or LoopNest.weight_stationary(M, K, N, tile_m, tile_k, tile_n, dtype_bytes)
