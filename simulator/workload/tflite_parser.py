"""
TFLite model parser — converts a .tflite flatbuffer file into an OpGraph.

No tensorflow dependency required. Uses the `flatbuffers` Python library
(pip install flatbuffers) plus the TFLite schema encoded directly below
as a minimal pure-Python decoder.

Usage
-----
    from simulator.workload.tflite_parser import TFLiteParser

    graph = TFLiteParser('mobilenet_v1.tflite').parse()
    print(graph)
    # OpGraph('mobilenet_v1', 31 ops, 5.68e+08 FLOPs)

Shape Inference
---------------
After loading the op graph we run a forward shape-inference pass that
fills output shapes from input shapes + operator parameters. This lets
us compute FLOPs and bytes for each op.

Supported opcodes (mapped to Op subclasses):
  CONV_2D              -> Conv2DOp
  DEPTHWISE_CONV_2D    -> DepthwiseConv2DOp
  FULLY_CONNECTED      -> GEMMOp
  AVERAGE_POOL_2D      -> PoolingOp
  MAX_POOL_2D          -> PoolingOp
  ADD                  -> AddOp
  SOFTMAX              -> SoftmaxOp
  RESHAPE              -> ReshapeOp
  All others           -> PassthroughOp
"""

import struct
import os
from typing import List, Dict, Optional, Tuple, Any

from .ops import (
    Op, GEMMOp, Conv2DOp, DepthwiseConv2DOp,
    AddOp, PoolingOp, SoftmaxOp, ReshapeOp, PassthroughOp
)
from .graph import OpGraph, OpNode


# ---------------------------------------------------------------------------
# TFLite opcode constants (from tensorflow/lite/schema/schema_generated.h)
# Only the opcodes we actually handle are listed.
# ---------------------------------------------------------------------------

class BuiltinOperator:
    ADD                 = 0
    AVERAGE_POOL_2D     = 1
    CONV_2D             = 3
    DEPTHWISE_CONV_2D   = 4
    FULLY_CONNECTED     = 9
    MAX_POOL_2D         = 17
    RESHAPE             = 22
    SOFTMAX             = 25
    CONCATENATION       = 2
    MUL                 = 18
    RELU                = 19
    RELU6               = 21
    LOGISTIC            = 14
    BATCH_MATMUL        = 126
    MEAN                = 40


class ActivationFunctionType:
    NONE  = 0
    RELU  = 1
    RELU6 = 3


# ---------------------------------------------------------------------------
# Minimal flatbuffer reader (enough to parse TFLite Model table)
# ---------------------------------------------------------------------------

class _FlatbufferReader:
    """
    Ultra-minimal flatbuffer reader for TFLite Model.

    TFLite uses flatbuffers for serialisation. Rather than generating
    full Python bindings from the schema (which requires the flatc tool),
    this reader implements only the subset of the flatbuffer wire format
    needed to decode the TFLite Model table.

    References:
      - https://flatbuffers.dev/flatbuffers_internals/
      - tensorflow/lite/schema/schema.fbs (TFLite schema)
    """

    def __init__(self, data: bytes):
        self._data = data
        self._n = len(data)

    def _u8(self, pos: int) -> int:
        return self._data[pos]

    def _u16(self, pos: int) -> int:
        return struct.unpack_from('<H', self._data, pos)[0]

    def _u32(self, pos: int) -> int:
        return struct.unpack_from('<I', self._data, pos)[0]

    def _i32(self, pos: int) -> int:
        return struct.unpack_from('<i', self._data, pos)[0]

    def _follow_ref(self, pos: int) -> int:
        """Follow a flatbuffer reference (offset from current position)."""
        offset = self._i32(pos)
        return pos + offset

    def _table(self, pos: int) -> '_Table':
        """Access a table at the given absolute position."""
        return _Table(self._data, pos)


