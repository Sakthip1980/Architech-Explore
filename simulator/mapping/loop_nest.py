"""
Loop nest representation for tiling and dataflow analysis.

A LoopNest is a list of LoopVar objects, one per loop dimension.
Each LoopVar has:
  - name            : dimension name ('m', 'k', 'n', 'c', 'r', 's', etc.)
  - size            : total loop extent
  - tile_size       : current tiling factor (must divide size)
  - memory_level    : 0 = register, 1 = L1/scratchpad, 2 = L2, 3 = DRAM
  - spatial_parallelism : how many PEs handle this dimension in parallel

Named dataflow presets:
  LoopNest.weight_stationary()  — WS: weights stay in registers; slide input
  LoopNest.output_stationary()  — OS: partial sums stay in registers
  LoopNest.input_stationary()   — IS: input tile stays; slide weights

These are the ONLY places where WS/IS/OS are defined.
Everything else uses the general LoopNest abstraction.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class LoopVar:
    """One loop dimension in a tiled loop nest."""
    name: str
    size: int               # total loop extent
    tile_size: int          # tile size for this level
    memory_level: int = 1   # 0=reg, 1=L1, 2=L2, 3=DRAM
    spatial_parallelism: int = 1  # parallel PEs on this dimension

    def __post_init__(self):
        if self.tile_size > self.size:
            self.tile_size = self.size
        # Snap tile_size up to next power of 2 for alignment
        # (only if not already a divisor)
        if self.size % self.tile_size != 0:
            # round down to largest divisor <= tile_size
            self.tile_size = self._largest_divisor_leq(self.size, self.tile_size)

    @staticmethod
    def _largest_divisor_leq(n: int, target: int) -> int:
        """Return largest integer d ≤ target that evenly divides n."""
        for d in range(min(target, n), 0, -1):
            if n % d == 0:
                return d
        return 1

    @property
    def num_tiles(self) -> int:
        """Number of tiles along this dimension."""
        return math.ceil(self.size / self.tile_size)

    def __repr__(self):
        return (f"LoopVar({self.name!r}, size={self.size}, "
                f"tile={self.tile_size}, mem_lvl={self.memory_level}, "
                f"par={self.spatial_parallelism})")


class LoopNest:
    """
    Tiled loop nest for a tensor operation.

    Supports tiled data reuse analysis and memory capacity checks.
    """

    def __init__(self, loops: List[LoopVar], dtype_bytes: int = 2):
        self.loops: List[LoopVar] = loops
        self.dtype_bytes = dtype_bytes

    # ------------------------------------------------------------------
    # Data reuse / traffic estimates
    # ------------------------------------------------------------------

    def tiled_read_bytes(self) -> float:
        """
        Estimate total bytes read from memory given the tiling.

        Conservative model: each tile of data at memory_level > 0 is
        loaded once per tile iteration of outer loops.
        """
        return self._traffic_estimate(mode='read')

    def tiled_write_bytes(self) -> float:
        """Estimate bytes written back to memory."""
        return self._traffic_estimate(mode='write')

    def _traffic_estimate(self, mode: str) -> float:
        """
        Simple tile-trip-count model:
          traffic ≈ product(num_tiles for outer loops) * tile_footprint
        """
        # Compute product of all tile counts (outer loops reload inner tiles)
        num_tiles_product = 1
        tile_footprint = self.dtype_bytes
        for lv in self.loops:
            num_tiles_product *= lv.num_tiles
            tile_footprint *= lv.tile_size
        return float(num_tiles_product * tile_footprint)

    # ------------------------------------------------------------------
    # Feasibility
    # ------------------------------------------------------------------

    def fits_in_memory(self, memory_sizes: Dict[int, int]) -> bool:
        """
        Check that tiles at each memory level fit in the given sizes.

        memory_sizes: {level: capacity_bytes}
        """
        for level, capacity in memory_sizes.items():
            footprint = self._footprint_at_level(level)
            if footprint > capacity:
                return False
        return True

    def _footprint_at_level(self, level: int) -> int:
        """Tile footprint of dimensions assigned to this memory level."""
        footprint = self.dtype_bytes
        for lv in self.loops:
            if lv.memory_level == level:
                footprint *= lv.tile_size
        return footprint

    # ------------------------------------------------------------------
    # Dataflow presets — WS, OS, IS
    # NOTE: These are the ONLY places where WS/IS/OS semantics are defined.
    # ------------------------------------------------------------------

    @classmethod
    def weight_stationary(cls, M: int, K: int, N: int,
                          tile_m: int = 32, tile_k: int = 32, tile_n: int = 32,
                          dtype_bytes: int = 2) -> 'LoopNest':
        """
        Weight-Stationary dataflow for GEMM: C[M,N] = A[M,K] × B[K,N].

        Weights B[K,N] tile stays in registers (level 0).
        Input A[M,K] tile streams from L1 (level 1).
        Output C[M,N] accumulates in registers, written to L1 when done.
        """
        return cls([
            LoopVar('n', N, min(tile_n, N), memory_level=0),   # weight dim: reg
            LoopVar('k', K, min(tile_k, K), memory_level=0),   # weight dim: reg
            LoopVar('m', M, min(tile_m, M), memory_level=1),   # activation: L1
        ], dtype_bytes=dtype_bytes)

    @classmethod
    def output_stationary(cls, M: int, K: int, N: int,
                          tile_m: int = 32, tile_k: int = 32, tile_n: int = 32,
                          dtype_bytes: int = 2) -> 'LoopNest':
        """
        Output-Stationary dataflow: partial sums C[m,n] stay in registers.

        Both A and B stream in; C accumulates without write-back until K done.
        """
        return cls([
            LoopVar('m', M, min(tile_m, M), memory_level=0),   # output: reg
            LoopVar('n', N, min(tile_n, N), memory_level=0),   # output: reg
            LoopVar('k', K, min(tile_k, K), memory_level=1),   # reduction: L1
        ], dtype_bytes=dtype_bytes)

    @classmethod
    def input_stationary(cls, M: int, K: int, N: int,
                         tile_m: int = 32, tile_k: int = 32, tile_n: int = 32,
                         dtype_bytes: int = 2) -> 'LoopNest':
        """
        Input-Stationary dataflow: input A[m,k] tile stays in registers.

        Weights B stream in; output C is written back each time N loop completes.
        """
        return cls([
            LoopVar('m', M, min(tile_m, M), memory_level=0),   # input: reg
            LoopVar('k', K, min(tile_k, K), memory_level=0),   # input: reg
            LoopVar('n', N, min(tile_n, N), memory_level=1),   # weight streams: L1
        ], dtype_bytes=dtype_bytes)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        return {
            'loops': [{
                'name': lv.name,
                'size': lv.size,
                'tile_size': lv.tile_size,
                'memory_level': lv.memory_level,
                'spatial_parallelism': lv.spatial_parallelism,
                'num_tiles': lv.num_tiles,
            } for lv in self.loops],
            'tiled_read_bytes': self.tiled_read_bytes(),
            'tiled_write_bytes': self.tiled_write_bytes(),
        }

    def __repr__(self):
        dims = ', '.join(f"{lv.name}({lv.tile_size}/{lv.size})" for lv in self.loops)
        return f"LoopNest([{dims}])"
