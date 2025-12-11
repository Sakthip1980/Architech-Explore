"""System-level simulation orchestration"""
from typing import List, Dict, Any, Optional
from .base import Module
import random


class System:
    """Main system container and simulation coordinator"""
    
    def __init__(self, name: str = "Architecture"):
        self.name = name
        self.modules: Dict[str, Module] = {}
        self.connections: List[tuple] = []
        
    def add_module(self, module: Module):
        """Add a hardware module to the system"""
        self.modules[module.name] = module
        
    def connect(self, source: Module, target: Module):
        """Connect two modules"""
        source.connect(target)
        self.connections.append((source.name, target.name))
        
    def simulate(
        self,
        cycles: int = 1000,
        workload: str = "memory_intensive"
    ) -> Dict[str, Any]:
        """
        Run system simulation
        
        Args:
            cycles: Number of simulation cycles
            workload: Type of workload ('memory_intensive', 'compute_intensive', 'mixed')
            
        Returns:
            Simulation results dictionary
        """
        # Reset all metrics
        for module in self.modules.values():
            module.reset_metrics()
            module.metrics.total_cycles = cycles
        
        # Generate workload pattern
        requests = self._generate_workload(cycles, workload)
        
        # Execute simulation
        total_latency = 0.0
        for req_type, size_bytes, target_module in requests:
            if target_module in self.modules:
                latency = self.modules[target_module].process_request(req_type, size_bytes)
                total_latency += latency
        
        # Collect results
        results = {
            'system_name': self.name,
            'total_cycles': cycles,
            'workload_type': workload,
            'total_requests': len(requests),
            'total_latency_ns': total_latency,
            'average_latency_ns': total_latency / len(requests) if requests else 0,
            'modules': {}
        }
        
        # Add per-module statistics
        total_power = 0.0
        for name, module in self.modules.items():
            results['modules'][name] = module.get_status()
            total_power += module.get_power()
        
        results['total_power_watts'] = total_power
        
        return results
    
    def _generate_workload(
        self,
        cycles: int,
        workload_type: str
    ) -> List[tuple]:
        """Generate synthetic workload"""
        requests = []
        num_requests = cycles // 10  # 1 request every 10 cycles on average
        
        # Determine target distribution based on workload
        modules_list = list(self.modules.keys())
        if not modules_list:
            return []
        
        for _ in range(num_requests):
            # Pick request type
            req_type = random.choice(['read', 'write'])
            
            # Pick size (64B to 4KB)
            size_bytes = random.choice([64, 128, 256, 512, 1024, 2048, 4096])
            
            # Pick target module
            if workload_type == 'memory_intensive':
                # Prefer DRAM
                target = random.choice([m for m in modules_list if 'DRAM' in m] or modules_list)
            elif workload_type == 'compute_intensive':
                # Prefer CPU/GPU
                target = random.choice([m for m in modules_list if 'CPU' in m or 'GPU' in m] or modules_list)
            else:
                # Mixed
                target = random.choice(modules_list)
            
            requests.append((req_type, size_bytes, target))
        
        return requests
    
    def get_topology(self) -> Dict[str, Any]:
        """Get system topology information"""
        return {
            'name': self.name,
            'modules': [
                {
                    'name': name,
                    'type': module.__class__.__name__,
                    'connections': list(module.connections.keys())
                }
                for name, module in self.modules.items()
            ],
            'connections': self.connections
        }
