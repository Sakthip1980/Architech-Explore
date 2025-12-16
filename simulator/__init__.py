"""
ArchSim - System Architecture Simulator
A modular simulation framework for exploring computer architecture designs
"""

from .system import System
from .base import Module, SimulationMetrics

# Memory Subsystem
from .models.dram import DRAM
from .models.hbm import HBM
from .models.cache import SRAMCache
from .models.nvm import NVM
from .models.scratchpad import Scratchpad

# Compute Units
from .models.cpu import CPU
from .models.gpu import GPU
from .models.npu import NPU
from .models.dsp import DSP

# Interconnects
from .models.interconnect import Interconnect
from .models.axi import AXIBus
from .models.pcie import PCIe
from .models.cxl import CXL

# Specialized
from .models.dma import DMAEngine
from .models.memory_controller import MemoryController

__all__ = [
    'System',
    'Module',
    'SimulationMetrics',
    # Memory
    'DRAM',
    'HBM', 
    'SRAMCache',
    'NVM',
    'Scratchpad',
    # Compute
    'CPU',
    'GPU',
    'NPU',
    'DSP',
    # Interconnects
    'Interconnect',
    'AXIBus',
    'PCIe',
    'CXL',
    # Specialized
    'DMAEngine',
    'MemoryController'
]
