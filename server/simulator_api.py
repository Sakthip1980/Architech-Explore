"""API wrapper for the simulator backend"""
from typing import Dict, Any, List, Optional
import sys
import os
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from simulator import (
    System, 
    # Memory
    DRAM, HBM, SRAMCache, NVM, Scratchpad,
    # Compute
    CPU, GPU, NPU, DSP, SystolicArray,
    # Interconnects
    Interconnect, AXIBus, PCIe, CXL,
    # Specialized
    DMAEngine, MemoryController,
    # Workloads
    Workload, get_resnet50_workload, get_gpt2_workload, get_llama7b_workload
)

# Import new configs
from simulator.configs import (
    HardwareConfig, get_hardware_preset, HARDWARE_PRESETS,
    ModelConfig, get_model_preset, MODEL_PRESETS,
    PrecisionConfig, PRECISION_MODES,
    ParallelismConfig,
    NetworkConfig, NetworkTopology, NETWORK_PRESETS,
)
from simulator.configs.network import CollectiveType

# State file for persistence between calls
STATE_FILE = os.path.join(project_root, '.simulator_state.json')


def safe_int(value: Any, default: int) -> int:
    """Safely convert value to int"""
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float) -> float:
    """Safely convert value to float"""
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return default


class SimulatorAPI:
    """Interface between Express API and Python simulator"""
    
    def __init__(self):
        self.system: Optional[System] = None
        self._graph_data: Optional[Dict] = None
        self._hardware_config: Optional[HardwareConfig] = None
        self._parallelism_config: Optional[ParallelismConfig] = None
        self._network_config: Optional[NetworkConfig] = None
        
    def _save_state(self, graph_data: Dict):
        """Save graph data to file for persistence"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(graph_data, f)
        except Exception:
            pass
    
    def _load_state(self) -> Optional[Dict]:
        """Load graph data from file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    def _create_module(self, node_id: str, data: Dict) -> Any:
        """Create appropriate module based on label with safe parameter handling"""
        label = data.get('label', 'Unknown')
        
        # Memory Subsystem
        if label == 'DRAM Controller':
            return DRAM(
                name=f"DRAM_{node_id}",
                frequency_mhz=safe_int(safe_float(data.get('frequency', 2.4), 2.4) * 1000, 2400),
                timings={
                    'tCL': safe_int(data.get('tCL', 16), 16),
                    'tRCD': safe_int(data.get('tRCD', 18), 18),
                    'tRP': safe_int(data.get('tRP', 18), 18),
                    'tRAS': safe_int(data.get('tRAS', 36), 36)
                },
                geometry={
                    'banks': safe_int(data.get('banks', 16), 16),
                    'bus_width': safe_int(data.get('busWidth', 64), 64),
                    'ranks': 2
                }
            )
        elif label == 'HBM':
            return HBM(
                name=f"HBM_{node_id}",
                generation=str(data.get('generation', 'HBM2e')),
                stacks=safe_int(data.get('stacks', 4), 4),
                capacity_per_stack_gb=safe_int(data.get('capacityPerStack', 4), 4),
                frequency_gbps=safe_float(data.get('frequency', 2.4), 2.4)
            )
        elif label == 'SRAM Cache':
            return SRAMCache(
                name=f"Cache_{node_id}",
                level=safe_int(data.get('level', 2), 2),
                size_kb=safe_int(data.get('sizeKb', 256), 256),
                associativity=safe_int(data.get('associativity', 8), 8),
                frequency_ghz=safe_float(data.get('frequency', 3.0), 3.0)
            )
        elif label == 'NVM Storage':
            return NVM(
                name=f"NVM_{node_id}",
                technology=str(data.get('technology', '3DXPoint')),
                capacity_gb=safe_int(data.get('capacityGb', 256), 256),
                read_latency_ns=safe_float(data.get('readLatency', 300), 300),
                write_latency_ns=safe_float(data.get('writeLatency', 1000), 1000)
            )
        elif label == 'Scratchpad':
            return Scratchpad(
                name=f"SPM_{node_id}",
                size_kb=safe_int(data.get('sizeKb', 256), 256),
                partitions=safe_int(data.get('partitions', 4), 4),
                frequency_ghz=safe_float(data.get('frequency', 1.0), 1.0)
            )
        
        # Compute Units
        elif label == 'CPU Core':
            return CPU(
                name=f"CPU_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 3.0), 3.0),
                cores=safe_int(data.get('cores', 4), 4),
                tdp_watts=safe_float(data.get('power', 65), 65)
            )
        elif label == 'GPU Accelerator':
            return GPU(
                name=f"GPU_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 1.5), 1.5),
                memory_bandwidth_gbps=safe_float(data.get('bandwidth', 256), 256),
                tdp_watts=safe_float(data.get('power', 150), 150)
            )
        elif label == 'NPU':
            return NPU(
                name=f"NPU_{node_id}",
                mac_units=safe_int(data.get('macUnits', 4096), 4096),
                frequency_ghz=safe_float(data.get('frequency', 1.0), 1.0),
                precision=str(data.get('precision', 'INT8')),
                on_chip_sram_mb=safe_int(data.get('sramMb', 32), 32),
                tdp_watts=safe_float(data.get('power', 30), 30)
            )
        elif label == 'DSP':
            return DSP(
                name=f"DSP_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 1.2), 1.2),
                vector_width=safe_int(data.get('vectorWidth', 256), 256),
                tdp_watts=safe_float(data.get('power', 5), 5)
            )
        elif label == 'Systolic Array':
            return SystolicArray(
                name=f"SystolicArray_{node_id}",
                array_height=safe_int(data.get('arrayHeight', 256), 256),
                array_width=safe_int(data.get('arrayWidth', 256), 256),
                frequency_ghz=safe_float(data.get('frequency', 1.0), 1.0),
                dataflow=str(data.get('dataflow', 'OS')),
                precision_bytes=safe_int(data.get('precisionBytes', 2), 2),
                tdp_watts=safe_float(data.get('power', 100), 100)
            )
        
        # Interconnects
        elif label == 'NoC / Bus':
            return Interconnect(
                name=f"Interconnect_{node_id}",
                bandwidth_gbps=safe_float(data.get('bandwidth', 100), 100),
                latency_ns=safe_float(data.get('latency', 10), 10)
            )
        elif label == 'AXI Bus':
            return AXIBus(
                name=f"AXI_{node_id}",
                version=str(data.get('version', 'AXI4')),
                data_width_bits=safe_int(data.get('dataWidth', 128), 128),
                frequency_mhz=safe_float(data.get('frequencyMhz', 200), 200)
            )
        elif label == 'PCIe Link':
            return PCIe(
                name=f"PCIe_{node_id}",
                generation=safe_int(data.get('generation', 4), 4),
                lanes=safe_int(data.get('lanes', 16), 16)
            )
        elif label == 'CXL Interface':
            return CXL(
                name=f"CXL_{node_id}",
                version=str(data.get('version', '2.0')),
                cxl_type=safe_int(data.get('cxlType', 3), 3),
                lanes=safe_int(data.get('lanes', 16), 16),
                attached_memory_gb=safe_int(data.get('memoryGb', 128), 128)
            )
        
        # Specialized
        elif label == 'DMA Engine':
            return DMAEngine(
                name=f"DMA_{node_id}",
                channels=safe_int(data.get('channels', 8), 8),
                bandwidth_gbps=safe_float(data.get('bandwidth', 25.6), 25.6)
            )
        elif label == 'Memory Controller':
            return MemoryController(
                name=f"MemCtrl_{node_id}",
                scheduling_policy=str(data.get('policy', 'FR-FCFS')),
                channels=safe_int(data.get('channels', 2), 2)
            )
        
        # Default fallback
        else:
            return CPU(name=f"Module_{node_id}")
        
    def build_system_from_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a system from frontend graph representation"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Save state for later
        self._save_state(graph_data)
        self._graph_data = graph_data
        
        # Create new system
        self.system = System(name='UserArchitecture')
        module_map = {}
        
        # Create modules from nodes
        for node in nodes:
            node_id = node['id']
            data = node.get('data', {})
            
            module = self._create_module(node_id, data)
            self.system.add_module(module)
            module_map[node_id] = module
        
        # Create connections from edges
        for edge in edges:
            source_id = edge['source']
            target_id = edge['target']
            
            if source_id in module_map and target_id in module_map:
                self.system.connect(module_map[source_id], module_map[target_id])
        
        return self.system.get_topology()
    
    def run_simulation(
        self,
        cycles: int = 1000,
        workload: str = 'memory_intensive'
    ) -> Dict[str, Any]:
        """Run simulation on the current system"""
        if not self.system:
            saved_state = self._load_state()
            if saved_state:
                self.build_system_from_graph(saved_state)
        
        if not self.system:
            return {'error': 'No system built. Build a system first.'}
        
        results = self.system.simulate(cycles=cycles, workload=workload)
        return results
    
    def build_and_run(
        self,
        graph_data: Dict[str, Any],
        cycles: int = 1000,
        workload: str = 'memory_intensive'
    ) -> Dict[str, Any]:
        """Build system and run simulation in one call"""
        topology = self.build_system_from_graph(graph_data)
        results = self.run_simulation(cycles=cycles, workload=workload)
        return {
            'topology': topology,
            'simulation': results
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.system:
            saved_state = self._load_state()
            if saved_state:
                self.build_system_from_graph(saved_state)
                
        if not self.system:
            return {'error': 'No system built'}
        
        return self.system.get_topology()
    
    def get_available_presets(self) -> Dict[str, Any]:
        """Get all available configuration presets"""
        return {
            'hardware': {
                name: config.to_dict() 
                for name, config in HARDWARE_PRESETS.items()
            },
            'models': {
                name: config.to_dict()
                for name, config in MODEL_PRESETS.items()
            },
            'precision': list(PRECISION_MODES.keys()),
            'networks': {
                name: config.to_dict()
                for name, config in NETWORK_PRESETS.items()
            }
        }
    
    def run_workload_simulation(
        self,
        graph_data: Dict[str, Any],
        workload_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a workload-based simulation on the architecture.
        
        Args:
            graph_data: Node graph representing the architecture
            workload_data: Workload definition (preset, custom, or CSV)
        """
        # Build the system first
        self.build_system_from_graph(graph_data)
        
        # Get hardware preset if specified
        hw_preset_name = workload_data.get('hardware_preset')
        if hw_preset_name and hw_preset_name in HARDWARE_PRESETS:
            self._hardware_config = get_hardware_preset(hw_preset_name)
        
        # Get parallelism config
        parallelism_data = workload_data.get('parallelism', {})
        self._parallelism_config = ParallelismConfig(
            dp=safe_int(parallelism_data.get('dp', 1), 1),
            pp=safe_int(parallelism_data.get('pp', 1), 1),
            tp=safe_int(parallelism_data.get('tp', 1), 1),
            cp=safe_int(parallelism_data.get('cp', 1), 1),
            num_microbatches=safe_int(parallelism_data.get('num_microbatches', 1), 1),
        )
        
        # Get network config
        network_preset_name = workload_data.get('network_preset')
        if network_preset_name and network_preset_name in NETWORK_PRESETS:
            self._network_config = NETWORK_PRESETS[network_preset_name]
        else:
            self._network_config = NetworkConfig(
                npus_count=self._parallelism_config.get_total_devices()
            )
        
        # Create workload based on type
        workload_type = workload_data.get('type', 'preset')
        batch = safe_int(workload_data.get('batch', 1), 1)
        seq_len = safe_int(workload_data.get('seq_len', 512), 512)
        
        # Check for model preset
        model_preset_name = workload_data.get('model_preset')
        model_config: Optional[ModelConfig] = None
        
        if model_preset_name and model_preset_name in MODEL_PRESETS:
            model_config = get_model_preset(model_preset_name)
            model_config.batch_size = batch
            model_config.seq_len = seq_len
        
        if workload_type == 'preset':
            preset = workload_data.get('preset', 'gpt2')
            if preset == 'gpt2':
                workload = get_gpt2_workload(batch=batch, seq_len=seq_len)
            elif preset == 'llama7b':
                workload = get_llama7b_workload(batch=batch, seq_len=seq_len)
            elif preset == 'resnet50':
                workload = get_resnet50_workload(batch=batch)
            else:
                workload = Workload("Custom")
        elif workload_type == 'csv':
            csv_content = workload_data.get('content', '')
            workload = Workload.from_csv(csv_content)
        elif workload_type == 'custom':
            workload = Workload("Custom")
            for layer in workload_data.get('layers', []):
                workload.add_gemm(
                    name=layer.get('name', 'layer'),
                    M=safe_int(layer.get('M', 1024), 1024),
                    K=safe_int(layer.get('K', 1024), 1024),
                    N=safe_int(layer.get('N', 1024), 1024)
                )
        elif workload_type == 'llm' and model_config:
            # Generate workload from model config
            workload = Workload(model_config.name)
            gemm_dims = model_config.get_layers_gemm_dims()
            for gemm in gemm_dims:
                workload.add_gemm(
                    name=gemm['name'],
                    M=gemm['M'],
                    K=gemm['K'],
                    N=gemm['N']
                )
        else:
            workload = Workload("Empty")
        
        # Find systolic arrays in the system
        systolic_arrays = []
        for module_name, module in self.system.modules.items():
            if isinstance(module, SystolicArray):
                systolic_arrays.append(module)
        
        if not systolic_arrays:
            return {'error': 'No Systolic Array found in the architecture. Add one to run workload simulation.'}
        
        # Use the first systolic array for simulation
        sa = systolic_arrays[0]
        
        # Use hardware config memory hierarchy if available
        tile_M = min(sa.array_height, 256)
        tile_K = 256
        tile_N = min(sa.array_width, 256)
        
        if self._hardware_config:
            # Calculate tile size from innermost memory (L0)
            l0_config = self._hardware_config.memory_hierarchy.get('l0')
            if l0_config:
                import math
                capacity = l0_config.size_bytes
                precision_bytes = sa.precision_bytes
                max_dim = int(math.sqrt(capacity / (3 * precision_bytes)))
                if max_dim > 0:
                    max_dim = 2 ** int(math.log2(max_dim))
                    tile_M = min(tile_M, max_dim)
                    tile_K = min(tile_K, max_dim)
                    tile_N = min(tile_N, max_dim)
        
        # Simulate each layer
        per_layer_results = []
        total_cycles = 0
        total_stalls = 0
        total_ops = 0
        total_bytes = 0
        
        for layer in workload.layers:
            # Simulate the GEMM operation
            result = sa.simulate_gemm(
                M=layer.M,
                K=layer.K,
                N=layer.N,
                tile_M=tile_M,
                tile_K=tile_K,
                tile_N=tile_N,
                memory_stall_cycles=0
            )
            
            layer_bytes = layer.get_bytes(sa.precision_bytes)['total']
            
            per_layer_results.append({
                'name': layer.name,
                'cycles': result['total_cycles'],
                'utilization': result['utilization_pct'],
                'stalls': result['stall_cycles'],
                'bytes_moved': layer_bytes
            })
            
            total_cycles += result['total_cycles']
            total_stalls += result['stall_cycles']
            total_ops += result['total_ops']
            total_bytes += layer_bytes
        
        # Calculate overall metrics
        compute_cycles = total_cycles - total_stalls
        execution_time_ns = total_cycles / sa.frequency_ghz
        throughput_tflops = (total_ops / execution_time_ns) * 1e-3 if execution_time_ns > 0 else 0
        
        # Apply parallelism overhead
        if self._parallelism_config:
            comm_overhead = self._parallelism_config.get_communication_overhead_factor()
            total_cycles = int(total_cycles * comm_overhead)
            
            # Add collective communication time
            if self._parallelism_config.dp > 1 and self._network_config:
                # AllReduce for gradients
                grad_bytes = total_bytes  # Simplified
                allreduce_time_ns = self._network_config.estimate_collective_time_ns(
                    CollectiveType.ALL_REDUCE,
                    grad_bytes,
                    self._parallelism_config.dp
                )
                total_cycles += int(allreduce_time_ns * sa.frequency_ghz)
            
            if self._parallelism_config.tp > 1 and self._network_config:
                # AllGather for tensor parallel
                activation_bytes = batch * seq_len * 4096 * sa.precision_bytes  # Simplified
                allgather_time_ns = self._network_config.estimate_collective_time_ns(
                    CollectiveType.ALL_GATHER,
                    activation_bytes,
                    self._parallelism_config.tp
                )
                total_cycles += int(allgather_time_ns * sa.frequency_ghz * len(workload.layers))
        
        # Recalculate after parallelism
        execution_time_ns = total_cycles / sa.frequency_ghz
        throughput_tflops = (total_ops / execution_time_ns) * 1e-3 if execution_time_ns > 0 else 0
        
        # Estimate energy with hardware config if available
        if self._hardware_config:
            compute_energy_j = total_ops * self._hardware_config.core.energy_per_flop_j
            memory_energy_j = 0
            for level_name, level_config in self._hardware_config.memory_hierarchy.items():
                level_bytes = total_bytes * (0.3 if 'l0' in level_name else 0.5 if 'l1' in level_name else 0.8 if 'l2' in level_name else 1.0)
                memory_energy_j += level_bytes * 8 * level_config.energy_per_bit_pj * 1e-12
            total_energy_pj = (compute_energy_j + memory_energy_j) * 1e12
        else:
            compute_energy_pj_per_op = 0.5
            memory_energy_pj_per_bit = 5.0
            total_energy_pj = (total_ops * compute_energy_pj_per_op) + (total_bytes * 8 * memory_energy_pj_per_bit)
        
        # Detect bottlenecks
        bottlenecks = []
        overall_util = (total_ops / (compute_cycles * sa.peak_ops_per_cycle) * 100) if compute_cycles > 0 else 0
        
        if overall_util < 50:
            bottlenecks.append({
                'component': sa.name,
                'type': 'compute_underutilization',
                'severity': 'high' if overall_util < 25 else 'medium',
                'description': f'Systolic array utilization at {overall_util:.1f}%. Consider larger batch sizes or different tile sizes.'
            })
        
        if total_stalls > compute_cycles * 0.1:
            bottlenecks.append({
                'component': 'Memory System',
                'type': 'memory_bandwidth',
                'severity': 'high' if total_stalls > compute_cycles * 0.5 else 'medium',
                'description': f'Memory stalls account for {(total_stalls/max(total_cycles, 1)*100):.1f}% of execution time.'
            })
        
        # Build memory hierarchy response
        if self._hardware_config:
            memory_hierarchy = []
            for level_name, level_config in self._hardware_config.memory_hierarchy.items():
                factor = 0.3 if 'l0' in level_name else 0.5 if 'l1' in level_name else 0.8 if 'l2' in level_name else 1.0
                memory_hierarchy.append({
                    'name': level_config.name,
                    'bytes_accessed': total_bytes * factor,
                    'energy_pj': total_bytes * factor * 8 * level_config.energy_per_bit_pj,
                    'bandwidth_util': min(95, overall_util * (1.2 if 'l0' in level_name else 1.0 if 'l1' in level_name else 0.8 if 'l2' in level_name else 0.6))
                })
        else:
            memory_hierarchy = [
                {
                    'name': 'L0 (Registers)',
                    'bytes_accessed': total_bytes * 0.3,
                    'energy_pj': total_bytes * 0.3 * 8 * 0.5,
                    'bandwidth_util': min(95, overall_util * 1.2)
                },
                {
                    'name': 'L1 (Scratchpad)',
                    'bytes_accessed': total_bytes * 0.5,
                    'energy_pj': total_bytes * 0.5 * 8 * 2,
                    'bandwidth_util': min(90, overall_util)
                },
                {
                    'name': 'L2 (SRAM)',
                    'bytes_accessed': total_bytes * 0.8,
                    'energy_pj': total_bytes * 0.8 * 8 * 5,
                    'bandwidth_util': min(80, overall_util * 0.8)
                },
                {
                    'name': 'HBM/DRAM',
                    'bytes_accessed': total_bytes,
                    'energy_pj': total_bytes * 8 * 10,
                    'bandwidth_util': min(70, overall_util * 0.6)
                }
            ]
        
        result = {
            'summary': {
                'total_cycles': total_cycles,
                'compute_cycles': compute_cycles,
                'stall_cycles': total_stalls,
                'utilization_pct': overall_util,
                'throughput_tflops': throughput_tflops,
                'total_energy_pj': total_energy_pj,
                'power_watts': sa.tdp_watts
            },
            'per_layer': per_layer_results,
            'memory_hierarchy': memory_hierarchy,
            'bottlenecks': bottlenecks,
            'workload': workload.get_summary()
        }
        
        # Add config info if available
        if self._hardware_config:
            result['hardware_config'] = self._hardware_config.to_dict()
        if self._parallelism_config:
            result['parallelism_config'] = self._parallelism_config.to_dict()
        if self._network_config:
            result['network_config'] = self._network_config.to_dict()
        if model_config:
            result['model_config'] = model_config.to_dict()
        
        return result


# Global simulator instance
simulator = SimulatorAPI()