class _Table:
    """Minimal flatbuffer table accessor."""

    def __init__(self, data: bytes, pos: int):
        self._data = data
        self._pos = pos
        # vtable offset: int32 at pos, follows to vtable
        vtable_offset = struct.unpack_from('<i', data, pos)[0]
        self._vtable_pos = pos - vtable_offset
        vtable_size = struct.unpack_from('<H', data, self._vtable_pos)[0]
        self._field_offsets: Dict[int, int] = {}
        # Each field slot is a uint16 at vtable_pos + 4 + field_id*2
        for i in range((vtable_size - 4) // 2):
            off = struct.unpack_from('<H', data, self._vtable_pos + 4 + i * 2)[0]
            if off != 0:
                self._field_offsets[i] = off

    def _get_field_pos(self, field_id: int) -> Optional[int]:
        off = self._field_offsets.get(field_id)
        if off is None:
            return None
        return self._pos + off

    def _int32(self, field_id: int, default: int = 0) -> int:
        p = self._get_field_pos(field_id)
        if p is None:
            return default
        return struct.unpack_from('<i', self._data, p)[0]

    def _uint32(self, field_id: int, default: int = 0) -> int:
        p = self._get_field_pos(field_id)
        if p is None:
            return default
        return struct.unpack_from('<I', self._data, p)[0]

    def _int8(self, field_id: int, default: int = 0) -> int:
        p = self._get_field_pos(field_id)
        if p is None:
            return default
        return struct.unpack_from('<b', self._data, p)[0]

    def _uint8(self, field_id: int, default: int = 0) -> int:
        p = self._get_field_pos(field_id)
        if p is None:
            return default
        return struct.unpack_from('<B', self._data, p)[0]

    def _bool(self, field_id: int, default: bool = False) -> bool:
        p = self._get_field_pos(field_id)
        if p is None:
            return default
        return bool(self._data[p])

    def _string(self, field_id: int) -> Optional[str]:
        p = self._get_field_pos(field_id)
        if p is None:
            return None
        # String: follow offset to a uint32 length + utf8 bytes
        ref = p + struct.unpack_from('<i', self._data, p)[0]
        length = struct.unpack_from('<I', self._data, ref)[0]
        return self._data[ref + 4: ref + 4 + length].decode('utf-8', errors='replace')

    def _vector_of_tables(self, field_id: int) -> List['_Table']:
        p = self._get_field_pos(field_id)
        if p is None:
            return []
        ref = p + struct.unpack_from('<i', self._data, p)[0]
        count = struct.unpack_from('<I', self._data, ref)[0]
        tables = []
        for i in range(count):
            item_pos = ref + 4 + i * 4
            item_ref = item_pos + struct.unpack_from('<i', self._data, item_pos)[0]
            tables.append(_Table(self._data, item_ref))
        return tables

    def _vector_of_int32(self, field_id: int) -> List[int]:
        p = self._get_field_pos(field_id)
        if p is None:
            return []
        ref = p + struct.unpack_from('<i', self._data, p)[0]
        count = struct.unpack_from('<I', self._data, ref)[0]
        return list(struct.unpack_from(f'<{count}i', self._data, ref + 4))

    def _vector_of_uint8(self, field_id: int) -> bytes:
        p = self._get_field_pos(field_id)
        if p is None:
            return b''
        ref = p + struct.unpack_from('<i', self._data, p)[0]
        count = struct.unpack_from('<I', self._data, ref)[0]
        return bytes(self._data[ref + 4: ref + 4 + count])

    def _nested_table(self, field_id: int) -> Optional['_Table']:
        p = self._get_field_pos(field_id)
        if p is None:
            return None
        ref = p + struct.unpack_from('<i', self._data, p)[0]
        return _Table(self._data, ref)


# ---------------------------------------------------------------------------
# TFLiteParser
# ---------------------------------------------------------------------------

class TFLiteParser:
    """
    Parse a .tflite file into an OpGraph.

    Parameters
    ----------
    path : path to the .tflite model file
    """

    def __init__(self, path: str):
        self.path = path
        with open(path, 'rb') as f:
            self._data = f.read()

    def parse(self) -> OpGraph:
        """
        Parse the TFLite flatbuffer and return an OpGraph.

        The graph is named after the model file (basename without extension).
        """
        model_name = os.path.splitext(os.path.basename(self.path))[0]

        # TFLite flatbuffer root starts at offset stored at byte 4
        root_offset = struct.unpack_from('<I', self._data, 4)[0]
        model_table = _Table(self._data, root_offset)

        # Model fields:
        #   field 0: version (uint32)
        #   field 1: operator_codes (vector of tables)
        #   field 2: subgraphs (vector of tables)
        #   field 3: description (string)
        #   field 4: buffers (vector of tables)
        version = model_table._uint32(0, 0)
        op_code_tables = model_table._vector_of_tables(1)
        subgraph_tables = model_table._vector_of_tables(2)

        if not subgraph_tables:
            raise ValueError("TFLite model has no subgraphs")

        # Build opcode → BuiltinOperator mapping
        opcode_map = self._build_opcode_map(op_code_tables)

        # Parse first subgraph (primary inference graph)
        subgraph = subgraph_tables[0]
        graph = self._parse_subgraph(subgraph, opcode_map, model_name)
        return graph

    def _build_opcode_map(self, op_code_tables: List[_Table]) -> Dict[int, int]:
        """
        Build index → builtin_code mapping.

        OperatorCode table fields:
          field 0: builtin_code (int8, deprecated but still present)
          field 3: builtin_code (int32, preferred for >= 127)
        """
        result: Dict[int, int] = {}
        for i, t in enumerate(op_code_tables):
            # Try int32 field first (field 3), fall back to int8 (field 0)
            code_i32 = t._int32(3, -1)
            code_i8  = t._int8(0, 0)
            code = code_i32 if code_i32 >= 0 else int(code_i8)
            result[i] = code
        return result

    def _parse_subgraph(
        self,
        subgraph: _Table,
        opcode_map: Dict[int, int],
        name: str,
    ) -> OpGraph:
        """
        Parse one TFLite subgraph into an OpGraph.

        Subgraph fields:
          field 0: tensors (vector of Tensor tables)
          field 1: inputs (vector of int32 tensor indices)
          field 2: outputs (vector of int32 tensor indices)
          field 3: operators (vector of Operator tables)
          field 4: name (string)
        """
        tensor_tables = subgraph._vector_of_tables(0)
        operator_tables = subgraph._vector_of_tables(3)
        sg_name = subgraph._string(4) or name

        # Build tensor metadata: index → {shape, dtype}
        tensors = self._parse_tensors(tensor_tables)

        # Build OpGraph with shape inference
        graph = OpGraph(sg_name)
        nodes: List[OpNode] = []
        tensor_producers: Dict[int, OpNode] = {}   # tensor_idx → node that writes it

        for op_table in operator_tables:
            op_code_idx = op_table._uint32(0)          # field 0: opcode_index
            inputs_raw  = op_table._vector_of_int32(1) # field 1: inputs (tensor indices)
            outputs_raw = op_table._vector_of_int32(2) # field 2: outputs
            builtin_options = op_table._nested_table(3) # field 3: builtin_options

            builtin_code = opcode_map.get(op_code_idx, -1)

            # Determine input dependencies (nodes that must run first)
            input_nodes = []
            for t_idx in inputs_raw:
                if t_idx >= 0 and t_idx in tensor_producers:
                    producer = tensor_producers[t_idx]
                    if producer not in input_nodes:
                        input_nodes.append(producer)

            # Build the Op
            op = self._build_op(
                builtin_code, inputs_raw, outputs_raw,
                tensors, builtin_options
            )

            node = graph.add_op(op, inputs=input_nodes)
            nodes.append(node)

            # Register tensor producers
            for t_idx in outputs_raw:
                if t_idx >= 0:
                    tensor_producers[t_idx] = node

        return graph

    def _parse_tensors(self, tensor_tables: List[_Table]) -> Dict[int, Dict]:
        """
        Build tensor metadata dictionary.

        Tensor fields:
          field 0: shape (vector of int32)
          field 1: type  (uint8: TensorType enum)
          field 2: buffer (uint32 buffer index)
          field 3: name (string)
          field 4: quantization
          field 5: is_variable
          field 6: shape_signature (vector of int32)
        """
        tensors: Dict[int, Dict] = {}
        for i, t in enumerate(tensor_tables):
            shape = t._vector_of_int32(0)
            dtype = t._uint8(1, 0)   # 0=float32, 1=float16, 2=int32, 3=uint8, 9=int8
            tensors[i] = {
                'shape': shape,
                'dtype': dtype,
                'dtype_bytes': _tflite_dtype_bytes(dtype),
            }
        return tensors

    def _build_op(
        self,
        builtin_code: int,
        inputs: List[int],
        outputs: List[int],
        tensors: Dict[int, Dict],
        options: Optional[_Table],
    ) -> Op:
        """Dispatch on builtin_code and construct the appropriate Op."""

        def _shape(t_idx: int) -> List[int]:
            if t_idx < 0 or t_idx not in tensors:
                return []
            return tensors[t_idx]['shape']

        def _dtype_bytes(t_idx: int) -> int:
            if t_idx < 0 or t_idx not in tensors:
                return 4
            return tensors[t_idx]['dtype_bytes']

        def _numel(shape: List[int]) -> int:
            r = 1
            for d in shape:
                r *= max(d, 1)
            return r

        try:
            if builtin_code == BuiltinOperator.CONV_2D:
                return self._build_conv2d(inputs, outputs, tensors, options)

            elif builtin_code == BuiltinOperator.DEPTHWISE_CONV_2D:
                return self._build_dw_conv2d(inputs, outputs, tensors, options)

            elif builtin_code == BuiltinOperator.FULLY_CONNECTED:
                return self._build_fc(inputs, outputs, tensors)

            elif builtin_code == BuiltinOperator.BATCH_MATMUL:
                return self._build_batch_matmul(inputs, outputs, tensors)

            elif builtin_code in (BuiltinOperator.AVERAGE_POOL_2D,
                                   BuiltinOperator.MAX_POOL_2D):
                return self._build_pooling(inputs, outputs, tensors, options)

            elif builtin_code in (BuiltinOperator.ADD, BuiltinOperator.MUL):
                out_shape = _shape(outputs[0]) if outputs else []
                n_elems = _numel(out_shape)
                return AddOp(n_elems, name=f'Add_{n_elems}')

            elif builtin_code == BuiltinOperator.SOFTMAX:
                out_shape = _shape(outputs[0]) if outputs else []
                n_elems = _numel(out_shape)
                return SoftmaxOp(1, n_elems, name=f'Softmax_{n_elems}')

            elif builtin_code == BuiltinOperator.RESHAPE:
                in_shape = _shape(inputs[0]) if inputs else []
                return ReshapeOp(_numel(in_shape), name=f'Reshape_{_numel(in_shape)}')

            else:
                # Unknown op → PassthroughOp
                in_bytes  = sum(_numel(_shape(t)) * _dtype_bytes(t) for t in inputs  if t >= 0)
                out_bytes = sum(_numel(_shape(t)) * _dtype_bytes(t) for t in outputs if t >= 0)
                return PassthroughOp(in_bytes, out_bytes,
                                     name=f'Op_{builtin_code}')

        except Exception:
            # Shape inference failure: use PassthroughOp with zero bytes
            return PassthroughOp(0, 0, name=f'Op_{builtin_code}_err')

    def _build_conv2d(self, inputs, outputs, tensors, options) -> Conv2DOp:
        """
        CONV_2D: input[N,H,W,C_in], weight[C_out,Kh,Kw,C_in], output[N,Ho,Wo,C_out]

        Options fields (Conv2DOptions):
          field 0: padding (uint8: SAME=0, VALID=1)
          field 1: stride_w (int32)
          field 2: stride_h (int32)
          field 3: dilation_w_factor (int32, default=1)
          field 4: dilation_h_factor (int32, default=1)
          field 5: fused_activation_function (int8)
        """
        in_shape = tensors.get(inputs[0], {}).get('shape', [1,1,1,1])
        w_shape  = tensors.get(inputs[1], {}).get('shape', [1,1,1,1])

        N  = in_shape[0] if len(in_shape) > 0 else 1
        H  = in_shape[1] if len(in_shape) > 1 else 1
        W  = in_shape[2] if len(in_shape) > 2 else 1
        Ci = in_shape[3] if len(in_shape) > 3 else 1

        Co  = w_shape[0] if len(w_shape) > 0 else 1
        Kh  = w_shape[1] if len(w_shape) > 1 else 1
        Kw  = w_shape[2] if len(w_shape) > 2 else 1

        stride_w = options._int32(1, 1) if options else 1
        stride_h = options._int32(2, 1) if options else 1
        pad_code = options._int32(0, 0) if options else 0  # 0=SAME,1=VALID
        pad = 0 if pad_code == 1 else Kh // 2   # approximate

        return Conv2DOp(N=N, C=Ci, H=H, W=W, K=Co, R=Kh, S=Kw,
                        stride=max(stride_h, stride_w), pad=pad)

    def _build_dw_conv2d(self, inputs, outputs, tensors, options) -> DepthwiseConv2DOp:
        in_shape = tensors.get(inputs[0], {}).get('shape', [1,1,1,1])
        w_shape  = tensors.get(inputs[1], {}).get('shape', [1,1,1,1])

        N  = in_shape[0] if len(in_shape) > 0 else 1
        H  = in_shape[1] if len(in_shape) > 1 else 1
        W  = in_shape[2] if len(in_shape) > 2 else 1
        C  = in_shape[3] if len(in_shape) > 3 else 1

        Kh = w_shape[1] if len(w_shape) > 1 else 1
        Kw = w_shape[2] if len(w_shape) > 2 else 1

        stride_w = options._int32(1, 1) if options else 1
        stride_h = options._int32(2, 1) if options else 1
        pad_code = options._int32(0, 0) if options else 0
        pad = 0 if pad_code == 1 else Kh // 2

        return DepthwiseConv2DOp(N=N, C=C, H=H, W=W, R=Kh, S=Kw,
                                  stride=max(stride_h, stride_w), pad=pad)

    def _build_fc(self, inputs, outputs, tensors) -> GEMMOp:
        """FullyConnected: input[batch, K], weight[N, K], output[batch, N]"""
        in_shape = tensors.get(inputs[0], {}).get('shape', [1, 1])
        w_shape  = tensors.get(inputs[1], {}).get('shape', [1, 1])

        M = in_shape[0] if len(in_shape) > 0 else 1
        K = in_shape[-1] if len(in_shape) > 1 else 1
        N = w_shape[0]  if len(w_shape)  > 0 else 1

        return GEMMOp(M=M, K=K, N=N)

    def _build_batch_matmul(self, inputs, outputs, tensors) -> GEMMOp:
        """BatchMatMul: A[...,M,K] x B[...,K,N]"""
        a_shape = tensors.get(inputs[0], {}).get('shape', [1, 1, 1])
        b_shape = tensors.get(inputs[1], {}).get('shape', [1, 1, 1])

        batch = a_shape[0] if len(a_shape) > 2 else 1
        M = a_shape[-2] if len(a_shape) > 1 else 1
        K = a_shape[-1] if len(a_shape) > 0 else 1
        N = b_shape[-1] if len(b_shape) > 0 else 1

        return GEMMOp(M=batch * M, K=K, N=N, name=f'BatchMatMul_B{batch}M{M}K{K}N{N}')

    def _build_pooling(self, inputs, outputs, tensors, options) -> PoolingOp:
        in_shape  = tensors.get(inputs[0],  {}).get('shape', [1,1,1,1])
        out_shape = tensors.get(outputs[0], {}).get('shape', [1,1,1,1]) if outputs else in_shape

        N = in_shape[0] if len(in_shape) > 0 else 1
        H = in_shape[1] if len(in_shape) > 1 else 1
        W = in_shape[2] if len(in_shape) > 2 else 1
        C = in_shape[3] if len(in_shape) > 3 else 1

        oH = out_shape[1] if len(out_shape) > 1 else 1
        oW = out_shape[2] if len(out_shape) > 2 else 1

        filter_h = options._int32(1, 1) if options else H // max(oH, 1)
        filter_w = options._int32(2, 1) if options else W // max(oW, 1)
        stride   = options._int32(3, 1) if options else 1

        return PoolingOp(N=N, C=C, H=H, W=W,
                         pool_h=max(filter_h, 1), pool_w=max(filter_w, 1),
                         stride=max(stride, 1))


def _tflite_dtype_bytes(dtype_code: int) -> int:
    """TFLite TensorType → element size in bytes."""
    return {
        0: 4,   # FLOAT32
        1: 2,   # FLOAT16
        2: 4,   # INT32
        3: 1,   # UINT8
        4: 8,   # INT64
        5: 1,   # STRING (treat as 1 byte)
        6: 1,   # BOOL
        7: 2,   # INT16
        8: 8,   # COMPLEX64
        9: 1,   # INT8
        10: 4,  # FLOAT64
        11: 8,  # COMPLEX128
        14: 1,  # UINT4
        15: 1,  # INT4
    }.get(dtype_code, 4)
