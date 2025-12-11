"""DRAM Controller model with detailed timing parameters"""
from typing import Dict, Any, Optional
from ..base import Module


class DRAM(Module):
    """
    Detailed DRAM controller model with DDR timing parameters.
    
    Key simulation parameters:
    - Timing: tCL, tRCD, tRP, tRAS (in clock cycles)
    - Geometry: banks, ranks, bus width
    - Performance: frequency, bandwidth
    """
    
    def __init__(
        self,
        name: str = "DRAM",
        capacity_gb: int = 32,
        frequency_mhz: int = 2400,
        timings: Optional[Dict[str, int]] = None,
        geometry: Optional[Dict[str, int]] = None,
        power_model: str = 'ddr4_standard',
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        # Memory capacity
        self.capacity_gb = capacity_gb
        
        # Clock frequency
        self.frequency_mhz = frequency_mhz
        self.clock_period_ns = 1000.0 / frequency_mhz  # Convert to ns
        
        # DDR Timing parameters (in clock cycles)
        default_timings = {
            'tCL': 16,   # CAS Latency
            'tRCD': 18,  # RAS to CAS Delay
            'tRP': 18,   # Row Precharge time
            'tRAS': 36   # Row Active time
        }
        self.timings = {**default_timings, **(timings or {})}
        
        # Memory geometry
        default_geometry = {
            'banks': 16,
            'ranks': 2,
            'bus_width': 64  # bits
        }
        self.geometry = {**default_geometry, **(geometry or {})}
        
        # Power model
        self.power_model = power_model
        self._base_power_w = self._calculate_base_power()
        
        # Performance tracking
        self._row_buffer_hits = 0
        self._row_buffer_misses = 0
        
    def _calculate_base_power(self) -> float:
        """Calculate base power consumption based on model"""
        power_models = {
            'ddr4_standard': 3.0,
            'ddr4_high_perf': 5.0,
            'ddr5_standard': 4.5,
            'lpddr4': 2.0
        }
        return power_models.get(self.power_model, 3.0)
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Simulate a memory request and return latency
        
        Args:
            request_type: 'read' or 'write'
            size_bytes: Size of the request
            
        Returns:
            Total latency in nanoseconds
        """
        self.metrics.total_requests += 1
        
        # Determine if this is a row buffer hit or miss
        row_hit = (self._row_buffer_hits + self._row_buffer_misses) % 4 == 0  # Simplified model
        
        if row_hit:
            self._row_buffer_hits += 1
            # Row buffer hit: only CAS latency
            latency_cycles = self.timings['tCL']
        else:
            self._row_buffer_misses += 1
            # Row buffer miss: precharge + activate + CAS
            latency_cycles = (
                self.timings['tRP'] +   # Precharge
                self.timings['tRCD'] +  # Activate
                self.timings['tCL']     # CAS
            )
        
        # Convert cycles to nanoseconds
        latency_ns = latency_cycles * self.clock_period_ns
        
        # Add burst transfer time for data
        burst_cycles = (size_bytes * 8) / self.geometry['bus_width']
        transfer_ns = burst_cycles * self.clock_period_ns
        
        total_latency = latency_ns + transfer_ns
        
        # Update metrics
        self.metrics.total_latency_ns += total_latency
        self.metrics.bandwidth_utilized_gbps = self.get_bandwidth() * 0.7  # 70% utilization estimate
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """
        Calculate theoretical peak bandwidth in GB/s
        
        BW = (bus_width / 8) * frequency * 2 (DDR)
        """
        bytes_per_cycle = self.geometry['bus_width'] / 8
        transfers_per_second = self.frequency_mhz * 1e6 * 2  # DDR = 2 transfers per cycle
        bandwidth_bps = bytes_per_cycle * transfers_per_second
        return bandwidth_bps / 1e9  # Convert to GB/s
    
    def get_power(self) -> float:
        """Return current power consumption in Watts"""
        # Dynamic power scales with utilization
        utilization = min(self.metrics.bandwidth_utilized_gbps / self.get_bandwidth(), 1.0)
        dynamic_power = self._base_power_w * utilization * 2.5
        return self._base_power_w + dynamic_power
    
    def get_row_buffer_hit_rate(self) -> float:
        """Calculate row buffer hit rate"""
        total_accesses = self._row_buffer_hits + self._row_buffer_misses
        if total_accesses == 0:
            return 0.0
        return self._row_buffer_hits / total_accesses
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed DRAM status"""
        base_status = super().get_status()
        base_status.update({
            'capacity_gb': self.capacity_gb,
            'frequency_mhz': self.frequency_mhz,
            'timings': self.timings,
            'geometry': self.geometry,
            'row_buffer_hit_rate': self.get_row_buffer_hit_rate(),
            'theoretical_bandwidth_gbps': self.get_bandwidth()
        })
        return base_status
