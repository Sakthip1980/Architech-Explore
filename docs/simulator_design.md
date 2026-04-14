# System Performance & Power Modeling Simulator — Design Document

**Version:** 0.1 Draft  
**Status:** Brainstorm / Architecture  

---

## 1. Problem Statement

Existing simulators (DeepFlow, SCALE-Sim, Timeloop, ASTRA-sim) each solve a narrow slice of the problem well, but share a common pain:

> Every time you model a new workload or a new piece of hardware, you must re-derive the roofline model from scratch. There is no reusable, composable substrate.

The goal of this simulator is to fix that by building a **composable, physics-consistent hardware modeling framework** where:

- Hardware is described as typed, parameterized building blocks
- Physical properties are self-consistent (knowing 3 of 4 related properties derives the 4th)
- Workloads are ingested directly from TensorFlow Lite graphs — no manual specification
- The roofline model is written once and applied automatically to every operator
- Mapping (tiling, dataflow, fusion, pipelining) is a first-class sweepable dimension
- Power estimation flows naturally from the same activity model as performance

---

## 2. Architecture Overview

The simulator has six layers, each independently replaceable:

```
┌─────────────────────────────────────────────────┐
│               USER LAYER                        │
│  define system → load workload → run → results  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            COMPOSITION LAYER                    │
│  Block templates, hierarchical assembly,        │
│  connection model, constraint propagation       │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│             MAPPING LAYER                       │
│  Op → block assignment, tiling, fusion,         │
│  pipeline stages, dataflow sweep                │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            SIMULATION LAYER                     │
│  Analytical (fast) or Event-driven (accurate)   │
│  Transaction lifecycle, stall tracking,         │
│  utilization counters, backpressure             │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│             POWER LAYER                         │
│  Dynamic (activity × E/op, traffic × E/bit)     │
│  Static (leakage × area × time)                 │
│  Power domains, clock gating                    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│             RESULTS LAYER                       │
│  Cycles, time, energy, power                    │
│  Per-block breakdown, bottleneck ID             │
│  Roofline plot, utilization heatmap             │
│  Sensitivity charts                             │
└─────────────────────────────────────────────────┘
```

---

## 3. Hardware Building Blocks

### 3.1 The Three-Layer Model

Every block is defined at three levels:

```
Layer 1: PROPERTY SCHEMA  — "what properties can exist"
  frequency, bandwidth, power, capacity, flops, interface_width,
  Cdyn, voltage, leakage_current, energy_per_op, latency, ...

Layer 2: BLOCK DEFINITION — "this kind of block has these properties"
  Cache      : frequency, bandwidth, power, capacity, latency
  ComputeUnit: frequency, flops, power, Cdyn, voltage
  Interconnect: bandwidth, latency, width, energy_per_bit

Layer 3: INSTANCE — "a specific block with specific values"
  l1_cache = Cache(frequency=1e9, capacity="256KB", bandwidth="2TB/s")
  npu_core  = Compute(frequency=1e9, flops="4TOPS", voltage=0.9)
```

### 3.2 Block Types

| Block Type | Key Properties | Models |
|---|---|---|
| `ComputeUnit` | flops, frequency, Cdyn, voltage, ops_per_cycle | CPU core, GPU SM, NPU array, DSP |
| `SystolicArray` | rows, cols, frequency, dtype, energy_per_mac | TPU MXU, dedicated MAC array |
| `SRAM` | capacity, bandwidth, frequency, Cdyn, latency_cycles | L1/L2/L3 cache, scratchpad |
| `DRAM` | capacity, bandwidth, energy_per_bit, latency | HBM, LPDDR, GDDR |
| `Interconnect` | bandwidth, latency, width, frequency | NoC, PCIe, NVLink, AXI bus |
| `PowerDomain` | voltage, clock_freq, gate_enable | Voltage island, clock domain |
| `Chip` | sub-blocks, die_area, process_node | Composed chip |

### 3.3 Static vs Dynamic Properties

Each block carries both:

```
Static (set at configuration time):
  frequency, bandwidth, capacity, flops, Cdyn, voltage, interface_width

Dynamic (updated during simulation):
  utilization       0.0–1.0    how busy right now
  occupancy         0–capacity how full is the buffer
  queue_depth       int        requests waiting
  stall_cycles      int        cycles blocked waiting
  active_cycles     int        cycles doing real work
  idle_cycles       int        cycles doing nothing
  energy_consumed   float      running total (joules)
  transactions      int        count of completed ops/transfers
```

---

## 4. Self-Consistent Property System

### 4.1 Core Concept

The most important design decision: **properties are not independent numbers — they are nodes in a physics equation graph**.

When you specify enough properties, the system automatically derives the rest. When you specify conflicting values, it warns you. When you're under-specified, it tells you what's missing.

