"""Systolic Array model with configurable dataflow"""
from typing import Dict, Any, Optional, List, Tuple
from ..base import Module
import math


class SystolicArray(Module):
    """
    Systolic Array accelerator model for GEMM operations.
    
    Supports three dataflow modes:
    - Weight Stationary (WS): Weights stay in place, activations flow
    - Output Stationary (OS): Partial sums accumulate in place
    - Input Stationary (IS): Inputs stay, weights flow
    
    Key parameters:
    - Array dimensions (height x width)
    - Operating frequency
    - Dataflow mode
    - Associated memory hierarchy
    """
    
    def __init__(
        self,
        name: str = "SystolicArray",
        array_height: int = 256,
        array_width: int = 256,
        frequency_ghz: float = 1.0,
        dataflow: str = "OS",  # WS, OS, IS
        precision_bytes: int = 2,  # FP16 = 2 bytes
        tdp_watts: float = 100,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.array_height = array_height
        self.array_width = array_width
        self.frequency_ghz = frequency_ghz
        self.dataflow = dataflow.upper()
        self.precision_bytes = precision_bytes
        self.tdp_watts = tdp_watts
        
        # Derived parameters
        self.num_macs = array_height * array_width
        self.peak_ops_per_cycle = self.num_macs * 2  # Each MAC = 1 mul + 1 add
        
        # Tracking
        self._total_compute_cycles = 0
        self._total_stall_cycles = 0
        self._total_ops = 0
        self._gemm_history: List[Dict] = []
        
    def get_peak_tflops(self) -> float:
        """Calculate peak throughput in TFLOPS"""
        ops_per_second = self.peak_ops_per_cycle * self.frequency_ghz * 1e9
        return ops_per_second / 1e12
    
    def calculate_tile_cycles(
        self,
        M_tile: int,
        K_tile: int,
        N_tile: int
    ) -> Dict[str, int]:
        """
        Calculate cycles to process a single tile based on dataflow.
        
        For systolic arrays:
        - WS: K iterations, each taking H+W-1 cycles to fill/drain
        - OS: Accumulate M×N outputs over K iterations
        - IS: Similar to WS but inputs stationary
        """
        H, W = self.array_height, self.array_width
        
        # Number of tiles needed to cover the GEMM tile
        m_tiles = math.ceil(M_tile / H)
        n_tiles = math.ceil(N_tile / W)
        
        # Compute cycles per output tile
        if self.dataflow == "OS":
            # Output stationary: K multiply-accumulate cycles per output
            compute_cycles = K_tile
            # Pipeline fill/drain overhead
            overhead_cycles = (H + W - 2)
        elif self.dataflow == "WS":
            # Weight stationary: stream activations through
            compute_cycles = K_tile
            overhead_cycles = (H + W - 2) + M_tile
        else:  # IS
            # Input stationary: stream weights through
            compute_cycles = K_tile
            overhead_cycles = (H + W - 2) + N_tile
        
        # Total cycles for all tiles
        total_compute = (compute_cycles + overhead_cycles) * m_tiles * n_tiles
        
        return {
            'compute_cycles': total_compute,
            'overhead_cycles': overhead_cycles * m_tiles * n_tiles,
            'm_tiles': m_tiles,
            'n_tiles': n_tiles
        }
    
    def simulate_gemm(
        self,
        M: int,
        K: int,
        N: int,
        tile_M: int,
        tile_K: int,
        tile_N: int,
        memory_stall_cycles: int = 0
    ) -> Dict[str, Any]:
        """
        Simulate a GEMM operation: C[M,N] = A[M,K] × B[K,N]
        
        Args:
            M, K, N: GEMM dimensions
            tile_M, tile_K, tile_N: Tile dimensions (constrained by memory)
            memory_stall_cycles: Stall cycles from memory bandwidth limits
        """
        # Calculate number of tiles
        num_M_tiles = math.ceil(M / tile_M)
        num_K_tiles = math.ceil(K / tile_K)
        num_N_tiles = math.ceil(N / tile_N)
        total_tiles = num_M_tiles * num_K_tiles * num_N_tiles
        
        # Calculate cycles per tile
        tile_result = self.calculate_tile_cycles(tile_M, tile_K, tile_N)
        cycles_per_tile = tile_result['compute_cycles']
        
        # Total compute cycles
        total_compute_cycles = cycles_per_tile * total_tiles
        
        # Total operations
        total_ops = 2 * M * K * N  # Multiply-accumulate = 2 ops
        
        # Utilization
        ideal_cycles = total_ops / self.peak_ops_per_cycle
        utilization = (ideal_cycles / max(total_compute_cycles, 1)) * 100
        
        # Time calculation
        total_cycles = total_compute_cycles + memory_stall_cycles
        execution_time_ns = total_cycles / self.frequency_ghz
        
        # Update tracking
        self._total_compute_cycles += total_compute_cycles
        self._total_stall_cycles += memory_stall_cycles
        self._total_ops += total_ops
        self.metrics.total_requests += 1
        self.metrics.total_latency_ns += execution_time_ns
        
        result = {
            'gemm_dims': {'M': M, 'K': K, 'N': N},
            'tile_dims': {'M': tile_M, 'K': tile_K, 'N': tile_N},
            'num_tiles': total_tiles,
            'compute_cycles': total_compute_cycles,
            'stall_cycles': memory_stall_cycles,
            'total_cycles': total_cycles,
            'total_ops': total_ops,
            'utilization_pct': utilization,
            'execution_time_ns': execution_time_ns,
            'throughput_tflops': (total_ops / execution_time_ns) * 1e-3
        }
        
        self._gemm_history.append(result)
        return result
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Generic request processing for compatibility.
        For detailed GEMM simulation, use simulate_gemm() directly.
        """
        self.metrics.total_requests += 1
        
        # Estimate as if processing a square GEMM
        dim = int(math.sqrt(size_bytes / self.precision_bytes / 3))
        result = self.simulate_gemm(dim, dim, dim, dim, dim, dim)
        
        return result['execution_time_ns']
    
    def get_bandwidth(self) -> float:
        """Return required memory bandwidth for peak utilization (GB/s)"""
        # For peak utilization, need to feed array_width elements per cycle
        bytes_per_cycle = self.array_width * self.precision_bytes * 2  # A and B inputs
        return bytes_per_cycle * self.frequency_ghz
    
    def get_power(self) -> float:
        """Return TDP in Watts"""
        return self.tdp_watts
    
    def get_utilization(self) -> float:
        """Calculate overall utilization across all GEMMs"""
        if self._total_compute_cycles == 0:
            return 0.0
        ideal_cycles = self._total_ops / self.peak_ops_per_cycle
        return (ideal_cycles / self._total_compute_cycles) * 100
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed systolic array status"""
        base_status = super().get_status()
        base_status.update({
            'array_dims': f'{self.array_height}x{self.array_width}',
            'num_macs': self.num_macs,
            'dataflow': self.dataflow,
            'peak_tflops': self.get_peak_tflops(),
            'utilization_pct': self.get_utilization(),
            'total_compute_cycles': self._total_compute_cycles,
            'total_stall_cycles': self._total_stall_cycles,
            'gemm_count': len(self._gemm_history)
        })
        return base_status


class MemoryHierarchy:
    """
    Multi-level memory hierarchy for systolic array.
    
    Manages L0 (registers) -> L1 (scratchpad) -> L2 (SRAM) -> L3 (HBM/DRAM)
    Calculates tile sizes based on innermost memory capacity.
    """
    
    def __init__(self):
        self.levels: List[Dict[str, Any]] = []
        
    def add_level(
        self,
        name: str,
        capacity_bytes: int,
        bandwidth_gbps: float,
        energy_per_bit_pj: float = 0.0,
        latency_cycles: int = 0
    ):
        """Add a memory level (innermost first)"""
        self.levels.append({
            'name': name,
            'capacity_bytes': capacity_bytes,
            'bandwidth_gbps': bandwidth_gbps,
            'energy_per_bit_pj': energy_per_bit_pj,
            'latency_cycles': latency_cycles,
            'bytes_accessed': 0,
            'energy_consumed_pj': 0
        })
    
    def get_max_tile_size(self, precision_bytes: int = 2) -> Dict[str, int]:
        """
        Calculate maximum tile dimensions based on innermost memory.
        
        For GEMM C = A × B, we need to fit:
        - A tile: M_tile × K_tile
        - B tile: K_tile × N_tile  
        - C tile: M_tile × N_tile
        
        Total = precision * (M*K + K*N + M*N) <= L0_capacity
        
        For simplicity, assume square tiles: 3 * dim^2 * precision <= capacity
        """
        if not self.levels:
            return {'M': 64, 'K': 64, 'N': 64}  # Default
        
        innermost = self.levels[0]
        capacity = innermost['capacity_bytes']
        
        # Solve for square tile: 3 * dim^2 * precision = capacity
        max_dim = int(math.sqrt(capacity / (3 * precision_bytes)))
        
        # Round down to power of 2 for efficiency
        if max_dim > 0:
            max_dim = 2 ** int(math.log2(max_dim))
        else:
            max_dim = 16  # Minimum
            
        return {'M': max_dim, 'K': max_dim, 'N': max_dim}
    
    def calculate_data_movement(
        self,
        M: int, K: int, N: int,
        tile_M: int, tile_K: int, tile_N: int,
        precision_bytes: int = 2,
        dataflow: str = "OS"
    ) -> Dict[str, Any]:
        """
        Calculate data movement through memory hierarchy.
        
        Returns bytes moved at each level and associated energy.
        """
        # Tile counts
        num_M = math.ceil(M / tile_M)
        num_K = math.ceil(K / tile_K)
        num_N = math.ceil(N / tile_N)
        
        # Data reuse depends on dataflow
        if dataflow == "OS":
            # Output stationary: each C element accumulated across K
            # A: M*K loaded once per N-tile
            # B: K*N loaded once per M-tile
            # C: M*N written once
            a_reads = M * K * num_N
            b_reads = K * N * num_M
            c_writes = M * N
        elif dataflow == "WS":
            # Weight stationary: B stays, A and C stream
            a_reads = M * K * num_N
            b_reads = K * N  # Loaded once
            c_writes = M * N
        else:  # IS
            # Input stationary: A stays, B and C stream
            a_reads = M * K  # Loaded once
            b_reads = K * N * num_M
            c_writes = M * N
        
        total_bytes = (a_reads + b_reads + c_writes) * precision_bytes
        
        # Calculate per-level movement (simplified: all goes through each level)
        level_stats = []
        total_energy_pj = 0
        
        for level in self.levels:
            bytes_at_level = total_bytes
            energy = bytes_at_level * 8 * level['energy_per_bit_pj']
            level['bytes_accessed'] += bytes_at_level
            level['energy_consumed_pj'] += energy
            total_energy_pj += energy
            
            level_stats.append({
                'name': level['name'],
                'bytes_moved': bytes_at_level,
                'energy_pj': energy
            })
        
        return {
            'a_bytes': a_reads * precision_bytes,
            'b_bytes': b_reads * precision_bytes,
            'c_bytes': c_writes * precision_bytes,
            'total_bytes': total_bytes,
            'total_energy_pj': total_energy_pj,
            'per_level': level_stats
        }
    
    def get_stall_cycles(
        self,
        bytes_needed: int,
        compute_cycles: int,
        frequency_ghz: float
    ) -> int:
        """
        Calculate memory stall cycles based on bandwidth constraints.
        
        If memory can't keep up with compute, we have stalls.
        """
        if not self.levels:
            return 0
        
        # Use innermost level bandwidth
        bandwidth_gbps = self.levels[0]['bandwidth_gbps']
        
        # Time to transfer data
        transfer_time_ns = bytes_needed / (bandwidth_gbps * 1e9) * 1e9
        transfer_cycles = transfer_time_ns * frequency_ghz
        
        # Stall = transfer time - compute time (if transfer is slower)
        stall_cycles = max(0, int(transfer_cycles - compute_cycles))
        
        return stall_cycles
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all memory levels"""
        return {
            'num_levels': len(self.levels),
            'levels': [
                {
                    'name': l['name'],
                    'capacity_kb': l['capacity_bytes'] / 1024,
                    'bandwidth_gbps': l['bandwidth_gbps'],
                    'bytes_accessed': l['bytes_accessed'],
                    'energy_consumed_pj': l['energy_consumed_pj']
                }
                for l in self.levels
            ]
        }
