"""NPU (Neural Processing Unit) / AI Accelerator model"""
from typing import Dict, Any, Optional
from ..base import Module


class NPU(Module):
    """
    Neural Processing Unit / AI Accelerator model.
    
    Characteristics:
    - High MAC (Multiply-Accumulate) throughput
    - Support for multiple precisions (INT8, FP16, FP32)
    - On-chip SRAM for weights/activations
    - Optimized for inference or training
    """
    
    def __init__(
        self,
        name: str = "NPU",
        mac_units: int = 4096,
        frequency_ghz: float = 1.0,
        precision: str = "INT8",  # INT8, FP16, BF16, FP32
        on_chip_sram_mb: int = 32,
        memory_bandwidth_gbps: float = 128,
        tdp_watts: float = 30,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.mac_units = mac_units
        self.frequency_ghz = frequency_ghz
        self.precision = precision
        self.on_chip_sram_mb = on_chip_sram_mb
        self.memory_bandwidth_gbps = memory_bandwidth_gbps
        self.tdp_watts = tdp_watts
        
        # Precision efficiency multipliers
        self._precision_multipliers = {
            'INT8': 4.0,   # 4x throughput vs FP32
            'INT4': 8.0,   # 8x throughput
            'FP16': 2.0,
            'BF16': 2.0,
            'FP32': 1.0
        }
        
    def get_peak_tops(self) -> float:
        """
        Calculate peak throughput in TOPS (Tera Operations Per Second)
        
        TOPS = MAC_units * 2 (mul + add) * frequency * precision_multiplier
        """
        multiplier = self._precision_multipliers.get(self.precision, 1.0)
        ops_per_cycle = self.mac_units * 2  # Each MAC = 1 multiply + 1 add
        tops = (ops_per_cycle * self.frequency_ghz * multiplier) / 1000
        return tops
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Simulate NPU operation.
        
        For AI workloads, latency depends on:
        - Data loading from memory
        - Compute time based on operation size
        """
        self.metrics.total_requests += 1
        
        # Check if data fits in on-chip SRAM
        sram_bytes = self.on_chip_sram_mb * 1024 * 1024
        
        if size_bytes <= sram_bytes:
            # On-chip: fast access
            memory_latency_ns = 10
        else:
            # Off-chip: memory bound
            memory_latency_ns = (size_bytes / (self.memory_bandwidth_gbps * 1e9)) * 1e9
        
        # Simplified compute time (assuming compute-bound for large ops)
        ops_estimate = size_bytes * 2  # Rough: 2 ops per byte
        tops = self.get_peak_tops() * 1e12
        compute_ns = (ops_estimate / tops) * 1e9
        
        total_latency = memory_latency_ns + compute_ns
        self.metrics.total_latency_ns += total_latency
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return memory bandwidth"""
        return self.memory_bandwidth_gbps
    
    def get_power(self) -> float:
        """Return TDP"""
        return self.tdp_watts
    
    def get_efficiency_tops_per_watt(self) -> float:
        """Calculate power efficiency"""
        return self.get_peak_tops() / self.tdp_watts
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed NPU status"""
        base_status = super().get_status()
        base_status.update({
            'mac_units': self.mac_units,
            'precision': self.precision,
            'peak_tops': self.get_peak_tops(),
            'on_chip_sram_mb': self.on_chip_sram_mb,
            'efficiency_tops_per_watt': self.get_efficiency_tops_per_watt()
        })
        return base_status
