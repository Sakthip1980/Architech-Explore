"""
Workload operation types.

Each Op knows its own:
  - flops()           total floating-point operations
  - read_bytes(dtype) bytes read from memory (weights + activations)
  - write_bytes(dtype) bytes written to memory (outputs)
  - loop_nest()       structured loop variables for the mapping layer

The roofline engine imports these — the roofline function itself is written
once and never re-implemented for new op types.

Bridge helpers at the bottom convert existing GEMMLayer / ConvLayer objects.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# Op ABC
# ---------------------------------------------------------------------------

class Op(ABC):
    """Abstract base for all computable operations."""

    def __init__(self, name: str = ''):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def flops(self) -> float:
        """Total multiply-add operations (counted as 2 FLOPs each)."""

    @abstractmethod
    def read_bytes(self, dtype_bytes: int = 2) -> float:
        """Bytes read from memory for this operation."""

    @abstractmethod
    def write_bytes(self, dtype_bytes: int = 2) -> float:
        """Bytes written to memory for this operation."""

    def arithmetic_intensity(self, dtype_bytes: int = 2) -> float:
        """FLOPs per byte of memory traffic (roofline x-axis)."""
        total_bytes = self.read_bytes(dtype_bytes) + self.write_bytes(dtype_bytes)
        if total_bytes == 0:
            return float('inf')
        return self.flops() / total_bytes

    def loop_nest(self) -> List[Dict[str, Any]]:
        """
        Return a list of loop variable descriptors for the mapping layer.
        Each entry: {name, size, tile_size, memory_level, spatial_parallelism}
        Default: single flat loop.
        """
        return []

    def __repr__(self):
        return (f"{self.__class__.__name__}('{self.name}', "
                f"flops={self.flops():.3g}, "
                f"AI={self.arithmetic_intensity():.2f})")


# ---------------------------------------------------------------------------
# GEMM  —  the core tensor operation
# ---------------------------------------------------------------------------

class GEMMOp(Op):
    """
    General Matrix Multiply: C[M,N] = A[M,K] × B[K,N]

    FLOPs = 2 * M * K * N   (multiply + accumulate per output element)
    Reads = A + B weights + B activations if bias
    Write = C output
    """

    def __init__(self, M: int, K: int, N: int, name: str = ''):
        super().__init__(name or f'GEMM_{M}x{K}x{N}')
        self.M = M
        self.K = K
        self.N = N

    def flops(self) -> float:
        return 2.0 * self.M * self.K * self.N

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        # A matrix: M*K elements, B matrix: K*N elements
        return (self.M * self.K + self.K * self.N) * dtype_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.M * self.N * dtype_bytes

    def loop_nest(self) -> List[Dict[str, Any]]:
        return [
            {'name': 'm', 'size': self.M, 'tile_size': min(self.M, 32),
             'memory_level': 1, 'spatial_parallelism': 1},
            {'name': 'n', 'size': self.N, 'tile_size': min(self.N, 32),
             'memory_level': 1, 'spatial_parallelism': 1},
            {'name': 'k', 'size': self.K, 'tile_size': min(self.K, 32),
             'memory_level': 0, 'spatial_parallelism': 1},
        ]


# ---------------------------------------------------------------------------
# MatMul  —  alias for GEMMOp with batch dimension
# ---------------------------------------------------------------------------

class MatMulOp(Op):
    """
    Batched matrix multiply: out[B,M,N] = A[B,M,K] × W[K,N]
    Flattened to a single GEMM: (B*M) x K x N
    """

    def __init__(self, batch: int, M: int, K: int, N: int, name: str = ''):
        super().__init__(name or f'MatMul_B{batch}_M{M}_K{K}_N{N}')
        self._gemm = GEMMOp(batch * M, K, N)
        self.batch = batch
        self.M = M
        self.K = K
        self.N = N

    def flops(self) -> float:
        return self._gemm.flops()

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return self._gemm.read_bytes(dtype_bytes)

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self._gemm.write_bytes(dtype_bytes)

    def loop_nest(self) -> List[Dict[str, Any]]:
        return self._gemm.loop_nest()


# ---------------------------------------------------------------------------
# Conv2D  —  via im2col mapping to GEMM
# ---------------------------------------------------------------------------

class Conv2DOp(Op):
    """
    Standard 2-D convolution: out[N,K,Ho,Wo] = in[N,C,H,W] * W[K,C,R,S]

    Maps to GEMM via im2col:
      M = N * Ho * Wo
      K_dim = C * R * S
      N_dim = K (output channels)
    """

    def __init__(self, N: int, C: int, H: int, W: int,
                 K: int, R: int, S: int,
                 stride: int = 1, pad: int = 0,
                 name: str = ''):
        super().__init__(name or f'Conv2D_N{N}_C{C}_H{H}_W{W}_K{K}_R{R}_S{S}')
        self.N = N
        self.C = C
        self.H = H
        self.W = W
        self.K = K  # output channels
        self.R = R  # filter height
        self.S = S  # filter width
        self.stride = stride
        self.pad = pad

        # Output spatial dimensions
        self.Ho = (H + 2 * pad - R) // stride + 1
        self.Wo = (W + 2 * pad - S) // stride + 1

        # GEMM equivalent
        self._gemm = GEMMOp(
            M=N * self.Ho * self.Wo,
            K=C * R * S,
            N=K,
        )

    def flops(self) -> float:
        return self._gemm.flops()

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        # Input (no repeated counting for overlap — approximate)
        input_bytes  = self.N * self.C * self.H * self.W * dtype_bytes
        weight_bytes = self.K * self.C * self.R * self.S * dtype_bytes
        return input_bytes + weight_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.N * self.K * self.Ho * self.Wo * dtype_bytes

    def loop_nest(self) -> List[Dict[str, Any]]:
        return [
            {'name': 'n',  'size': self.N,           'tile_size': 1,
             'memory_level': 2, 'spatial_parallelism': 1},
            {'name': 'k',  'size': self.K,            'tile_size': min(self.K, 64),
             'memory_level': 1, 'spatial_parallelism': 1},
            {'name': 'c',  'size': self.C,            'tile_size': min(self.C, 16),
             'memory_level': 0, 'spatial_parallelism': 1},
            {'name': 'ho', 'size': self.Ho,           'tile_size': min(self.Ho, 8),
             'memory_level': 1, 'spatial_parallelism': 1},
            {'name': 'wo', 'size': self.Wo,           'tile_size': min(self.Wo, 8),
             'memory_level': 1, 'spatial_parallelism': 1},
            {'name': 'r',  'size': self.R,            'tile_size': self.R,
             'memory_level': 0, 'spatial_parallelism': 1},
            {'name': 's',  'size': self.S,            'tile_size': self.S,
             'memory_level': 0, 'spatial_parallelism': 1},
        ]


# ---------------------------------------------------------------------------
# DepthwiseConv2D
# ---------------------------------------------------------------------------

class DepthwiseConv2DOp(Op):
    """
    Depthwise separable convolution: each channel filtered independently.
    FLOPs = N * C * Ho * Wo * R * S  (no cross-channel accumulation)
    """

    def __init__(self, N: int, C: int, H: int, W: int,
                 R: int, S: int, stride: int = 1, pad: int = 0,
                 name: str = ''):
        super().__init__(name or f'DWConv_N{N}_C{C}_H{H}_W{W}_R{R}S{S}')
        self.N = N
        self.C = C
        self.H = H
        self.W = W
        self.R = R
        self.S = S
        self.stride = stride
        self.pad = pad
        self.Ho = (H + 2 * pad - R) // stride + 1
        self.Wo = (W + 2 * pad - S) // stride + 1

    def flops(self) -> float:
        return 2.0 * self.N * self.C * self.Ho * self.Wo * self.R * self.S

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        input_bytes  = self.N * self.C * self.H * self.W * dtype_bytes
        weight_bytes = self.C * self.R * self.S * dtype_bytes
        return input_bytes + weight_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.N * self.C * self.Ho * self.Wo * dtype_bytes


# ---------------------------------------------------------------------------
# Element-wise Add
# ---------------------------------------------------------------------------

class AddOp(Op):
    """Element-wise addition: out = A + B."""

    def __init__(self, elements: int, name: str = ''):
        super().__init__(name or f'Add_{elements}')
        self.elements = elements

    def flops(self) -> float:
        return float(self.elements)  # 1 add per element

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return 2 * self.elements * dtype_bytes  # two input tensors

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.elements * dtype_bytes


# ---------------------------------------------------------------------------
# Pooling (max/avg)
# ---------------------------------------------------------------------------

class PoolingOp(Op):
    """Spatial pooling: max or average over a kernel window."""

    def __init__(self, N: int, C: int, H: int, W: int,
                 pool_h: int, pool_w: int, stride: int = 1,
                 name: str = ''):
        super().__init__(name or f'Pool_{N}x{C}x{H}x{W}')
        self.N = N
        self.C = C
        self.H = H
        self.W = W
        self.pool_h = pool_h
        self.pool_w = pool_w
        self.stride = stride
        self.Ho = (H - pool_h) // stride + 1
        self.Wo = (W - pool_w) // stride + 1

    def flops(self) -> float:
        # one comparison per element in the pool window
        return float(self.N * self.C * self.Ho * self.Wo * self.pool_h * self.pool_w)

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return self.N * self.C * self.H * self.W * dtype_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.N * self.C * self.Ho * self.Wo * dtype_bytes


# ---------------------------------------------------------------------------
# Softmax
# ---------------------------------------------------------------------------

class SoftmaxOp(Op):
    """Softmax over a vector of length N_classes for batch_size samples."""

    def __init__(self, batch_size: int, n_classes: int, name: str = ''):
        super().__init__(name or f'Softmax_{batch_size}x{n_classes}')
        self.batch_size = batch_size
        self.n_classes = n_classes

    def flops(self) -> float:
        # exp + divide per element + one sum per row
        return float(self.batch_size * (5 * self.n_classes))

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return self.batch_size * self.n_classes * dtype_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.batch_size * self.n_classes * dtype_bytes


# ---------------------------------------------------------------------------
# Reshape (zero compute, only data re-layout)
# ---------------------------------------------------------------------------

class ReshapeOp(Op):
    """Reshape / transpose — zero FLOPs but may move data."""

    def __init__(self, total_elements: int, name: str = ''):
        super().__init__(name or f'Reshape_{total_elements}')
        self.total_elements = total_elements

    def flops(self) -> float:
        return 0.0

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return self.total_elements * dtype_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self.total_elements * dtype_bytes


# ---------------------------------------------------------------------------
# Passthrough (unknown / unsupported ops — still count bytes)
# ---------------------------------------------------------------------------

class PassthroughOp(Op):
    """
    Placeholder for unsupported or unknown operation types.
    Contributes memory traffic but zero compute FLOPs.
    """

    def __init__(self, input_bytes: float, output_bytes: float,
                 name: str = 'Unknown'):
        super().__init__(name)
        self._input_bytes = input_bytes
        self._output_bytes = output_bytes

    def flops(self) -> float:
        return 0.0

    def read_bytes(self, dtype_bytes: int = 2) -> float:
        return self._input_bytes

    def write_bytes(self, dtype_bytes: int = 2) -> float:
        return self._output_bytes


# ---------------------------------------------------------------------------
# Bridge helpers  —  convert existing model objects → Op instances
# ---------------------------------------------------------------------------

def gemm_layer_to_op(layer) -> GEMMOp:
    """
    Convert a simulator.models.workload.GEMMLayer to a GEMMOp.
    Reuses the same M, K, N math — no duplication.
    """
    return GEMMOp(M=layer.M, K=layer.K, N=layer.N, name=layer.name)


def conv_layer_to_op(layer) -> Conv2DOp:
    """
    Convert a simulator.models.workload.ConvLayer to a Conv2DOp.
    """
    return Conv2DOp(
        N=layer.N, C=layer.C, H=layer.H, W=layer.W,
        K=layer.K, R=layer.R, S=layer.S,
        stride=layer.stride, pad=layer.pad,
        name=layer.name,
    )


def workload_to_ops(workload) -> List[Op]:
    """
    Convert a simulator.models.workload.Workload into a list of Op objects.
    """
    ops = []
    for layer in workload.layers:
        cls_name = layer.__class__.__name__
        if cls_name == 'GEMMLayer':
            ops.append(gemm_layer_to_op(layer))
        elif cls_name == 'ConvLayer':
            ops.append(conv_layer_to_op(layer))
        else:
            # Unknown layer type → PassthroughOp with rough byte estimate
            ops.append(PassthroughOp(
                input_bytes=getattr(layer, 'input_bytes', 0),
                output_bytes=getattr(layer, 'output_bytes', 0),
                name=getattr(layer, 'name', cls_name),
            ))
    return ops
