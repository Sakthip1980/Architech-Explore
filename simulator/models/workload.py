"""Workload definitions for DNN layer simulation"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import csv
import io


@dataclass
class GEMMLayer:
    """A single GEMM operation: C[M,N] = A[M,K] × B[K,N]"""
    name: str
    M: int  # Output rows / Batch
    K: int  # Inner dimension
    N: int  # Output columns
    
    def get_ops(self) -> int:
        """Total operations (multiply-accumulate = 2 ops)"""
        return 2 * self.M * self.K * self.N
    
    def get_bytes(self, precision: int = 2) -> Dict[str, int]:
        """Get data sizes in bytes"""
        return {
            'A': self.M * self.K * precision,
            'B': self.K * self.N * precision,
            'C': self.M * self.N * precision,
            'total': (self.M * self.K + self.K * self.N + self.M * self.N) * precision
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'M': self.M,
            'K': self.K,
            'N': self.N,
            'ops': self.get_ops(),
            'bytes': self.get_bytes()
        }


@dataclass
class ConvLayer:
    """Convolution layer that maps to GEMM via im2col"""
    name: str
    batch: int      # N
    in_channels: int  # C
    out_channels: int  # K
    input_height: int  # H
    input_width: int   # W
    kernel_height: int = 3
    kernel_width: int = 3
    stride: int = 1
    padding: int = 1
    
    def to_gemm(self) -> GEMMLayer:
        """Convert convolution to equivalent GEMM dimensions"""
        # Output spatial dimensions
        out_h = (self.input_height + 2 * self.padding - self.kernel_height) // self.stride + 1
        out_w = (self.input_width + 2 * self.padding - self.kernel_width) // self.stride + 1
        
        # GEMM dimensions via im2col
        M = self.batch * out_h * out_w  # Output elements
        K = self.in_channels * self.kernel_height * self.kernel_width  # Filter size
        N = self.out_channels  # Number of filters
        
        return GEMMLayer(name=self.name, M=M, K=K, N=N)
    
    def to_dict(self) -> Dict[str, Any]:
        gemm = self.to_gemm()
        return {
            'name': self.name,
            'type': 'conv',
            'batch': self.batch,
            'in_channels': self.in_channels,
            'out_channels': self.out_channels,
            'input_size': f'{self.input_height}x{self.input_width}',
            'kernel_size': f'{self.kernel_height}x{self.kernel_width}',
            'gemm_M': gemm.M,
            'gemm_K': gemm.K,
            'gemm_N': gemm.N,
            'ops': gemm.get_ops()
        }


class Workload:
    """Collection of layers representing a DNN workload"""
    
    def __init__(self, name: str = "Custom"):
        self.name = name
        self.layers: List[GEMMLayer] = []
        
    def add_gemm(self, name: str, M: int, K: int, N: int):
        """Add a GEMM layer directly"""
        self.layers.append(GEMMLayer(name=name, M=M, K=K, N=N))
        
    def add_conv(self, layer: ConvLayer):
        """Add a convolution layer (converted to GEMM)"""
        self.layers.append(layer.to_gemm())
    
    def add_attention(
        self,
        name: str,
        batch: int,
        seq_len: int,
        hidden_dim: int,
        num_heads: int = 8
    ):
        """
        Add attention layer components:
        - Q, K, V projections
        - Attention scores (Q × K^T)
        - Attention output (scores × V)
        - Output projection
        """
        head_dim = hidden_dim // num_heads
        
        # Q, K, V projections: [B*S, D] × [D, D] -> [B*S, D]
        self.add_gemm(f"{name}_qkv", batch * seq_len, hidden_dim, hidden_dim * 3)
        
        # Attention scores: [B*H, S, d] × [B*H, d, S] -> [B*H, S, S]
        self.add_gemm(f"{name}_attn", batch * num_heads * seq_len, head_dim, seq_len)
        
        # Attention × V: [B*H, S, S] × [B*H, S, d] -> [B*H, S, d]
        self.add_gemm(f"{name}_attn_v", batch * num_heads * seq_len, seq_len, head_dim)
        
        # Output projection: [B*S, D] × [D, D] -> [B*S, D]
        self.add_gemm(f"{name}_out", batch * seq_len, hidden_dim, hidden_dim)
    
    def add_ffn(
        self,
        name: str,
        batch: int,
        seq_len: int,
        hidden_dim: int,
        ffn_dim: int = None
    ):
        """
        Add feed-forward network layers:
        - Up projection: hidden -> 4*hidden (default)
        - Down projection: 4*hidden -> hidden
        """
        if ffn_dim is None:
            ffn_dim = hidden_dim * 4
        
        # Up projection
        self.add_gemm(f"{name}_up", batch * seq_len, hidden_dim, ffn_dim)
        
        # Down projection
        self.add_gemm(f"{name}_down", batch * seq_len, ffn_dim, hidden_dim)
    
    def add_transformer_layer(
        self,
        name: str,
        batch: int,
        seq_len: int,
        hidden_dim: int,
        num_heads: int = 8,
        ffn_dim: int = None
    ):
        """Add a complete transformer layer (attention + FFN)"""
        self.add_attention(f"{name}_attn", batch, seq_len, hidden_dim, num_heads)
        self.add_ffn(f"{name}_ffn", batch, seq_len, hidden_dim, ffn_dim)
    
    @classmethod
    def from_csv(cls, csv_content: str, name: str = "Imported") -> 'Workload':
        """
        Parse workload from CSV format.
        
        Expected format:
        Layer,M,N,K
        layer1,1024,1024,2048
        ...
        
        Or convolution format:
        Layer,N,C,H,W,K,R,S
        conv1,1,3,224,224,64,3,3
        ...
        """
        workload = cls(name=name)
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            if 'M' in row and 'K' in row and 'N' in row:
                # GEMM format
                workload.add_gemm(
                    name=row.get('Layer', row.get('layer', 'layer')),
                    M=int(row['M']),
                    K=int(row['K']),
                    N=int(row['N'])
                )
            elif 'H' in row and 'W' in row and 'R' in row:
                # Convolution format
                conv = ConvLayer(
                    name=row.get('Layer', row.get('layer', 'conv')),
                    batch=int(row.get('N', row.get('batch', 1))),
                    in_channels=int(row['C']),
                    out_channels=int(row['K']),
                    input_height=int(row['H']),
                    input_width=int(row['W']),
                    kernel_height=int(row['R']),
                    kernel_width=int(row.get('S', row['R']))
                )
                workload.add_conv(conv)
        
        return workload
    
    def get_total_ops(self) -> int:
        """Get total operations across all layers"""
        return sum(layer.get_ops() for layer in self.layers)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get workload summary"""
        return {
            'name': self.name,
            'num_layers': len(self.layers),
            'total_ops': self.get_total_ops(),
            'layers': [layer.to_dict() for layer in self.layers]
        }


