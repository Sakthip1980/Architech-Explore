"""HBM (High Bandwidth Memory) model"""
from typing import Dict, Any, Optional
from ..base import Module


class HBM(Module):
    """
    High Bandwidth Memory (HBM2/HBM3) model.
    3D-stacked DRAM with ultra-high bandwidth for AI accelerators.
    
    Key characteristics:
    - Multiple stacks with independent channels
    - Wide interface (1024-bit per stack typical)
    - Lower latency than traditional DRAM due to proximity
    """
    
    def __init__(
        self,
        name: str = "HBM",
        generation: str = "HBM2e",  # HBM2, HBM2e, HBM3, HBM3e
        stacks: int = 4,
        capacity_per_stack_gb: int = 4,
        channels_per_stack: int = 8,
        channel_width_bits: int = 128,
        frequency_gbps: float = 2.4,  # Data rate per pin in Gbps
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.generation = generation
        self.stacks = stacks
        self.capacity_per_stack_gb = capacity_per_stack_gb
        self.channels_per_stack = channels_per_stack
        self.channel_width_bits = channel_width_bits
        self.frequency_gbps = frequency_gbps
        
        # HBM generation-specific parameters
        self._gen_params = {
            'HBM2': {'max_bw_per_stack': 256, 'power_per_stack_w': 4.5},
            'HBM2e': {'max_bw_per_stack': 307, 'power_per_stack_w': 5.0},
            'HBM3': {'max_bw_per_stack': 665, 'power_per_stack_w': 6.5},
            'HBM3e': {'max_bw_per_stack': 1229, 'power_per_stack_w': 8.0},
        }
        
        self._base_latency_ns = 80 if 'HBM3' in generation else 100
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate HBM access"""
        self.metrics.total_requests += 1
        
        # HBM has lower latency due to 3D stacking proximity
        base_latency = self._base_latency_ns
        
        # Transfer time based on aggregate bandwidth
        bandwidth_gbps = self.get_bandwidth()
        transfer_ns = (size_bytes / (bandwidth_gbps * 1e9)) * 1e9
        
        total_latency = base_latency + transfer_ns
        self.metrics.total_latency_ns += total_latency
        self.metrics.bandwidth_utilized_gbps = bandwidth_gbps * 0.75
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """
        Calculate total HBM bandwidth in GB/s
        
        BW = stacks * channels_per_stack * channel_width * frequency / 8
        """
        total_channels = self.stacks * self.channels_per_stack
        bits_per_transfer = total_channels * self.channel_width_bits
        bytes_per_transfer = bits_per_transfer / 8
        bandwidth = bytes_per_transfer * self.frequency_gbps
        return bandwidth
    
    def get_power(self) -> float:
        """Return power consumption in Watts"""
        gen_params = self._gen_params.get(self.generation, self._gen_params['HBM2'])
        base_power = gen_params['power_per_stack_w'] * self.stacks
        # Dynamic power based on utilization
        utilization = self.metrics.bandwidth_utilized_gbps / max(self.get_bandwidth(), 1)
        return base_power * (0.3 + 0.7 * utilization)
    
    def get_capacity(self) -> int:
        """Return total capacity in GB"""
        return self.stacks * self.capacity_per_stack_gb
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed HBM status"""
        base_status = super().get_status()
        base_status.update({
            'generation': self.generation,
            'stacks': self.stacks,
            'total_capacity_gb': self.get_capacity(),
            'channels': self.stacks * self.channels_per_stack,
            'theoretical_bandwidth_gbps': self.get_bandwidth()
        })
        return base_status
