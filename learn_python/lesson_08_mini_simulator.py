# ============================================================
# LESSON 8: Build Your First Mini Simulator
# ============================================================
# Goal: Put everything together to build a small but real
#       hardware performance simulator from scratch.
#
# What it simulates:
#   - A simple system: CPU -> Cache -> DRAM
#   - A workload of memory requests
#   - Outputs latency, bandwidth utilisation, and bottleneck
#
# Concepts used: variables, functions, lists, dicts,
#                classes, dataclass, enum, file I/O, loops
# ============================================================

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

# ============================================================
# STEP 1: Define result types with dataclasses and enums
# ============================================================

class Bottleneck(Enum):
    COMPUTE = "compute-bound"
    MEMORY  = "memory-bound"
    IDLE    = "underutilised"

@dataclass
class RequestResult:
    """Outcome of one memory request routed through the hierarchy."""
    source_level: str
    latency_ns:   float
    bytes_moved:  int
    cache_hit:    bool

@dataclass
class SimulationReport:
    """Aggregated metrics for the whole simulation run."""
    total_requests:   int    = 0
    total_latency_ns: float  = 0.0
    total_bytes:      int    = 0
    cache_hits:       int    = 0
    results:          List[RequestResult] = field(default_factory=list)

    def avg_latency_ns(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ns / self.total_requests

    def cache_hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    def effective_bandwidth_gbps(self, elapsed_ns: float) -> float:
        if elapsed_ns == 0:
            return 0.0
        return self.total_bytes / (elapsed_ns * 1e-9) / 1e9

    def print_summary(self):
        print("=" * 50)
        print("  SIMULATION REPORT")
        print("=" * 50)
        print(f"  Total requests  : {self.total_requests}")
        print(f"  Avg latency     : {self.avg_latency_ns():.1f} ns")
        print(f"  Cache hit rate  : {self.cache_hit_rate():.0%}")
        print(f"  Total bytes     : {self.total_bytes / 1024:.1f} KB")
        print("=" * 50)

# ============================================================
# STEP 2: Hardware modules
# ============================================================

class MemoryLevel:
    """One level in the memory hierarchy (cache or DRAM)."""

    def __init__(self, name: str, latency_ns: float,
                 bandwidth_gbps: float, hit_rate: float = 1.0):
        self.name          = name
        self.latency_ns    = latency_ns
        self.bandwidth_gbps = bandwidth_gbps
        self.hit_rate      = hit_rate   # probability this level serves the request
        self.requests_served = 0

    def try_serve(self, size_bytes: int):
        """
        Attempt to serve a request.
        Returns (success, latency_ns).
        """
        import random
        hit = random.random() < self.hit_rate
        if hit:
            transfer_ns = (size_bytes / (self.bandwidth_gbps * 1e9)) * 1e9
            latency = self.latency_ns + transfer_ns
            self.requests_served += 1
            return True, latency
        return False, 0.0

    def __repr__(self):
        return (f"MemoryLevel({self.name}, latency={self.latency_ns}ns, "
                f"bw={self.bandwidth_gbps}GB/s, hit_rate={self.hit_rate:.0%})")

# ============================================================
# STEP 3: The memory hierarchy
# ============================================================

class MemoryHierarchy:
    """Ordered list of memory levels. Requests waterfall from L1 to DRAM."""

    def __init__(self):
        self.levels: List[MemoryLevel] = []

    def add_level(self, level: MemoryLevel):
        self.levels.append(level)
        return self    # allows chaining: hierarchy.add(l1).add(l2)

    def process_request(self, size_bytes: int) -> RequestResult:
        """
        Walk levels from fastest to slowest until one serves the request.
        This mirrors the real cache-miss waterfall.
        """
        for level in self.levels:
            hit, latency_ns = level.try_serve(size_bytes)
            if hit:
                return RequestResult(
                    source_level=level.name,
                    latency_ns=latency_ns,
                    bytes_moved=size_bytes,
                    cache_hit=(level.name != "DRAM"),  # DRAM access = cache miss
                )
        # Fallback: if nothing hit (shouldn't happen with DRAM at end)
        last = self.levels[-1]
        transfer_ns = (size_bytes / (last.bandwidth_gbps * 1e9)) * 1e9
        return RequestResult(last.name, last.latency_ns + transfer_ns,
                             size_bytes, False)

    def print_config(self):
        print("Memory Hierarchy:")
        for i, lvl in enumerate(self.levels):
            print(f"  L{i+1}: {lvl}")

# ============================================================
# STEP 4: The workload generator
# ============================================================

def generate_workload(num_requests: int, avg_size_bytes: int = 64) -> List[int]:
    """
    Generate a list of memory request sizes.
    Sizes are randomly chosen near avg_size_bytes (multiples of 64B).
    """
    import random
    sizes = []
    for _ in range(num_requests):
        # Randomly pick a nearby cache-line multiple
        multiplier = random.choice([1, 1, 1, 2, 4, 8])   # 1 is most common
        sizes.append(avg_size_bytes * multiplier)
    return sizes

# ============================================================
# STEP 5: The simulator engine
# ============================================================

def run_simulation(hierarchy: MemoryHierarchy,
                   workload: List[int]) -> SimulationReport:
    """Drive each request through the memory hierarchy and collect results."""
    report = SimulationReport()

    for size_bytes in workload:
        result = hierarchy.process_request(size_bytes)
        report.total_requests   += 1
        report.total_latency_ns += result.latency_ns
        report.total_bytes      += result.bytes_moved
        if result.cache_hit:
            report.cache_hits += 1
        report.results.append(result)

    return report

# ============================================================
# STEP 6: Bottleneck analysis
# ============================================================

def analyse_bottleneck(report: SimulationReport,
                       compute_util: float,
                       memory_util: float) -> Bottleneck:
    THRESHOLD = 0.85
    if compute_util >= THRESHOLD and memory_util >= THRESHOLD:
        return Bottleneck.COMPUTE   # usually compute when both saturated
    elif compute_util >= THRESHOLD:
        return Bottleneck.COMPUTE
    elif memory_util >= THRESHOLD:
        return Bottleneck.MEMORY
    return Bottleneck.IDLE

# ============================================================
# STEP 7: Save report to JSON
# ============================================================

def save_report(report: SimulationReport, filepath: str):
    data = {
        "total_requests":   report.total_requests,
        "avg_latency_ns":   report.avg_latency_ns(),
        "cache_hit_rate":   report.cache_hit_rate(),
        "total_bytes_kb":   report.total_bytes / 1024,
        "per_level_counts": {},
    }
    for result in report.results:
        data["per_level_counts"][result.source_level] = \
            data["per_level_counts"].get(result.source_level, 0) + 1

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Report saved to {filepath}")

# ============================================================
# STEP 8: MAIN — wire it all together and run
# ============================================================

if __name__ == "__main__":

    # --- Build the memory hierarchy ---
    hierarchy = MemoryHierarchy()
    hierarchy.add_level(MemoryLevel("L1_cache", latency_ns=1,   bandwidth_gbps=200,  hit_rate=0.80))
    hierarchy.add_level(MemoryLevel("L2_cache", latency_ns=5,   bandwidth_gbps=100,  hit_rate=0.90))
    hierarchy.add_level(MemoryLevel("DRAM",     latency_ns=80,  bandwidth_gbps=51.2, hit_rate=1.00))
    hierarchy.print_config()
    print()

    # --- Generate workload ---
    import random
    random.seed(42)   # fix seed for reproducibility
    workload = generate_workload(num_requests=1000, avg_size_bytes=64)
    print(f"Workload: {len(workload)} requests, "
          f"avg size {sum(workload)/len(workload):.0f} bytes")
    print()

    # --- Run simulation ---
    report = run_simulation(hierarchy, workload)

    # --- Print results ---
    report.print_summary()
    print()

    # --- Show which level served how many requests ---
    level_counts = {}
    for r in report.results:
        level_counts[r.source_level] = level_counts.get(r.source_level, 0) + 1
    print("Requests served per level:")
    for level, count in level_counts.items():
        print(f"  {level:10s}: {count:4d}  ({count/len(report.results):.0%})")
    print()

    # --- Bottleneck analysis ---
    # Pretend we measured these utilisation values from a profiler:
    compute_util = 0.45
    mem_util     = report.cache_hit_rate()   # proxy for memory pressure
    bottleneck = analyse_bottleneck(report, compute_util, mem_util)
    print(f"System bottleneck: {bottleneck.value}")
    print()

    # --- Save to file ---
    save_report(report, "/tmp/simulation_report.json")
    print("\nOpen /tmp/simulation_report.json to inspect the JSON output.")

# ============================================================
# WHAT YOU JUST BUILT
# ============================================================
# A working memory hierarchy simulator that:
#   - Models L1 cache, L2 cache, and DRAM with real latencies
#   - Routes requests from fastest to slowest level
#   - Collects latency and hit-rate statistics
#   - Detects system bottlenecks
#   - Saves results to JSON
#
# This is the same pattern as simulator/models/cache.py and
# the hierarchy used in simulator/models/systolic_array.py.
#
# CHALLENGE: Extend this simulator to:
#   1. Add an HBM level between L2 and DRAM
#   2. Track total energy (latency * power per level)
#   3. Plot a histogram of per-level latencies
# ============================================================
