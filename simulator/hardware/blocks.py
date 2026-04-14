"""
Hardware block hierarchy built on top of the property system.

Block extends Module (from simulator/base.py) and adds:
  - PropertySchema ownership for self-consistent physics properties
  - Parent/child hierarchy for power and clock domain inheritance
  - Concrete block types: ComputeBlock, MemoryBlock, InterconnectBlock
  - Domain containers: PowerDomain, ClockDomain
  - bridge function: block_from_module() wraps existing Module subclasses
"""

from typing import Optional, Dict, Any, List
from ..base import Module
from .properties import PropertySchema, parse_unit


class Block(Module):
    """
    Base hardware block: a Module that owns a PropertySchema.

    Properties can be set as strings ("1GHz", "50fF") or plain numbers.
    Getting a property checks the local schema first, then walks up the
    parent chain (voltage from PowerDomain, frequency from ClockDomain).
    """

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self._schema = PropertySchema()
        self._parent: Optional['Block'] = None
        self._children: List['Block'] = []
        self._power_domain: Optional['PowerDomain'] = None
        self._clock_domain: Optional['ClockDomain'] = None

    # ------------------------------------------------------------------
    # Property interface
    # ------------------------------------------------------------------

    def set_property(self, name: str, value) -> 'Block':
        """
        Set a property by name. value can be a string ("1GHz") or number.
        Triggers the self-consistent solver automatically.
        Returns self for chaining.
        """
        self._schema.set(name, value)
        return self

    def get_property(self, name: str) -> Optional[float]:
        """
        Return the SI value for a named property.

        Lookup order:
          1. Local schema (user-set or derived)
          2. PowerDomain parent (voltage, I_leak, P_total …)
          3. ClockDomain parent (frequency)
          4. Block parent (anything)
        """
        val = self._schema.get(name)
        if val is not None:
            return val
        # Inherit from domains
        if self._power_domain is not None:
            val = self._power_domain._schema.get(name)
            if val is not None:
                return val
        if self._clock_domain is not None:
            val = self._clock_domain._schema.get(name)
            if val is not None:
                return val
        # Inherit from structural parent
        if self._parent is not None:
            return self._parent.get_property(name)
        return None

    def missing_properties(self) -> List[str]:
        """Return property names that are unset in the local schema."""
        return self._schema.missing()

    # ------------------------------------------------------------------
    # Hierarchy management
    # ------------------------------------------------------------------

    def add_child(self, child: 'Block') -> 'Block':
        """Add a child block; sets child's parent to self."""
        child._parent = self
        self._children.append(child)
        return self

    def set_power_domain(self, domain: 'PowerDomain') -> 'Block':
        """Attach a PowerDomain so this block inherits voltage etc."""
        self._power_domain = domain
        return self

    def set_clock_domain(self, domain: 'ClockDomain') -> 'Block':
        """Attach a ClockDomain so this block inherits frequency."""
        self._clock_domain = domain
        return self

    # ------------------------------------------------------------------
    # Module ABC stubs (concrete blocks override as needed)
    # ------------------------------------------------------------------

    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Default: return latency based on bandwidth property if available."""
        bw = self.get_property('BW')
        if bw and bw > 0:
            latency_s = size_bytes / bw
            latency_ns = latency_s * 1e9
            self.metrics.total_requests += 1
            self.metrics.total_latency_ns += latency_ns
            return latency_ns
        return 0.0

    def get_bandwidth(self) -> float:
        """Return BW in GB/s (from property schema)."""
        bw = self.get_property('BW')
        if bw is not None:
            return bw / 1e9  # B/s -> GB/s
        return 0.0

    def get_power(self) -> float:
        """Return P_total in Watts (from property schema)."""
        pt = self.get_property('P_total')
        if pt is not None:
            return pt
        pd = self.get_property('P_dynamic')
        ps = self.get_property('P_static')
        if pd is not None and ps is not None:
            return pd + ps
        return 0.0

    # ------------------------------------------------------------------
    # Block interface contract (used by event-driven engine in Phase 5)
    # ------------------------------------------------------------------

    def can_accept(self) -> bool:
        """True if this block can accept a new operation right now."""
        return True  # default: always ready; subclasses may override

    def submit(self, op_id: int, flops: float, bytes_read: float,
               bytes_write: float) -> int:
        """Submit work; returns estimated completion cycle."""
        return 0  # concrete engines override this

    def tick(self, cycle: int) -> List[int]:
        """Advance one cycle; return list of completed op_ids."""
        return []

    def utilization(self) -> float:
        """Return fraction of cycles spent doing useful work (0–1)."""
        if self.metrics.total_cycles == 0:
            return 0.0
        active = self.metrics.total_requests  # proxy
        return min(active / max(self.metrics.total_cycles, 1), 1.0)

    def energy_so_far(self) -> float:
        """Return energy consumed so far in Joules."""
        e = self.get_property('energy')
        if e is not None:
            return e
        pt = self.get_power()
        t = self.get_property('time')
        if t is not None:
            return pt * t
        return 0.0

    # ------------------------------------------------------------------
    # Status / repr
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status['properties'] = self._schema.to_dict()
        status['power_domain'] = (self._power_domain.name
                                   if self._power_domain else None)
        status['clock_domain'] = (self._clock_domain.name
                                   if self._clock_domain else None)
        return status

    def __repr__(self):
        props = self._schema.to_dict()
        n_props = len(props)
        return f"{self.__class__.__name__}('{self.name}', {n_props} props set)"


# ---------------------------------------------------------------------------
# Concrete block types
# ---------------------------------------------------------------------------

class ComputeBlock(Block):
    """
    A compute unit (CPU core, NPU, systolic array tile, etc.).

    Typical properties: frequency, ops_per_cycle, throughput,
    P_dynamic, P_static, Cdyn, voltage.
    """

    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Estimate latency for a compute request."""
        tp = self.get_property('throughput')   # FLOP/s
        if tp and tp > 0 and request_type == 'compute':
            # Treat size_bytes as op count for compute requests
            latency_s = size_bytes / tp
            latency_ns = latency_s * 1e9
        else:
            latency_ns = super().process_request(request_type, size_bytes)
        self.metrics.total_requests += 1
        self.metrics.total_latency_ns += latency_ns
        return latency_ns