This eliminates the most common error in hardware modeling: inconsistent parameter sets.

### 4.2 Physical Equation Groups

**Power Group**
```
P_dynamic = Cdyn × V² × f          (CMOS switching power)
P_static  = I_leak × V              (leakage power)
P_total   = P_dynamic + P_static

Know any 3 → derive the 4th.
```

**Energy Group**
```
E = P × t                           (energy from power and time)
E = Q × V                           (energy from charge and voltage)
E_per_op = P_total / throughput     (energy cost per operation)

Know any 2 → derive the 3rd.
```

**Bandwidth Group**
```
BW = width × frequency              (peak interface bandwidth)
BW = data_rate / overhead_factor    (effective bandwidth)
latency = transfer_size / BW        (transfer time)

Know any 2 → derive the 3rd.
```

**Compute Group**
```
throughput = ops_per_cycle × frequency   (peak FLOPS/TOPS)
utilization = actual_ops / peak_ops      (efficiency)
effective_throughput = throughput × utilization

Know any 2 → derive the 3rd.
```

**Thermal Group**
```
T_junction = T_ambient + P_total × θ_ja  (junction temperature)
θ_ja = thermal resistance (package-dependent)

Know T_ambient, P_total, θ_ja → get T_junction.
Alternatively: set T_junction budget → get max allowed P_total.
```

**Timing Group**
```
time = cycles / frequency           (wall time from cycles)
cycles = ops / throughput           (cycles for a given workload)
latency_cycles = latency × frequency

Know any 2 → derive the 3rd.
```

### 4.3 How the Solver Works

The property system maintains a graph of equations. When a value is set, it propagates forward through the graph to compute dependent values:

```
User sets: Cdyn=50fF, voltage=0.9V, frequency=1GHz
System solves: P_dynamic = 50e-15 × (0.9)² × 1e9 = 40.5 mW ✓

User sets: P_dynamic=40.5mW, voltage=0.9V, frequency=1GHz
System solves: Cdyn = P_dynamic / (V² × f) = 50 fF ✓

User sets: P_dynamic=40.5mW, time=10ms
System solves: E_dynamic = 40.5e-3 × 10e-3 = 0.405 mJ ✓

User sets conflicting: Cdyn=50fF, voltage=0.9V, frequency=1GHz, P_dynamic=100mW
System warns: "P_dynamic conflicts: equation gives 40.5mW, you specified 100mW"
```

### 4.4 Unit Handling

All properties carry units. The system enforces dimensional consistency:

```
bandwidth: GB/s or TB/s or Gb/s  → normalized to bytes/second internally
capacity:  KB, MB, GB            → normalized to bytes internally
power:     mW, W                 → normalized to watts internally
energy:    pJ, nJ, mJ, J        → normalized to joules internally
frequency: MHz, GHz              → normalized to Hz internally
```

Users can write values in natural units: `capacity="256KB"`, `bandwidth="2TB/s"`. The system parses and normalizes automatically.

---

## 5. Connection Model

Connections are first-class objects — not just wires.

```
Connection:
  src_block        which block sends
  dst_block        which block receives
  interface_width  bits per transaction
  protocol         handshake type (valid/ready, req/ack, bus, NoC)
  shared           point-to-point OR shared bus (contention modeled)
  direction        unidirectional | bidirectional
  energy_per_bit   joules per bit transferred
```

**Transaction lifecycle over a connection:**

```
CREATED   → request issued by source block
QUEUED    → waiting in connection queue (backpressure starts here)
GRANTED   → arbitration won (for shared bus)
IN_FLIGHT → data moving across the link
RECEIVED  → destination block accepted
COMPLETED → response returned to source
```

Stalls, contention, and backpressure emerge naturally from this lifecycle — they are not special-cased.

---

## 6. Hierarchical Composition

Blocks compose into larger blocks recursively:

```
System
├── Chip
│   ├── Cluster 0
│   │   ├── ComputeCore (×4)
│   │   ├── L1 Cache (per core)
│   │   └── L2 Cache (shared within cluster)
│   ├── Cluster 1  (same structure)
│   ├── L3 Cache
│   └── NoC
└── Package
    ├── HBM Stack (×4)
    └── PCIe Link
```

Connections are defined at the level of the hierarchy where they make sense. L2↔L3 is a Chip-level connection. HBM↔Chip is a Package-level connection. This scales naturally from single-core to chiplet systems.

---

## 7. Workload Ingestion

### 7.1 TFLite Graph Parser

The simulator accepts a `.tflite` file directly. It:

1. Parses the flatbuffer format
2. Extracts the operator DAG (nodes = ops, edges = tensors)
3. Runs shape inference to determine tensor dimensions at every node
4. Auto-computes per-operator: FLOPs, parameter bytes, activation bytes, loop nest structure

### 7.2 Per-Operator Auto-Computation

