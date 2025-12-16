"""Hardware and model configuration presets"""
from .hardware_presets import HardwareConfig, get_hardware_preset, HARDWARE_PRESETS
from .model_presets import ModelConfig, get_model_preset, MODEL_PRESETS
from .precision import PrecisionConfig, PRECISION_MODES
from .parallelism import ParallelismConfig, PARALLELISM_PRESETS
from .network import NetworkConfig, NetworkTopology, NETWORK_PRESETS

__all__ = [
    'HardwareConfig',
    'get_hardware_preset',
    'HARDWARE_PRESETS',
    'ModelConfig', 
    'get_model_preset',
    'MODEL_PRESETS',
    'PrecisionConfig',
    'PRECISION_MODES',
    'ParallelismConfig',
    'PARALLELISM_PRESETS',
    'NetworkConfig',
    'NetworkTopology',
    'NETWORK_PRESETS',
]