class MemoryBlock(Block):
    """
    A memory module (SRAM, DRAM, HBM, NVM, scratchpad, cache …).

    Typical properties: BW, latency_s, size_bytes, width_bytes,
    frequency, P_dynamic, P_static.
    """

    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Estimate read/write latency."""
        # Fixed access latency (if set) + transfer time
        lat_fixed = self.get_property('latency_s') or 0.0
        bw = self.get_property('BW')
        transfer_s = (size_bytes / bw) if (bw and bw > 0) else 0.0
        latency_ns = (lat_fixed + transfer_s) * 1e9
        self.metrics.total_requests += 1
        self.metrics.total_latency_ns += latency_ns
        return latency_ns


class InterconnectBlock(Block):
    """
    A link or bus (AXI, PCIe, CXL, NoC hop …).

    Typical properties: BW, latency_s, width_bytes, frequency.
    """
    # Inherits process_request from Block (bandwidth-based latency)


class PowerDomain(Block):
    """
    Container that provides shared voltage / leakage current to child blocks.

    Set 'voltage' and optionally 'I_leak' here; child blocks inherit them.
    """

    def __init__(self, name: str, voltage_str: str = '1.0V',
                 i_leak_str: Optional[str] = None):
        super().__init__(name)
        self.set_property('voltage', voltage_str)
        if i_leak_str:
            self.set_property('I_leak', i_leak_str)

    def process_request(self, request_type: str, size_bytes: int) -> float:
        return 0.0

    def get_bandwidth(self) -> float:
        return 0.0

    def get_power(self) -> float:
        return 0.0


class ClockDomain(Block):
    """
    Container that provides a shared clock frequency to child blocks.

    Set 'frequency' here; child blocks inherit it.
    """

    def __init__(self, name: str, frequency_str: str = '1GHz'):
        super().__init__(name)
        self.set_property('frequency', frequency_str)

    def process_request(self, request_type: str, size_bytes: int) -> float:
        return 0.0

    def get_bandwidth(self) -> float:
        return 0.0

    def get_power(self) -> float:
        return 0.0


# ---------------------------------------------------------------------------
# Bridge: wrap existing Module subclasses as Block instances
# ---------------------------------------------------------------------------

# Map of attribute names on existing Module subclasses → property names in schema
_MODULE_ATTR_MAP = {
    # frequency — various naming conventions
    'frequency_ghz':    ('frequency', lambda v: v * 1e9),
    'clock_freq_ghz':   ('frequency', lambda v: v * 1e9),
    'frequency_mhz':    ('frequency', lambda v: v * 1e6),
    'clock_freq_mhz':   ('frequency', lambda v: v * 1e6),
    # bandwidth
    'bandwidth_gbps':          ('BW', lambda v: v * 1e9),
    'memory_bandwidth_gbps':   ('BW', lambda v: v * 1e9),
    'peak_bandwidth_gbps':     ('BW', lambda v: v * 1e9),
    'bus_bandwidth_gbps':      ('BW', lambda v: v * 1e9),
    'total_bandwidth_gbps':    ('BW', lambda v: v * 1e9),
    'bandwidth_gbps_per_link': ('BW', lambda v: v * 1e9),
    # power / TDP
    'tdp_watts':    ('P_total', lambda v: v),
    'power_watts':  ('P_total', lambda v: v),
    # storage capacity — mapped to 'capacity_bytes' (NOT part of BW equation)
    'capacity_gb':      ('capacity_bytes', lambda v: int(v * 1024**3)),
    'capacity_mb':      ('capacity_bytes', lambda v: int(v * 1024**2)),
    'sram_size_mb':     ('capacity_bytes', lambda v: int(v * 1024**2)),
    'on_chip_sram_mb':  ('capacity_bytes', lambda v: int(v * 1024**2)),
    # interface width
    'bus_width_bytes':   ('width_bytes', lambda v: v),
    'data_width_bytes':  ('width_bytes', lambda v: v),
    # latency (fixed access latency — NOT derived from clock_period)
    'read_latency_ns':    ('latency_s', lambda v: v * 1e-9),
    'access_latency_ns':  ('latency_s', lambda v: v * 1e-9),
    # NOTE: clock_period_ns is NOT mapped — it is internal to DRAM timing
    # and must not be confused with transfer latency
}


def block_from_module(module: Module) -> Block:
    """
    Create a Block wrapping an existing Module subclass.

    Reads known numeric attributes from the module and populates
    a PropertySchema automatically. No existing code is modified.

    Example
    -------
    from simulator.models.npu import NPU
    npu = NPU('myNPU', mac_units=1024, frequency_ghz=1.0, ...)
    block = block_from_module(npu)
    block.get_property('frequency')   # -> 1e9
    block.get_property('BW')          # -> bandwidth in B/s
    """
    # Determine block type from module class name
    class_name = module.__class__.__name__.lower()
    if any(k in class_name for k in ('cpu', 'gpu', 'npu', 'dsp', 'systolic')):
        blk = ComputeBlock(module.name)
    elif any(k in class_name for k in ('dram', 'hbm', 'nvm', 'cache', 'sram',
                                        'scratchpad', 'memory')):
        blk = MemoryBlock(module.name)
    elif any(k in class_name for k in ('axi', 'pcie', 'cxl', 'interconnect',
                                        'dma', 'bus', 'link')):
        blk = InterconnectBlock(module.name)
    else:
        blk = Block(module.name)

    # Copy connections (they remain as Module references)
    blk.connections = module.connections.copy()

    # Load known attributes into the property schema
    for attr, (prop_name, converter) in _MODULE_ATTR_MAP.items():
        val = getattr(module, attr, None)
        if val is not None:
            try:
                si_val = converter(val)
                blk._schema.set(prop_name, si_val)
            except Exception:
                pass  # skip attributes that can't be converted

    # ── NPU-specific: mac_units → ops_per_cycle (with precision multiplier)
    mac_units = getattr(module, 'mac_units', None)
    precision = getattr(module, 'precision', 'FP32')
    if mac_units is not None and not blk._schema.get('ops_per_cycle'):
        _precision_mul = {
            'INT4': 8, 'INT8': 4, 'FP16': 2, 'BF16': 2, 'TF32': 2, 'FP32': 1
        }
        mul = _precision_mul.get(str(precision).upper(), 1)
        # Each MAC = multiply + accumulate = 2 FLOPs; scale by precision
        ops_per_cycle = mac_units * 2 * mul
        blk._schema.set('ops_per_cycle', ops_per_cycle)

    # ── SystolicArray-specific: array_height × array_width → ops_per_cycle
    arr_h = getattr(module, 'array_height', None)
    arr_w = getattr(module, 'array_width',  None)
    if arr_h is not None and arr_w is not None and not blk._schema.get('ops_per_cycle'):
        # Each cell does one MAC per cycle = 2 FLOPs
        blk._schema.set('ops_per_cycle', arr_h * arr_w * 2)

    # ── DRAM-specific: compute bandwidth from geometry + frequency
    # geometry = {bus_width: bits, ...}; frequency_mhz is transfer rate
    if not blk._schema.get('BW'):
        geo = getattr(module, 'geometry', None)
        freq_mhz = getattr(module, 'frequency_mhz', None)
        if isinstance(geo, dict) and freq_mhz is not None:
            bus_width_bits = geo.get('bus_width', 0)
            bus_width_bytes = bus_width_bits / 8
            # DDR transfers on both clock edges
            bw = bus_width_bytes * freq_mhz * 1e6 * 2
            if bw > 0:
                blk._schema.set('BW', bw)
                blk._schema.set('width_bytes', bus_width_bytes)

    # Also capture any generic numeric attributes not in the map
    # by storing them in the block's _config dict for reference
    blk._config.update({k: v for k, v in vars(module).items()
                         if isinstance(v, (int, float)) and
                         not k.startswith('_') and
                         k not in ('id',)})

    return blk