# Pre-defined workloads
def get_resnet50_workload(batch: int = 1) -> Workload:
    """ResNet-50 workload (simplified to key GEMM layers)"""
    workload = Workload("ResNet-50")
    
    # First conv
    workload.add_conv(ConvLayer("conv1", batch, 3, 64, 224, 224, 7, 7, stride=2, padding=3))
    
    # Simplified: add representative bottleneck blocks
    # Stage 2: 256 -> 64 -> 256
    for i in range(3):
        workload.add_conv(ConvLayer(f"stage2_b{i}_1", batch, 256, 64, 56, 56, 1, 1, padding=0))
        workload.add_conv(ConvLayer(f"stage2_b{i}_2", batch, 64, 64, 56, 56, 3, 3))
        workload.add_conv(ConvLayer(f"stage2_b{i}_3", batch, 64, 256, 56, 56, 1, 1, padding=0))
    
    # FC layer
    workload.add_gemm("fc", batch, 2048, 1000)
    
    return workload


def get_gpt2_workload(batch: int = 1, seq_len: int = 512) -> Workload:
    """GPT-2 (124M) workload"""
    workload = Workload("GPT-2")
    hidden_dim = 768
    num_layers = 12
    num_heads = 12
    
    for i in range(num_layers):
        workload.add_transformer_layer(
            f"layer_{i}",
            batch=batch,
            seq_len=seq_len,
            hidden_dim=hidden_dim,
            num_heads=num_heads
        )
    
    # Final projection to vocab
    workload.add_gemm("lm_head", batch * seq_len, hidden_dim, 50257)
    
    return workload


def get_llama7b_workload(batch: int = 1, seq_len: int = 2048) -> Workload:
    """LLaMA 7B workload (simplified)"""
    workload = Workload("LLaMA-7B")
    hidden_dim = 4096
    num_layers = 32
    num_heads = 32
    ffn_dim = 11008
    
    for i in range(num_layers):
        workload.add_transformer_layer(
            f"layer_{i}",
            batch=batch,
            seq_len=seq_len,
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            ffn_dim=ffn_dim
        )
    
    return workload
