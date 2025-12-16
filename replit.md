# ArchSim - System Architecture Simulator

## Overview

ArchSim is a modular system architecture simulation and exploration tool. It provides a visual drag-and-drop interface for designing computer system architectures (CPUs, memory hierarchies, interconnects, accelerators) and runs Python-based simulations to analyze performance metrics like latency, bandwidth, and power consumption.

The application combines a React-based visual flow editor with a Python simulation backend, allowing users to build hardware system graphs and simulate their behavior under different workloads.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **React + TypeScript** single-page application built with Vite
- **React Flow** library for the node-based visual graph editor where users drag-and-drop hardware components
- **Tailwind CSS v4** with a dark engineering theme and custom CSS variables
- **shadcn/ui** component library (New York style) with Radix UI primitives
- **Wouter** for lightweight client-side routing
- **TanStack React Query** for server state management and API calls
- **React Hook Form** for form handling in the properties panel

### Backend Architecture
- **Express.js** server with TypeScript
- **Python simulator bridge** - Node.js spawns Python processes to run simulations via `simulator_bridge.py`
- The simulator API (`simulator_api.py`) translates graph data from the frontend into Python hardware module instances
- State persistence via JSON file (`.simulator_state.json`) for maintaining system configuration between API calls

### Data Flow
1. User creates/modifies architecture graph in React Flow editor
2. Frontend sends graph data (nodes + edges) to Express API
3. Express spawns Python process with graph data as CLI argument
4. Python builds hardware system from graph, runs simulation cycles
5. Results (latency, bandwidth, power metrics) returned to frontend

### Simulation Engine (Python)
- Located in `/simulator/` directory
- Base `Module` class with abstract `process_request()` method
- Hardware models: DRAM, HBM, SRAM Cache, NVM, Scratchpad (memory); CPU, GPU, NPU, DSP (compute); AXI, PCIe, CXL, NoC (interconnects); DMA, Memory Controller (specialized)
- `System` class orchestrates simulation, generates workloads, collects metrics

### Configuration System (NEW)
Located in `/simulator/configs/`:
- **hardware_presets.py**: A100, H100, V100, TPU v3 presets with 4-level memory hierarchy (L0-L3), core configs, network configs
- **model_presets.py**: LLM models (Llama2/3, GPT-2/3, BERT) with attention configs (MHA/GQA), MoE support, memory estimation
- **precision.py**: FP32/FP16/BF16/FP8/INT8 modes with mixed precision and param storage modes
- **parallelism.py**: DP/TP/PP/CP parallelism with ZeRO stages 0-3, microbatch support
- **network.py**: Ring/Switch/FullyConnected/2D Torus topologies with collective algorithms (AllReduce, AllGather, etc.)

### Key Design Patterns
- **Component-based architecture** - Hardware modules are self-contained with their own timing/power models
- **Bridge pattern** - Node.js to Python communication via CLI/JSON for simulation execution
- **In-memory storage** - User data stored in memory (MemStorage class), database schema exists but storage implementation uses Maps
- **Preset-based configuration** - Hardware/model/network presets matching DeepFlow and Astra-Sim reference simulators

## Features (Aligned with DeepFlow/Astra-Sim)

### Hardware Configuration
- **GPU Presets**: NVIDIA A100 80GB, H100 SXM5 80GB, V100 32GB
- **TPU Support**: Google TPU v3
- **4-Level Memory Hierarchy**: Register File (L0) → Shared Memory (L1) → L2 Cache → HBM/DRAM (L3)
- **Per-level energy model**: J/bit for each memory level
- **Dataflow modes**: Weight Stationary, Output Stationary, Input Stationary, Best

### Model/Workload Support
- **LLM Models**: Llama2-7B, Llama3.1-8B/70B/405B, GPT-2, GPT-3 175B
- **Transformer Components**: BERT-Base, BERT-Large
- **CNNs**: ResNet-50 (as GEMM workload)
- **Attention Types**: MHA, GQA (Grouped Query Attention), MQA
- **FlashAttention**: Toggle support for memory-efficient attention
- **MoE**: Mixture of Experts with configurable num_experts and top_k

### Parallelism Strategies
- **Data Parallel (DP)**: With ZeRO optimization stages 0-3
- **Tensor Parallel (TP)**: With sequence parallelism option
- **Pipeline Parallel (PP)**: With microbatch scheduling
- **Context Parallel (CP)**: For long sequence training

### Network Topology
- **Topologies**: Ring, Switch, FullyConnected, 2D Torus
- **Network Presets**: DGX V100, HGX H100 (8/16/32 GPU), TPU v3 Pod
- **Collective Operations**: AllReduce, AllGather, ReduceScatter, AllToAll
- **Algorithms**: Ring, HalvingDoubling, DoubleBinaryTree, Direct

### Training vs Inference
- **Training Mode**: FWD+BWD with optimizer state memory estimation
- **Inference Mode**: KV-cache modeling with memory estimation
- **Memory Estimation**: Params, gradients, optimizer states, activations

## External Dependencies

### Database
- **PostgreSQL** with Drizzle ORM configured (schema in `shared/schema.ts`)
- Currently uses in-memory storage (`MemStorage`) - database integration ready but not active
- Schema includes basic user table with id, username, password

### Third-Party Services
- No external API integrations
- No authentication services configured (basic user schema exists)

### Key NPM Packages
- `reactflow` - Visual node-based graph editor
- `drizzle-orm` + `drizzle-zod` - Database ORM and schema validation
- `@tanstack/react-query` - Server state management
- `express` - HTTP server
- Full shadcn/ui component set (dialogs, forms, tabs, etc.)

### Python Dependencies
- Standard library only (no requirements.txt visible)
- Simulator is self-contained with no external Python packages

## API Endpoints

- `POST /api/simulator/build` - Build system from graph data
- `POST /api/simulator/run` - Run simulation cycles
- `POST /api/simulator/build-and-run` - Build and run in one call
- `GET /api/simulator/status` - Get current system status
- `POST /api/simulator/workload` - Run workload-based simulation with configs
- `GET /api/simulator/presets` - Get all available hardware/model/network presets
