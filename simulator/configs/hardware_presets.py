"""Hardware configuration presets based on DeepFlow and Astra-Sim reference configs"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class DataflowMode(Enum):
    WEIGHT_STATIONARY = "WS"
    OUTPUT_STATIONARY = "OS"
    INPUT_STATIONARY = "IS"
    ACTIVATION_STATIONARY = "AS"
    BEST = "best"


@dataclass
class MemoryLevelConfig:
    """Configuration for a single memory level"""
    name: str
    size_bytes: int
    bandwidth_gbps: float
    energy_per_bit_pj: float = 0.0
    latency_ns: float = 0.0
    util: float = 1.0
    scope: str = "global"  # mcu, mcu-bundle, global


@dataclass
class CoreConfig:
    """Compute core configuration (tensor cores, systolic array)"""
    operating_frequency_hz: float = 1.0e9
    num_bundles: int = 1  # SMs, compute units
    num_mcu_per_bundle: int = 4  # tensor cores per SM
    nominal_flop_rate_per_mcu: int = 512  # FLOPs per cycle per MCU
    energy_per_flop_j: float = 1.8e-13
    fma_d1: int = 8  # matrix multiply tile dimensions
    fma_d2: int = 4
    dataflow: DataflowMode = DataflowMode.OUTPUT_STATIONARY
    util: float = 1.0


@dataclass
class NetworkLinkConfig:
    """Network link configuration"""
    bandwidth_gbps: float = 400.0
    latency_ns: float = 5000.0
    util: float = 1.0


@dataclass
class HardwareConfig:
    """Complete hardware configuration matching DeepFlow schema"""
    name: str
    core: CoreConfig
    memory_hierarchy: Dict[str, MemoryLevelConfig]
    intra_node_network: NetworkLinkConfig
    inter_node_network: NetworkLinkConfig
    num_devices_per_node: int = 1
    num_nodes: int = 1
    
    def get_peak_tflops(self) -> float:
        """Calculate peak throughput in TFLOPS"""
        flops_per_cycle = (
            self.core.num_bundles * 
            self.core.num_mcu_per_bundle * 
            self.core.nominal_flop_rate_per_mcu
        )
        ops_per_second = flops_per_cycle * self.core.operating_frequency_hz
        return ops_per_second / 1e12
    
    def get_memory_bandwidth_gbps(self) -> float:
        """Get DRAM/HBM bandwidth"""
        if 'l3' in self.memory_hierarchy:
            return self.memory_hierarchy['l3'].bandwidth_gbps
        return 0.0
    
    def get_total_memory_bytes(self) -> int:
        """Get total DRAM/HBM capacity"""
        if 'l3' in self.memory_hierarchy:
            return self.memory_hierarchy['l3'].size_bytes
        return 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'peak_tflops': self.get_peak_tflops(),
            'memory_gb': self.get_total_memory_bytes() / (1024**3),
            'memory_bandwidth_gbps': self.get_memory_bandwidth_gbps(),
            'num_devices': self.num_devices_per_node * self.num_nodes,
            'frequency_ghz': self.core.operating_frequency_hz / 1e9,
            'dataflow': self.core.dataflow.value,
        }


# =============================================================================
# Hardware Presets (based on DeepFlow configs)
# =============================================================================

def _nvidia_a100_80gb() -> HardwareConfig:
    """NVIDIA A100 80GB SXM configuration"""
    return HardwareConfig(
        name="NVIDIA A100 80GB",
        core=CoreConfig(
            operating_frequency_hz=1.41e9,
            num_bundles=108,  # SMs
            num_mcu_per_bundle=4,  # tensor cores per SM
            nominal_flop_rate_per_mcu=512,
            energy_per_flop_j=1.8e-13,
            fma_d1=8,
            fma_d2=4,
            dataflow=DataflowMode.BEST,
            util=1.0,
        ),
        memory_hierarchy={
            'l0': MemoryLevelConfig(
                name="Register File",
                size_bytes=27 * 1024 * 1024,  # 27 MB
                bandwidth_gbps=122000,  # 122 TB/s
                energy_per_bit_pj=0.11,
                latency_ns=0,
                scope="mcu",
            ),
            'l1': MemoryLevelConfig(
                name="Shared Memory (L1)",
                size_bytes=20736 * 1024,  # 20.7 MB
                bandwidth_gbps=18000,  # 18 TB/s
                energy_per_bit_pj=0.13,
                latency_ns=0,
                scope="mcu-bundle",
            ),
            'l2': MemoryLevelConfig(
                name="L2 Cache",
                size_bytes=40 * 1024 * 1024,  # 40 MB
                bandwidth_gbps=7050,
                energy_per_bit_pj=0.13,
                latency_ns=0,
                scope="global",
            ),
            'l3': MemoryLevelConfig(
                name="HBM2e",
                size_bytes=80 * 1024 * 1024 * 1024,  # 80 GB
                bandwidth_gbps=1986,
                energy_per_bit_pj=4.5,
                latency_ns=100,
                scope="global",
            ),
        },
        intra_node_network=NetworkLinkConfig(bandwidth_gbps=400, latency_ns=5000, util=1.0),
        inter_node_network=NetworkLinkConfig(bandwidth_gbps=400, latency_ns=5000, util=0.96),
        num_devices_per_node=8,
        num_nodes=1,
    )


def _nvidia_h100_sxm5_80gb() -> HardwareConfig:
    """NVIDIA H100 SXM5 80GB configuration"""
    return HardwareConfig(
        name="NVIDIA H100 SXM5 80GB",
        core=CoreConfig(
            operating_frequency_hz=1.98e9,
            num_bundles=132,  # SMs
            num_mcu_per_bundle=4,  # tensor cores per SM
            nominal_flop_rate_per_mcu=1024,  # Higher than A100
            energy_per_flop_j=1.8e-13,
            fma_d1=8,
            fma_d2=4,
            dataflow=DataflowMode.BEST,
            util=0.75,
        ),
        memory_hierarchy={
            'l0': MemoryLevelConfig(
                name="Register File",
                size_bytes=33 * 1024 * 1024,  # 33 MB
                bandwidth_gbps=244000,  # 244 TB/s
                energy_per_bit_pj=0.11,
                latency_ns=0,
                scope="mcu",
            ),
            'l1': MemoryLevelConfig(
                name="Shared Memory (L1)",
                size_bytes=30096 * 1024,  # ~30 MB
                bandwidth_gbps=22392,
                energy_per_bit_pj=0.13,
                latency_ns=0,
                scope="mcu-bundle",
            ),
            'l2': MemoryLevelConfig(
                name="L2 Cache",
                size_bytes=50 * 1024 * 1024,  # 50 MB
                bandwidth_gbps=8138,
                energy_per_bit_pj=0.13,
                latency_ns=0,
                scope="global",
            ),
            'l3': MemoryLevelConfig(
                name="HBM3",
                size_bytes=80 * 1024 * 1024 * 1024,  # 80 GB
                bandwidth_gbps=3440,
                energy_per_bit_pj=4.5,
                latency_ns=100,
                scope="global",
            ),
        },
        intra_node_network=NetworkLinkConfig(bandwidth_gbps=400, latency_ns=5000, util=1.0),
        inter_node_network=NetworkLinkConfig(bandwidth_gbps=400, latency_ns=5000, util=0.96),
        num_devices_per_node=8,
        num_nodes=1,
    )


def _nvidia_v100() -> HardwareConfig:
    """NVIDIA V100 32GB configuration"""
    return HardwareConfig(
        name="NVIDIA V100 32GB",
        core=CoreConfig(
            operating_frequency_hz=1.38e9,
            num_bundles=80,  # SMs
            num_mcu_per_bundle=8,  # tensor cores per SM
            nominal_flop_rate_per_mcu=128,
            energy_per_flop_j=2.0e-13,
            fma_d1=4,
            fma_d2=4,
            dataflow=DataflowMode.OUTPUT_STATIONARY,
            util=1.0,
        ),
        memory_hierarchy={
            'l0': MemoryLevelConfig(
                name="Register File",
                size_bytes=20 * 1024 * 1024,
                bandwidth_gbps=100000,
                energy_per_bit_pj=0.11,
                latency_ns=0,
                scope="mcu",
            ),
            'l1': MemoryLevelConfig(
                name="Shared Memory (L1)",
                size_bytes=6 * 1024 * 1024,
                bandwidth_gbps=12000,
                energy_per_bit_pj=0.15,
                latency_ns=0,
                scope="mcu-bundle",
            ),
            'l2': MemoryLevelConfig(
                name="L2 Cache",
                size_bytes=6 * 1024 * 1024,
                bandwidth_gbps=3000,
                energy_per_bit_pj=0.15,
                latency_ns=0,
                scope="global",
            ),
            'l3': MemoryLevelConfig(
                name="HBM2",
                size_bytes=32 * 1024 * 1024 * 1024,  # 32 GB
                bandwidth_gbps=900,
                energy_per_bit_pj=5.0,
                latency_ns=100,
                scope="global",
            ),
        },
        intra_node_network=NetworkLinkConfig(bandwidth_gbps=300, latency_ns=5000, util=1.0),
        inter_node_network=NetworkLinkConfig(bandwidth_gbps=100, latency_ns=10000, util=0.9),
        num_devices_per_node=8,
        num_nodes=1,
    )


def _google_tpu_v3() -> HardwareConfig:
    """Google TPU v3 configuration"""
    return HardwareConfig(
        name="Google TPU v3",
        core=CoreConfig(
            operating_frequency_hz=0.94e9,
            num_bundles=2,  # MXUs
            num_mcu_per_bundle=1,
            nominal_flop_rate_per_mcu=65536,  # 128x128 systolic array
            energy_per_flop_j=1.5e-13,
            fma_d1=128,
            fma_d2=128,
            dataflow=DataflowMode.OUTPUT_STATIONARY,
            util=1.0,
        ),
        memory_hierarchy={
            'l0': MemoryLevelConfig(
                name="Unified Buffer",
                size_bytes=32 * 1024 * 1024,  # 32 MB
                bandwidth_gbps=700,
                energy_per_bit_pj=0.5,
                latency_ns=0,
                scope="global",
            ),
            'l1': MemoryLevelConfig(
                name="Weight FIFO",
                size_bytes=4 * 1024 * 1024,
                bandwidth_gbps=2000,
                energy_per_bit_pj=0.3,
                latency_ns=0,
                scope="mcu",
            ),
            'l2': MemoryLevelConfig(
                name="Accumulator",
                size_bytes=4 * 1024 * 1024,
                bandwidth_gbps=2000,
                energy_per_bit_pj=0.3,
                latency_ns=0,
                scope="mcu",
            ),
            'l3': MemoryLevelConfig(
                name="HBM",
                size_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
                bandwidth_gbps=900,
                energy_per_bit_pj=5.0,
                latency_ns=100,
                scope="global",
            ),
        },
        intra_node_network=NetworkLinkConfig(bandwidth_gbps=656, latency_ns=1000, util=1.0),
        inter_node_network=NetworkLinkConfig(bandwidth_gbps=656, latency_ns=5000, util=0.95),
        num_devices_per_node=8,
        num_nodes=1,
    )


def _custom_systolic_array() -> HardwareConfig:
    """Configurable custom systolic array accelerator"""
    return HardwareConfig(
        name="Custom Systolic Array",
        core=CoreConfig(
            operating_frequency_hz=1.0e9,
            num_bundles=1,
            num_mcu_per_bundle=1,
            nominal_flop_rate_per_mcu=131072,  # 256x256 array
            energy_per_flop_j=1.0e-13,
            fma_d1=256,
            fma_d2=256,
            dataflow=DataflowMode.OUTPUT_STATIONARY,
            util=1.0,
        ),
        memory_hierarchy={
            'l0': MemoryLevelConfig(
                name="Scratchpad L0",
                size_bytes=256 * 1024,  # 256 KB
                bandwidth_gbps=512,
                energy_per_bit_pj=0.1,
                latency_ns=0,
                scope="mcu",
            ),
            'l1': MemoryLevelConfig(
                name="Scratchpad L1",
                size_bytes=2 * 1024 * 1024,  # 2 MB
                bandwidth_gbps=256,
                energy_per_bit_pj=0.2,
                latency_ns=1,
                scope="mcu-bundle",
            ),
            'l2': MemoryLevelConfig(
                name="SRAM Buffer",
                size_bytes=16 * 1024 * 1024,  # 16 MB
                bandwidth_gbps=128,
                energy_per_bit_pj=0.5,
                latency_ns=5,
                scope="global",
            ),
            'l3': MemoryLevelConfig(
                name="HBM",
                size_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
                bandwidth_gbps=1024,
                energy_per_bit_pj=4.0,
                latency_ns=50,
                scope="global",
            ),
        },
        intra_node_network=NetworkLinkConfig(bandwidth_gbps=100, latency_ns=1000, util=1.0),
        inter_node_network=NetworkLinkConfig(bandwidth_gbps=100, latency_ns=5000, util=0.9),
        num_devices_per_node=1,
        num_nodes=1,
    )


HARDWARE_PRESETS: Dict[str, HardwareConfig] = {
    'a100_80gb': _nvidia_a100_80gb(),
    'h100_sxm5_80gb': _nvidia_h100_sxm5_80gb(),
    'v100_32gb': _nvidia_v100(),
    'tpu_v3': _google_tpu_v3(),
    'custom': _custom_systolic_array(),
}


def get_hardware_preset(name: str) -> HardwareConfig:
    """Get a hardware configuration preset by name"""
    if name not in HARDWARE_PRESETS:
        available = list(HARDWARE_PRESETS.keys())
        raise ValueError(f"Unknown hardware preset '{name}'. Available: {available}")
    return HARDWARE_PRESETS[name]
