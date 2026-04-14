"""
ArchSim - System Architecture Simulator
A modular simulation framework for exploring computer architecture designs

Subpackages (new)
-----------------
simulator.hardware  — self-consistent property system, Block hierarchy, Connections
simulator.workload  — Op types (GEMMOp, Conv2DOp, …), OpGraph
simulator.engine    — roofline, AnalyticalEngine, EventDrivenEngine
simulator.mapping   — LoopNest, DataflowMode, Mapper
simulator.power     — PowerDomainModel, SystemPowerModel
simulator.results   — SimResult, SensitivitySweep, visualization
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
from .models.systolic_array import SystolicArray, MemoryHierarchy

# Interconnects
from .models.interconnect import Interconnect
from .models.axi import AXIBus
from .models.pcie import PCIe
from .models.cxl import CXL

# Specialized
from .models.dma import DMAEngine
from .models.memory_controller import MemoryController

# Workloads (existing)
from .models.workload import (
    Workload, GEMMLayer, ConvLayer,
    get_resnet50_workload, get_gpt2_workload, get_llama7b_workload
)

# New subpackages — import lazily to avoid circular imports at module level
# Use: from simulator.hardware import Block, PropertySchema, block_from_module
# Use: from simulator.engine import AnalyticalEngine, EventDrivenEngine
# Use: from simulator.mapping import Mapper, DataflowMode
# Use: from simulator.power import SystemPowerModel
# Use: from simulator.results import SimResult, SensitivitySweep, plot_roofline

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
    'SystolicArray',
    'MemoryHierarchy',
    # Interconnects
    'Interconnect',
    'AXIBus',
    'PCIe',
    'CXL',
    # Specialized
    'DMAEngine',
    'MemoryController',
    # Workloads
    'Workload',
    'GEMMLayer',
    'ConvLayer',
    'get_resnet50_workload',
    'get_gpt2_workload',
    'get_llama7b_workload'
]
