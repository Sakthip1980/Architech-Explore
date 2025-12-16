"""SRAM Cache model"""
from typing import Dict, Any, Optional
from ..base import Module


class SRAMCache(Module):
    """
    SRAM Cache model (L1/L2/L3).
    
    Simulates cache behavior with configurable:
    - Size, associativity, line size
    - Hit/miss latencies
    - Simple LRU-like hit rate model
    """
    
    def __init__(
        self,
        name: str = "Cache",
        level: int = 1,  # 1, 2, or 3
        size_kb: int = 64,
        associativity: int = 8,
        line_size_bytes: int = 64,
        frequency_ghz: float = 3.0,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.level = level
        self.size_kb = size_kb
        self.associativity = associativity
        self.line_size_bytes = line_size_bytes
        self.frequency_ghz = frequency_ghz
        
        # Level-specific latencies (in cycles)
        self._latency_cycles = {
            1: 4,   # L1: ~4 cycles
            2: 12,  # L2: ~12 cycles
            3: 40   # L3: ~40 cycles
        }
        
        # Level-specific power per KB (mW)
        self._power_per_kb_mw = {
            1: 0.5,   # L1: high power, fast
            2: 0.2,   # L2: medium
            3: 0.08   # L3: low power, larger
        }
        
        # Simulated hit tracking
        self._hits = 0
        self._misses = 0
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate cache access"""
        self.metrics.total_requests += 1
        
        # Simplified hit rate model based on working set vs cache size
        cache_bytes = self.size_kb * 1024
        hit_probability = min(cache_bytes / max(size_bytes * 100, 1), 0.95)
        
        # Determine hit or miss
        import random
        is_hit = random.random() < hit_probability
        
        if is_hit:
            self._hits += 1
            latency_cycles = self._latency_cycles.get(self.level, 10)
        else:
            self._misses += 1
            # Miss penalty: go to next level (simplified)
            latency_cycles = self._latency_cycles.get(self.level, 10) * 10
        
        # Convert cycles to nanoseconds
        latency_ns = latency_cycles / self.frequency_ghz
        self.metrics.total_latency_ns += latency_ns
        
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """Cache bandwidth in GB/s"""
        # Simplified: line_size * frequency * ports
        ports = 2 if self.level == 1 else 1
        return (self.line_size_bytes * self.frequency_ghz * ports)
    
    def get_power(self) -> float:
        """Return power consumption in Watts"""
        power_mw = self._power_per_kb_mw.get(self.level, 0.2) * self.size_kb
        return power_mw / 1000  # Convert to Watts
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed cache status"""
        base_status = super().get_status()
        base_status.update({
            'level': f'L{self.level}',
            'size_kb': self.size_kb,
            'associativity': self.associativity,
            'line_size': self.line_size_bytes,
            'hit_rate': self.get_hit_rate(),
            'hits': self._hits,
            'misses': self._misses
        })
        return base_status
