"""DSP (Digital Signal Processor) model"""
from typing import Dict, Any, Optional
from ..base import Module


class DSP(Module):
    """
    Digital Signal Processor model.
    
    Characteristics:
    - SIMD/vector operations
    - Fixed-point arithmetic optimization
    - Low-latency signal processing pipelines
    """
    
    def __init__(
        self,
        name: str = "DSP",
        frequency_ghz: float = 1.2,
        vector_width: int = 256,  # bits (e.g., 256-bit SIMD)
        mac_units: int = 8,
        fixed_point_support: bool = True,
        fft_accelerator: bool = True,
        tdp_watts: float = 5,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.frequency_ghz = frequency_ghz
        self.vector_width = vector_width
        self.mac_units = mac_units
        self.fixed_point_support = fixed_point_support
        self.fft_accelerator = fft_accelerator
        self.tdp_watts = tdp_watts
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Simulate DSP operation.
        
        DSP optimized for streaming signal processing with low latency.
        """
        self.metrics.total_requests += 1
        
        # DSP pipeline latency (very low for signal processing)
        pipeline_cycles = 8
        
        # Vector processing throughput
        bytes_per_cycle = self.vector_width / 8
        processing_cycles = size_bytes / bytes_per_cycle
        
        total_cycles = pipeline_cycles + processing_cycles
        latency_ns = total_cycles / self.frequency_ghz
        
        self.metrics.total_latency_ns += latency_ns
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """Return processing throughput in GB/s"""
        bytes_per_cycle = self.vector_width / 8
        return bytes_per_cycle * self.frequency_ghz
    
    def get_power(self) -> float:
        """Return TDP"""
        return self.tdp_watts
    
    def get_peak_gops(self) -> float:
        """Calculate peak GOPS (Giga Operations Per Second)"""
        ops_per_cycle = self.mac_units * 2 * (self.vector_width // 32)  # 32-bit elements
        return ops_per_cycle * self.frequency_ghz
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed DSP status"""
        base_status = super().get_status()
        base_status.update({
            'vector_width': self.vector_width,
            'mac_units': self.mac_units,
            'peak_gops': self.get_peak_gops(),
            'fft_accelerator': self.fft_accelerator,
            'fixed_point': self.fixed_point_support
        })
        return base_status
