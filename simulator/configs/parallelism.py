"""Parallelism configuration for distributed training/inference"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum


class ZeROStage(Enum):
    DISABLED = 0  # Standard DDP
    STAGE_1 = 1   # Optimizer state partitioning
    STAGE_2 = 2   # Gradient partitioning
    STAGE_3 = 3   # Parameter partitioning


@dataclass
class ParallelismConfig:
    """Parallelism configuration matching DeepFlow schema"""
    # Data Parallelism
    dp: int = 1  # Data parallel degree
    dp_zero_stage: ZeROStage = ZeROStage.DISABLED
    
    # Pipeline Parallelism
    pp: int = 1  # Pipeline parallel degree (number of stages)
    num_microbatches: int = 1  # Microbatches for pipeline
    
    # Tensor Parallelism
    tp: int = 1  # Tensor parallel degree
    tp_sequence_parallel: bool = True  # Enable sequence parallelism with TP
    
    # Context Parallelism (for long sequences)
    cp: int = 1  # Context parallel degree
    
    # Expert Parallelism (for MoE)
    ep: int = 1  # Expert parallel degree
    
    def get_total_devices(self) -> int:
        """Get total number of devices required"""
        return self.dp * self.pp * self.tp * self.cp * self.ep
    
    def get_world_size(self) -> int:
        """Alias for total devices"""
        return self.get_total_devices()
    
    def get_dp_group_size(self) -> int:
        """Get size of data parallel group"""
        return self.dp
    
    def get_tp_group_size(self) -> int:
        """Get size of tensor parallel group"""
        return self.tp
    
    def get_pp_group_size(self) -> int:
        """Get size of pipeline parallel group"""
        return self.pp
    
    def validate(self) -> bool:
        """Validate parallelism configuration"""
        if self.dp < 1 or self.pp < 1 or self.tp < 1:
            return False
        if self.num_microbatches < self.pp:
            return False  # Need at least pp microbatches for pipeline
        return True
    
    def get_communication_overhead_factor(self) -> float:
        """Estimate communication overhead factor"""
        overhead = 1.0
        
        # Data parallel: AllReduce gradients
        if self.dp > 1:
            overhead += 0.05 * (self.dp - 1)
        
        # Tensor parallel: AllReduce activations
        if self.tp > 1:
            overhead += 0.10 * (self.tp - 1)
        
        # Pipeline parallel: P2P communication
        if self.pp > 1:
            bubble_ratio = (self.pp - 1) / (self.num_microbatches + self.pp - 1)
            overhead += bubble_ratio * 0.5
        
        # Context parallel: AllToAll
        if self.cp > 1:
            overhead += 0.15 * (self.cp - 1)
        
        return overhead
    
    def get_memory_efficiency(self) -> float:
        """Estimate memory efficiency based on ZeRO stage"""
        if self.dp == 1:
            return 1.0
        
        if self.dp_zero_stage == ZeROStage.DISABLED:
            return 1.0
        elif self.dp_zero_stage == ZeROStage.STAGE_1:
            # Optimizer states partitioned
            return 1.0 + (2.0 / self.dp)  # Optimizer states reduced
        elif self.dp_zero_stage == ZeROStage.STAGE_2:
            # Gradients also partitioned
            return 1.0 + (3.0 / self.dp)
        else:  # STAGE_3
            # Parameters also partitioned
            return 1.0 + (4.0 / self.dp)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'dp': self.dp,
            'pp': self.pp,
            'tp': self.tp,
            'cp': self.cp,
            'ep': self.ep,
            'dp_zero_stage': self.dp_zero_stage.value,
            'num_microbatches': self.num_microbatches,
            'tp_sequence_parallel': self.tp_sequence_parallel,
            'total_devices': self.get_total_devices(),
            'communication_overhead': self.get_communication_overhead_factor(),
        }


# Common parallelism configurations
PARALLELISM_PRESETS: Dict[str, ParallelismConfig] = {
    'single_gpu': ParallelismConfig(dp=1, pp=1, tp=1),
    'dp_8': ParallelismConfig(dp=8, pp=1, tp=1),
    'tp_8': ParallelismConfig(dp=1, pp=1, tp=8),
    'dp_8_tp_8': ParallelismConfig(dp=8, pp=1, tp=8),
    'megatron_llm': ParallelismConfig(dp=8, pp=4, tp=8, num_microbatches=8),
    'zero3_dp_64': ParallelismConfig(dp=64, pp=1, tp=1, dp_zero_stage=ZeROStage.STAGE_3),
}