```
Conv2D(input=1×224×224×3, filter=32×3×3×3, output=1×224×224×32):
  FLOPs           = 2 × 32 × 224 × 224 × 3 × 3 × 3 = 87M
  param_bytes     = 32 × 3 × 3 × 3 × sizeof(dtype)
  act_read_bytes  = depends on tiling (computed by mapper)
  act_write_bytes = depends on tiling (computed by mapper)
  loop_nest       = [N, K, H, W, C, R, S]  (for mapper to tile)
```

This is written once per operator type (Conv2D, MatMul, DepthwiseConv, Pooling, etc.) and never needs to be changed regardless of what workload or hardware is used.

---

## 8. Mapping Layer

### 8.1 What a Mapping Is

A mapping is a complete description of how a workload runs on a system:

```
Mapping = {
  placement:    op → block         (which block runs each op)
  dataflow:     op → DataflowSpec  (loop binding per op)
  fusions:      list of FusionGroups
  pipeline:     PipelineSpec
  splits:       list of SplitSpecs
  dispatch:     DispatchPolicy
}
```

### 8.2 Dataflow as Loop Binding

Dataflow (weight-stationary, input-stationary, output-stationary, or any custom) is represented as explicit loop bindings — which loop variable lives at which memory level:

```
For Conv2D loops [N, K, C, H, W, R, S]:

Weight-Stationary example:
  K → register level (stationary, reused across all N,H,W)
  C → L1 SRAM
  H, W → L2 SRAM
  N → DRAM (outermost)

Custom binding:
  K → register level, tile=16, spatial=4  (4-way parallel across PEs)
  C → L1, tile=8
  H, W → L2, tile=7
  N → DRAM, tile=1
```

Weight-stationary, input-stationary, and output-stationary are **named presets** in this space — not hardcoded modes.

### 8.3 Control Flow Dimensions

| Dimension | Description | Sweep |
|---|---|---|
| Tile sizes | Loop blocking per level | Integer grid |
| Loop order | Which loop is innermost | Permutations |
| Loop level | Which memory level | Discrete |
| Spatial parallelism | Which loops spread across PEs | Integer ≤ PE count |
| Op fusion | Fuse adjacent ops (eliminates SRAM round-trips) | Valid chain subsets |
| Pipeline stages | Ops in concurrent pipeline stages | DAG partitions |
| Op splitting | Split large op across multiple blocks | Block count |
| Dispatch policy | EAGER, BATCHED, PRIORITY, ROUND_ROBIN | Small enum |

### 8.4 Mapping Sweep

The mapper generates Pareto-optimal candidates across the full mapping space, pruning infeasible points (exceeds memory, violates bandwidth):

```
for each mapping in sweep.generate(graph, system):
    if not feasibility_check(mapping, system):
        continue
    result = sim.evaluate(mapping)
    results.append((mapping, result))

pareto = pareto_front(results, objectives=["cycles", "energy"])
```

---

## 9. Simulation Engine

### 9.1 Two Modes

**Mode 1: Analytical (fast — use for sweeps)**
- Per op: `cycles = max(flops/throughput, bytes/bandwidth)` (roofline)
- DAG critical path gives total cycles
- Good for exploring thousands of mappings quickly

**Mode 2: Event-Driven (accurate — use for detailed analysis)**
- Each block has an event queue
- Ops dispatched when dependencies satisfied and block is free
- DMA/compute overlap emerges automatically
- Models backpressure, contention, stall cascades

### 9.2 The Roofline Function — Written Once

```python
def roofline(flops, read_bytes, write_bytes, hw_block):
    compute_cycles = flops / hw_block.throughput
    memory_cycles  = (read_bytes + write_bytes) / hw_block.bandwidth
    cycles = max(compute_cycles, memory_cycles)
    bottleneck = "compute" if compute_cycles >= memory_cycles else "memory"
    arithmetic_intensity = flops / (read_bytes + write_bytes)
    return cycles, bottleneck, arithmetic_intensity
```

This function is never rewritten. Every new operator type just provides `flops`, `read_bytes`, `write_bytes` — pure shape math.

### 9.3 Resource State Tracking

Each block tracks full resource utilization:

```
Per resource (port / execution unit / buffer):
  state: IDLE | BUSY | STALLED
  active_cycles, stall_cycles, idle_cycles
  transactions completed
  queue depth over time
```

This gives a complete picture of where cycles are lost and which resources are the bottleneck.

---

## 10. Power Model

### 10.1 Dynamic Power

```
E_compute = ops_executed × E_per_op
E_memory  = bytes_transferred × E_per_bit    (per memory level)
E_network = bytes_transferred × E_per_bit    (per link)

P_dynamic = E_dynamic / simulation_time
```

### 10.2 Static Power

```
P_static = I_leak × V    (per block, always on)
E_static = P_static × active_time
```

