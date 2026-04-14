"""
Feasibility checker for tile/mapping candidates.

check_feasibility(op, hw_block, tile_sizes) -> FeasibilityResult
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any, List
from ..workload.ops import GEMMOp, Conv2DOp, Op


@dataclass
class FeasibilityResult:
    """Result of checking whether a tiling fits on the hardware."""
    feasible: bool
    violations: List[str]   # human-readable list of violations
    memory_footprint: Dict[int, int]   # level -> bytes required
    memory_capacity: Dict[int, int]    # level -> bytes available

    def __repr__(self):
        status = 'OK' if self.feasible else 'INFEASIBLE'
        return f"FeasibilityResult({status}, violations={self.violations})"


def check_feasibility(
    op: Op,
    hw_block,
    tile_sizes: Dict[str, int],
    dtype_bytes: int = 2,
) -> FeasibilityResult:
    """
    Check whether a set of tile sizes is feasible on the hardware block.

    Checks:
      1. Tile footprint at each memory level ≤ hardware capacity
      2. Output tile fits in output SRAM/register file

    Parameters
    ----------
    op         : the Op being mapped
    hw_block   : hardware block with capacity properties
    tile_sizes : {dim_name: tile_size}  e.g. {'m': 32, 'k': 32, 'n': 32}
    dtype_bytes: element size in bytes
    """
    violations: List[str] = []

    # Get hardware memory capacity (bytes) at each level
    # Level 1: on-chip SRAM (capacity_bytes or fallback)
    sram_capacity = _get_capacity(hw_block)
    memory_capacity = {0: 8192, 1: sram_capacity, 2: sram_capacity * 4, 3: 2**40}

    # Compute footprint for the given tiles
    footprint: Dict[int, int] = {}
    if isinstance(op, GEMMOp):
        m = tile_sizes.get('m', op.M)
        k = tile_sizes.get('k', op.K)
        n = tile_sizes.get('n', op.N)
        # Inputs: A[m,k] + B[k,n], Output: C[m,n]
        footprint[1] = (m * k + k * n + m * n) * dtype_bytes
    elif isinstance(op, Conv2DOp):
        n_ = tile_sizes.get('n', 1)
        c  = tile_sizes.get('c', op.C)
        k  = tile_sizes.get('k', op.K)
        ho = tile_sizes.get('ho', op.Ho)
        wo = tile_sizes.get('wo', op.Wo)
        r  = tile_sizes.get('r', op.R)
        s  = tile_sizes.get('s', op.S)
        # Input tile, weight tile, output tile
        footprint[1] = (n_ * c * (ho * op.stride + r - 1) * (wo * op.stride + s - 1)
                        + k * c * r * s
                        + n_ * k * ho * wo) * dtype_bytes
    else:
        # Generic: rough estimate using total tensor sizes
        footprint[1] = int(op.read_bytes(dtype_bytes) + op.write_bytes(dtype_bytes))

    # Check each level
    for level, required in footprint.items():
        available = memory_capacity.get(level, 0)
        if required > available:
            violations.append(
                f"Level {level} footprint {required:,} B > capacity {available:,} B"
            )

    return FeasibilityResult(
        feasible=len(violations) == 0,
        violations=violations,
        memory_footprint=footprint,
        memory_capacity={k: memory_capacity[k] for k in footprint},
    )


def _get_capacity(hw_block) -> int:
    """Extract on-chip SRAM capacity in bytes from a hardware block."""
    if hasattr(hw_block, 'get_property'):
        cap = hw_block.get_property('capacity_bytes')
        if cap and cap > 0:
            return int(cap)
    # Look for common attribute names
    for attr in ('on_chip_sram_mb', 'sram_size_mb', 'cache_size_mb'):
        val = getattr(hw_block, attr, None)
        if val is not None:
            return int(val * 1024 * 1024)
    return 256 * 1024  # default: 256 KB
