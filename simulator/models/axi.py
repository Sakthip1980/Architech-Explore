"""AXI Bus model"""
from typing import Dict, Any, Optional
from ..base import Module


class AXIBus(Module):
    """
    AXI (Advanced eXtensible Interface) Bus model.
    
    AMBA AXI protocol features:
    - Separate address/data channels
    - Out-of-order transaction completion
    - Burst transfers
    - Multiple outstanding transactions
    """
    
    def __init__(
        self,
        name: str = "AXI",
        version: str = "AXI4",  # AXI3, AXI4, AXI4-Lite, AXI5
        data_width_bits: int = 128,
        address_width_bits: int = 32,
        frequency_mhz: float = 200,
        max_burst_length: int = 256,
        outstanding_transactions: int = 16,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.version = version
        self.data_width_bits = data_width_bits
        self.address_width_bits = address_width_bits
        self.frequency_mhz = frequency_mhz
        self.max_burst_length = max_burst_length
        self.outstanding_transactions = outstanding_transactions
        
        # Protocol overhead (cycles)
        self._address_phase_cycles = 1
        self._response_cycles = 1
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate AXI transaction"""
        self.metrics.total_requests += 1
        
        bytes_per_beat = self.data_width_bits / 8
        
        # Calculate number of beats needed
        beats = max(1, size_bytes / bytes_per_beat)
        
        # Burst efficiency: longer bursts are more efficient
        if beats <= self.max_burst_length:
            # Single burst
            overhead_cycles = self._address_phase_cycles + self._response_cycles
        else:
            # Multiple bursts needed
            num_bursts = (beats + self.max_burst_length - 1) // self.max_burst_length
            overhead_cycles = num_bursts * (self._address_phase_cycles + self._response_cycles)
        
        total_cycles = overhead_cycles + beats
        
        # Convert to nanoseconds
        clock_period_ns = 1000 / self.frequency_mhz
        latency_ns = total_cycles * clock_period_ns
        
        self.metrics.total_latency_ns += latency_ns
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """Calculate peak bandwidth in GB/s"""
        bytes_per_cycle = self.data_width_bits / 8
        bandwidth = bytes_per_cycle * (self.frequency_mhz / 1000)
        return bandwidth
    
    def get_power(self) -> float:
        """Return estimated power in Watts"""
        # AXI bus power scales with data width and frequency
        base_power_mw = 50  # Base interconnect power
        width_factor = self.data_width_bits / 64
        freq_factor = self.frequency_mhz / 100
        return (base_power_mw * width_factor * freq_factor) / 1000
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed AXI status"""
        base_status = super().get_status()
        base_status.update({
            'version': self.version,
            'data_width': self.data_width_bits,
            'frequency_mhz': self.frequency_mhz,
            'max_burst': self.max_burst_length,
            'outstanding': self.outstanding_transactions,
            'theoretical_bandwidth_gbps': self.get_bandwidth()
        })
        return base_status
