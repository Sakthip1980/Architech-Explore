"""Model configuration presets based on DeepFlow reference configs"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class AttentionType(Enum):
    MHA = "mha"  # Multi-Head Attention
    GQA = "gqa"  # Grouped Query Attention
    MQA = "mqa"  # Multi-Query Attention
    MLA = "mla"  # Multi-head Latent Attention (not implemented)


class ModelType(Enum):
    GPT = "gpt"
    LLAMA = "llama"
    QWEN = "qwen"
    PHI = "phi"
    BERT = "bert"
    GEMM = "gemm"
    LSTM = "lstm"


class RunType(Enum):
    TRAINING = "training"
    INFERENCE = "inference"


@dataclass
class AttentionConfig:
    """Attention mechanism configuration"""
    attention_type: AttentionType = AttentionType.MHA
    num_heads: int = 32
    kv_heads: Optional[int] = None  # For GQA/MQA
    use_flashattention: bool = False
    attention_tile_size: int = 256
    
    def get_kv_heads(self) -> int:
        """Get number of KV heads (defaults to num_heads for MHA)"""
        if self.attention_type == AttentionType.MQA:
            return 1
        elif self.kv_heads is not None:
            return self.kv_heads
        return self.num_heads


@dataclass
class ModelConfig:
    """Complete model configuration matching DeepFlow schema"""
    name: str
    model_type: ModelType = ModelType.GPT
    run_type: RunType = RunType.TRAINING
    
    # Architecture parameters
    batch_size: int = 1
    seq_len: int = 2048
    hidden_dim: int = 4096
    intermediate_size: int = 11008  # FFN intermediate dim
    vocab_size: int = 32000
    num_layers: int = 32
    
    # Attention configuration
    attention: AttentionConfig = field(default_factory=AttentionConfig)
    
    # MoE (Mixture of Experts)
    num_experts: int = 1
    top_k: int = 1
    
    # Other options
    tied_embeddings: bool = False
    
    def get_kv_cache_size_bytes(self, kv_bytes: float = 2.0, context_len: Optional[int] = None) -> int:
        """Calculate KV cache size in bytes for inference"""
        kv_heads = self.attention.get_kv_heads()
        head_dim = self.hidden_dim // self.attention.num_heads
        seq = context_len if context_len else self.seq_len
        
        # KV cache per layer: batch * 2 (K+V) * kv_heads * head_dim * seq_len
        kv_per_layer = self.batch_size * 2 * kv_heads * head_dim * seq * kv_bytes
        return int(kv_per_layer * self.num_layers)
    
    def get_training_memory_bytes(self, param_bytes: float = 2.0, optimizer_bytes: float = 8.0) -> Dict:
        """Estimate training memory requirements"""
        total_params = self.get_total_params()
        
        params_mem = total_params * param_bytes
        grads_mem = total_params * param_bytes
        optimizer_mem = total_params * optimizer_bytes  # Adam: m + v in FP32
        
        # Activation memory (rough estimate)
        activation_per_layer = self.batch_size * self.seq_len * self.hidden_dim * param_bytes * 10
        activations_mem = activation_per_layer * self.num_layers
        
        return {
            'params_bytes': int(params_mem),
            'gradients_bytes': int(grads_mem),
            'optimizer_bytes': int(optimizer_mem),
            'activations_bytes': int(activations_mem),
            'total_bytes': int(params_mem + grads_mem + optimizer_mem + activations_mem),
        }
    
    def get_inference_memory_bytes(self, param_bytes: float = 2.0, kv_bytes: float = 2.0) -> Dict:
        """Estimate inference memory requirements"""
        total_params = self.get_total_params()
        
        params_mem = total_params * param_bytes
        kv_cache_mem = self.get_kv_cache_size_bytes(kv_bytes)
        
        # Activation memory for single forward pass (smaller than training)
        activation_mem = self.batch_size * self.seq_len * self.hidden_dim * param_bytes * 3
        
        return {
            'params_bytes': int(params_mem),
            'kv_cache_bytes': int(kv_cache_mem),
            'activations_bytes': int(activation_mem),
            'total_bytes': int(params_mem + kv_cache_mem + activation_mem),
        }
    
    def get_total_params(self) -> int:
        """Estimate total parameter count"""
        # Embedding
        embedding_params = self.vocab_size * self.hidden_dim
        
        # Attention per layer: Q, K, V, O projections
        kv_heads = self.attention.get_kv_heads()
        head_dim = self.hidden_dim // self.attention.num_heads
        qkvo_params = (
            self.hidden_dim * self.hidden_dim +  # Q
            self.hidden_dim * (kv_heads * head_dim) +  # K
            self.hidden_dim * (kv_heads * head_dim) +  # V
            self.hidden_dim * self.hidden_dim  # O
        )
        
        # FFN per layer
        ffn_params = 2 * self.hidden_dim * self.intermediate_size
        if self.model_type == ModelType.LLAMA:
            ffn_params = 3 * self.hidden_dim * self.intermediate_size  # SwiGLU
        
        # Layer norm params
        ln_params = 2 * self.hidden_dim * 2  # 2 layer norms per layer
        
        # Total per layer
        params_per_layer = qkvo_params + ffn_params + ln_params
        
        # MoE multiplier
        if self.num_experts > 1:
            params_per_layer = qkvo_params + ln_params + (ffn_params * self.num_experts)
        
        total = embedding_params + (params_per_layer * self.num_layers)
        
        if not self.tied_embeddings:
            total += embedding_params  # Output embedding
        
        return total
    
    def get_layers_gemm_dims(self) -> List[Dict]:
        """Get GEMM dimensions for each layer operation"""
        B = self.batch_size
        S = self.seq_len
        H = self.hidden_dim
        I = self.intermediate_size
        kv_heads = self.attention.get_kv_heads()
        head_dim = H // self.attention.num_heads
        
        gemms = []
        
        # Per transformer layer
        for layer in range(self.num_layers):
            # Q projection: [B*S, H] x [H, H]
            gemms.append({'name': f'layer{layer}_q_proj', 'M': B * S, 'K': H, 'N': H})
            
            # K projection: [B*S, H] x [H, kv_dim]
            kv_dim = kv_heads * head_dim
            gemms.append({'name': f'layer{layer}_k_proj', 'M': B * S, 'K': H, 'N': kv_dim})
            
            # V projection
            gemms.append({'name': f'layer{layer}_v_proj', 'M': B * S, 'K': H, 'N': kv_dim})
            
            # Attention: [B*num_heads, S, head_dim] x [B*num_heads, head_dim, S]
            # This is batched GEMM, simplified as single GEMM
            gemms.append({'name': f'layer{layer}_attn_score', 'M': B * self.attention.num_heads * S, 'K': head_dim, 'N': S})
            gemms.append({'name': f'layer{layer}_attn_value', 'M': B * self.attention.num_heads * S, 'K': S, 'N': head_dim})
            
            # O projection
            gemms.append({'name': f'layer{layer}_o_proj', 'M': B * S, 'K': H, 'N': H})
            
            # FFN (depends on model type)
            if self.model_type == ModelType.LLAMA:
                # SwiGLU: gate, up, down
                gemms.append({'name': f'layer{layer}_ffn_gate', 'M': B * S, 'K': H, 'N': I})
                gemms.append({'name': f'layer{layer}_ffn_up', 'M': B * S, 'K': H, 'N': I})
                gemms.append({'name': f'layer{layer}_ffn_down', 'M': B * S, 'K': I, 'N': H})
            else:
                # Standard FFN
                gemms.append({'name': f'layer{layer}_ffn_up', 'M': B * S, 'K': H, 'N': I})
                gemms.append({'name': f'layer{layer}_ffn_down', 'M': B * S, 'K': I, 'N': H})
        
        return gemms
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            'name': self.name,
            'model_type': self.model_type.value,
            'run_type': self.run_type.value,
            'batch_size': self.batch_size,
            'seq_len': self.seq_len,
            'hidden_dim': self.hidden_dim,
            'num_layers': self.num_layers,
            'num_heads': self.attention.num_heads,
            'attention_type': self.attention.attention_type.value,
            'use_flashattention': self.attention.use_flashattention,
            'vocab_size': self.vocab_size,
            'num_experts': self.num_experts,
            'total_params': self.get_total_params(),
        }
        
        # Add memory estimates based on run type
        if self.run_type == RunType.TRAINING:
            result['memory'] = self.get_training_memory_bytes()
        else:
            result['memory'] = self.get_inference_memory_bytes()
            result['kv_cache_bytes'] = self.get_kv_cache_size_bytes()
        
        return result


# =============================================================================
# Model Presets (based on DeepFlow configs)
# =============================================================================

def _llama2_7b() -> ModelConfig:
    """Llama 2 7B configuration"""
    return ModelConfig(
        name="Llama2-7B",
        model_type=ModelType.LLAMA,
        run_type=RunType.TRAINING,
        batch_size=1,
        seq_len=2048,
        hidden_dim=4096,
        intermediate_size=11008,
        vocab_size=32000,
        num_layers=32,
        attention=AttentionConfig(
            attention_type=AttentionType.MHA,
            num_heads=32,
            use_flashattention=False,
        ),
        tied_embeddings=True,
    )


def _llama3_8b() -> ModelConfig:
    """Llama 3.1 8B configuration"""
    return ModelConfig(
        name="Llama3.1-8B",
        model_type=ModelType.LLAMA,
        run_type=RunType.INFERENCE,
        batch_size=1,
        seq_len=8192,
        hidden_dim=4096,
        intermediate_size=14336,
        vocab_size=128256,
        num_layers=32,
        attention=AttentionConfig(
            attention_type=AttentionType.GQA,
            num_heads=32,
            kv_heads=8,
            use_flashattention=True,
            attention_tile_size=256,
        ),
    )


def _llama3_70b() -> ModelConfig:
    """Llama 3.1 70B configuration"""
    return ModelConfig(
        name="Llama3.1-70B",
        model_type=ModelType.LLAMA,
        run_type=RunType.INFERENCE,
        batch_size=1,
        seq_len=8192,
        hidden_dim=8192,
        intermediate_size=28672,
        vocab_size=128256,
        num_layers=80,
        attention=AttentionConfig(
            attention_type=AttentionType.GQA,
            num_heads=64,
            kv_heads=8,
            use_flashattention=True,
        ),
    )


def _llama3_405b() -> ModelConfig:
    """Llama 3.1 405B configuration"""
    return ModelConfig(
        name="Llama3.1-405B",
        model_type=ModelType.LLAMA,
        run_type=RunType.INFERENCE,
        batch_size=1,
        seq_len=8192,
        hidden_dim=16384,
        intermediate_size=53248,
        vocab_size=128256,
        num_layers=126,
        attention=AttentionConfig(
            attention_type=AttentionType.GQA,
            num_heads=128,
            kv_heads=8,
            use_flashattention=True,
        ),
    )


def _gpt2() -> ModelConfig:
    """GPT-2 configuration"""
    return ModelConfig(
        name="GPT-2",
        model_type=ModelType.GPT,
        run_type=RunType.TRAINING,
        batch_size=1,
        seq_len=1024,
        hidden_dim=768,
        intermediate_size=3072,
        vocab_size=50257,
        num_layers=12,
        attention=AttentionConfig(
            attention_type=AttentionType.MHA,
            num_heads=12,
        ),
    )


def _gpt3_175b() -> ModelConfig:
    """GPT-3 175B configuration"""
    return ModelConfig(
        name="GPT-3 175B",
        model_type=ModelType.GPT,
        run_type=RunType.TRAINING,
        batch_size=1,
        seq_len=2048,
        hidden_dim=12288,
        intermediate_size=49152,
        vocab_size=50257,
        num_layers=96,
        attention=AttentionConfig(
            attention_type=AttentionType.MHA,
            num_heads=96,
        ),
    )


def _bert_base() -> ModelConfig:
    """BERT Base configuration"""
    return ModelConfig(
        name="BERT-Base",
        model_type=ModelType.BERT,
        run_type=RunType.TRAINING,
        batch_size=32,
        seq_len=512,
        hidden_dim=768,
        intermediate_size=3072,
        vocab_size=30522,
        num_layers=12,
        attention=AttentionConfig(
            attention_type=AttentionType.MHA,
            num_heads=12,
        ),
    )


def _bert_large() -> ModelConfig:
    """BERT Large configuration"""
    return ModelConfig(
        name="BERT-Large",
        model_type=ModelType.BERT,
        run_type=RunType.TRAINING,
        batch_size=32,
        seq_len=512,
        hidden_dim=1024,
        intermediate_size=4096,
        vocab_size=30522,
        num_layers=24,
        attention=AttentionConfig(
            attention_type=AttentionType.MHA,
            num_heads=16,
        ),
    )


def _resnet50_gemms() -> ModelConfig:
    """ResNet-50 represented as GEMM workload"""
    return ModelConfig(
        name="ResNet-50",
        model_type=ModelType.GEMM,
        run_type=RunType.TRAINING,
        batch_size=32,
        seq_len=1,  # Not applicable for CNNs
        hidden_dim=2048,
        intermediate_size=512,
        vocab_size=1000,  # ImageNet classes
        num_layers=50,
    )


MODEL_PRESETS: Dict[str, ModelConfig] = {
    'llama2_7b': _llama2_7b(),
    'llama3_8b': _llama3_8b(),
    'llama3_70b': _llama3_70b(),
    'llama3_405b': _llama3_405b(),
    'gpt2': _gpt2(),
    'gpt3_175b': _gpt3_175b(),
    'bert_base': _bert_base(),
    'bert_large': _bert_large(),
    'resnet50': _resnet50_gemms(),
}


def get_model_preset(name: str) -> ModelConfig:
    """Get a model configuration preset by name"""
    if name not in MODEL_PRESETS:
        available = list(MODEL_PRESETS.keys())
        raise ValueError(f"Unknown model preset '{name}'. Available: {available}")
    return MODEL_PRESETS[name]
