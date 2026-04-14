"""
simulator.workload — Workload operation types and computation graphs

Public API
----------
Op               - abstract base for all ops
GEMMOp           - General Matrix Multiply
MatMulOp         - batched MatMul (delegates to GEMM)
Conv2DOp         - 2-D convolution (im2col → GEMM)
DepthwiseConv2DOp- depthwise separable convolution
AddOp            - element-wise addition
PoolingOp        - spatial pooling (max/avg)
SoftmaxOp        - softmax over class logits
ReshapeOp        - zero-FLOP reshape / transpose
PassthroughOp    - unknown/unsupported op placeholder

OpNode           - one node in the computation graph
OpGraph          - DAG of OpNodes with topological sort
CycleError       - raised when the graph has a cycle

gemm_layer_to_op   - bridge: GEMMLayer → GEMMOp
conv_layer_to_op   - bridge: ConvLayer → Conv2DOp
workload_to_ops    - bridge: Workload → List[Op]
"""

from .ops import (
    Op,
    GEMMOp,
    MatMulOp,
    Conv2DOp,
    DepthwiseConv2DOp,
    AddOp,
    PoolingOp,
    SoftmaxOp,
    ReshapeOp,
    PassthroughOp,
    gemm_layer_to_op,
    conv_layer_to_op,
    workload_to_ops,
)
from .graph import OpNode, OpGraph, CycleError
from .tflite_parser import TFLiteParser

__all__ = [
    'Op', 'GEMMOp', 'MatMulOp', 'Conv2DOp', 'DepthwiseConv2DOp',
    'AddOp', 'PoolingOp', 'SoftmaxOp', 'ReshapeOp', 'PassthroughOp',
    'gemm_layer_to_op', 'conv_layer_to_op', 'workload_to_ops',
    'OpNode', 'OpGraph', 'CycleError',
    'TFLiteParser',
]