### 10.3 Power Domains

Blocks belong to power domains. Domains can be clock-gated when idle:

```python
domain = PowerDomain(voltage=0.9, clock_gate=True)
domain.add(core_0, core_1, l1_cache)

# If domain is idle for N cycles, clock gating kicks in
# P_static drops to P_retention (much lower)
```

### 10.4 Thermal Model

```
T_junction = T_ambient + P_total × θ_ja

Use case:
  Set T_junction budget (e.g., 85°C) → get max allowed P_total
  Run simulation → check if actual power stays within budget
```

---

## 11. Results and Analysis

### 11.1 Output Metrics

| Metric | Granularity |
|---|---|
| Total cycles | System |
| Wall time | System |
| Total energy | System, per block, per op |
| Average power | System, per block, per domain |
| Peak power | System |
| Utilization | Per block, per resource |
| Stall breakdown | Per block: compute stall, memory stall, network stall |
| Bottleneck | Which block/resource limits performance |
| Arithmetic intensity | Per op, system roofline position |

### 11.2 Built-In Visualizations

- **Roofline plot**: every op plotted as (arithmetic intensity, achieved throughput)
- **Utilization heatmap**: per-block utilization over simulation time
- **Stall waterfall**: where cycles are lost, layer by layer
- **Power timeline**: instantaneous power per domain over time
- **Pareto front**: energy vs cycles across all explored mappings
- **Sensitivity chart**: which parameter change has the most impact on performance

### 11.3 Sensitivity Analysis

```python
sweep = ParameterSweep(system)
sweep.vary("hbm.bandwidth",  [500, 1000, 2000, 4000])  # GB/s
sweep.vary("npu.flops",      [1, 2, 4, 8])              # TOPS
sweep.vary("l2.capacity",    [256, 512, 1024, 2048])    # KB

results = sweep.run(workload, mapping)
results.plot_sensitivity()  # reveals the dominant bottleneck
```

---

## 12. Extensibility Design

### 12.1 The Block Interface Contract

Every block — regardless of internal complexity — presents the same interface to the simulator:

```python
class Block:
    def can_accept(self, transaction) -> bool
    def submit(self, transaction) -> None
    def tick(self) -> None          # advance by 1 cycle
    def utilization(self) -> float
    def energy_so_far(self) -> float
```

The simulator never looks inside a block. Adding a new block type = implement these 5 methods. This is the extensibility guarantee.

### 12.2 Adding a New Operator Type

Adding a new TFLite operator type requires only:

```python
class MyNewOp(Op):
    def flops(self, mapping) -> float:
        # pure shape math, no simulation logic
        return ...

    def read_bytes(self, mapping) -> float:
        return ...

    def write_bytes(self, mapping) -> float:
        return ...

    def loop_nest(self) -> LoopNest:
        return ...
```

The roofline engine, power model, and mapper work automatically on this new op.

---

## 13. Module Structure

```
sim/
├── hardware/
│   ├── properties.py    # property schema, units, equation solver
│   ├── blocks.py        # ComputeUnit, SRAM, DRAM, Interconnect
│   ├── system.py        # System (block graph, topology)
│   └── registry.py      # block type registry
├── workload/
│   ├── tflite_parser.py # flatbuffer → Op DAG
│   ├── ops.py           # per-op flops/bytes math
│   └── graph.py         # Op DAG, shape inference
├── mapping/
│   ├── mapper.py        # greedy + tiling sweep mapper
│   ├── loop_nest.py     # tiling math, data reuse
│   └── dataflow.py      # loop binding, WS/IS/OS presets
├── engine/
│   ├── roofline.py      # THE roofline function (written once)
│   ├── analytical.py    # Mode 1: analytical DAG scheduling
│   └── event_driven.py  # Mode 2: discrete event simulation
├── power/
│   └── model.py         # dynamic + static + thermal
└── results/
    ├── result.py        # SimResult dataclass
    └── viz.py           # plots, heatmaps, sensitivity charts
```

---

## 14. Comparison to Existing Simulators

| Capability | DeepFlow | SCALE-Sim | Timeloop | This Simulator |
|---|---|---|---|---|
| Composable hardware blocks | No | No | Partial | Yes |
| Self-consistent properties | No | No | No | Yes |
| TFLite ingestion | No | No | No | Yes |
| Auto roofline (any op) | No | No | No | Yes |
| Dataflow sweep | No | Partial | Yes | Yes |
| Control flow sweep | No | No | No | Yes |
| Event-driven simulation | Via AstraSim | No | No | Yes |
| Power model | Partial | Via Accelergy | Via Accelergy | Built-in |
| Thermal model | No | No | No | Yes |
| Sensitivity analysis | Manual | Manual | Manual | Built-in |

---

*End of design document — version 0.1*
