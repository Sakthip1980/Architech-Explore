"""Precision configuration for compute and memory operations"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum


class PrecisionFormat(Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    FP8_E4M3 = "fp8_e4m3"
    FP8_E5M2 = "fp8_e5m2"
    INT8 = "int8"
    INT4 = "int4"


PRECISION_BYTES: Dict[PrecisionFormat, float] = {
    PrecisionFormat.FP32: 4.0,
    PrecisionFormat.FP16: 2.0,
    PrecisionFormat.BF16: 2.0,
    PrecisionFormat.FP8_E4M3: 1.0,
    PrecisionFormat.FP8_E5M2: 1.0,
    PrecisionFormat.INT8: 1.0,
    PrecisionFormat.INT4: 0.5,
}


class ParamStorageMode(Enum):
    AS_TENSOR_FORMAT = "as_tensor_format"
    TENSOR_PLUS_FP32_MASTER = "tensor_plus_fp32_master"
    FP32_PARAMS = "fp32_params"


@dataclass
class PrecisionConfig:
    """Precision configuration matching DeepFlow schema"""
    tensor_format: PrecisionFormat = PrecisionFormat.BF16
    mixed_precision: bool = False
    param_storage_mode: ParamStorageMode = ParamStorageMode.AS_TENSOR_FORMAT
    kv_cache_format: PrecisionFormat = PrecisionFormat.BF16
    
    def get_tensor_bytes(self) -> float:
        """Get bytes per tensor element"""
        return PRECISION_BYTES[self.tensor_format]
    
    def get_param_bytes(self) -> float:
        """Get bytes per parameter based on storage mode"""
        if self.param_storage_mode == ParamStorageMode.FP32_PARAMS:
            return 4.0
        return PRECISION_BYTES[self.tensor_format]
    
    def get_master_copy_bytes(self) -> float:
        """Get additional bytes for master copy (if any)"""
        if self.param_storage_mode == ParamStorageMode.TENSOR_PLUS_FP32_MASTER:
            return 4.0
        return 0.0
    
    def get_optimizer_state_bytes(self) -> float:
        """Get bytes per optimizer state (Adam: m, v)"""
        if self.mixed_precision:
            return 8.0  # 2 FP32 states
        return 2 * PRECISION_BYTES[self.tensor_format]
    
    def get_gradient_bytes(self) -> float:
        """Get bytes per gradient element"""
        if self.param_storage_mode == ParamStorageMode.FP32_PARAMS:
            return 4.0
        return PRECISION_BYTES[self.tensor_format]
    
    def get_activation_bytes(self) -> float:
        """Get bytes per activation element"""
        return PRECISION_BYTES[self.tensor_format]
    
    def get_kv_cache_bytes(self) -> float:
        """Get bytes per KV cache element"""
        return PRECISION_BYTES[self.kv_cache_format]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'tensor_format': self.tensor_format.value,
            'mixed_precision': self.mixed_precision,
            'param_storage_mode': self.param_storage_mode.value,
            'kv_cache_format': self.kv_cache_format.value,
            'tensor_bytes': self.get_tensor_bytes(),
            'param_bytes': self.get_param_bytes(),
        }


PRECISION_MODES: Dict[str, PrecisionConfig] = {
    'fp32': PrecisionConfig(
        tensor_format=PrecisionFormat.FP32,
        mixed_precision=False,
        param_storage_mode=ParamStorageMode.FP32_PARAMS,
    ),
    'fp16': PrecisionConfig(
        tensor_format=PrecisionFormat.FP16,
        mixed_precision=False,
        param_storage_mode=ParamStorageMode.AS_TENSOR_FORMAT,
    ),
    'bf16': PrecisionConfig(
        tensor_format=PrecisionFormat.BF16,
        mixed_precision=False,
        param_storage_mode=ParamStorageMode.AS_TENSOR_FORMAT,
    ),
    'mixed_fp16': PrecisionConfig(
        tensor_format=PrecisionFormat.FP16,
        mixed_precision=True,
        param_storage_mode=ParamStorageMode.TENSOR_PLUS_FP32_MASTER,
    ),
    'mixed_bf16': PrecisionConfig(
        tensor_format=PrecisionFormat.BF16,
        mixed_precision=True,
        param_storage_mode=ParamStorageMode.TENSOR_PLUS_FP32_MASTER,
    ),
    'fp8': PrecisionConfig(
        tensor_format=PrecisionFormat.FP8_E4M3,
        mixed_precision=True,
        param_storage_mode=ParamStorageMode.TENSOR_PLUS_FP32_MASTER,
    ),
    'int8': PrecisionConfig(
        tensor_format=PrecisionFormat.INT8,
        mixed_precision=False,
        param_storage_mode=ParamStorageMode.AS_TENSOR_FORMAT,
    ),
}
