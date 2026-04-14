"""
Self-consistent property system for hardware blocks.

Properties are linked by physics equations. Setting any N-1 values
in a group automatically derives the Nth.  Conflicts are flagged as
ConflictWarning; missing values are reported via .missing().

Unit parsing:  "256KB" -> 262144 (bytes)
               "2TB/s" -> 2e12  (bytes/s)
               "1GHz"  -> 1e9   (Hz)
               "50fF"  -> 5e-14 (Farads)
               "0.9V"  -> 0.9   (Volts)
               "100mW" -> 0.1   (Watts)
All values are stored in canonical SI units internally.
"""

import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, Optional, Any


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

_BYTE_SCALE = {
    'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3,
    'TB': 1024**4, 'PB': 1024**5,
}

# Map each unit token -> (SI scale factor, canonical unit)
# SI scale is the multiplier to convert that unit to its SI base.
_UNIT_TABLE = {
    # --- frequency
    'THz':  (1e12,  'Hz'),
    'GHz':  (1e9,   'Hz'),
    'MHz':  (1e6,   'Hz'),
    'KHz':  (1e3,   'Hz'),
    'kHz':  (1e3,   'Hz'),
    'Hz':   (1.0,   'Hz'),
    # --- voltage
    'mV':   (1e-3,  'V'),
    'V':    (1.0,   'V'),
    # --- current
    'uA':   (1e-6,  'A'),
    'mA':   (1e-3,  'A'),
    'A':    (1.0,   'A'),
    # --- capacitance
    'fF':   (1e-15, 'F'),
    'pF':   (1e-12, 'F'),
    'nF':   (1e-9,  'F'),
    'uF':   (1e-6,  'F'),
    'mF':   (1e-3,  'F'),
    'F':    (1.0,   'F'),
    # --- power
    'uW':   (1e-6,  'W'),
    'mW':   (1e-3,  'W'),
    'W':    (1.0,   'W'),
    'kW':   (1e3,   'W'),
    'MW':   (1e6,   'W'),
    # --- energy
    'pJ':   (1e-12, 'J'),
    'nJ':   (1e-9,  'J'),
    'uJ':   (1e-6,  'J'),
    'mJ':   (1e-3,  'J'),
    'J':    (1.0,   'J'),
    # --- time
    'ps':   (1e-12, 's'),
    'ns':   (1e-9,  's'),
    'us':   (1e-6,  's'),
    'ms':   (1e-3,  's'),
    's':    (1.0,   's'),
    # --- thermal / resistance
    'C/W':  (1.0,   'C/W'),
    'Ohm':  (1.0,   'Ohm'),
    # --- temperature
    'C':    (1.0,   'C'),
    # --- cycles (dimensionless count)
    'cycles': (1.0, 'cycles'),
    # --- dimensionless
    '':     (1.0,   ''),
}

# FLOP/s prefixes handled separately (see parse_unit)
_FLOPS_PREFIXES = [('T', 1e12), ('G', 1e9), ('M', 1e6), ('K', 1e3), ('k', 1e3), ('', 1.0)]


def parse_unit(raw) -> tuple:
    """
    Parse a value+unit string into (SI_float, canonical_unit_str).

    Examples
    --------
    parse_unit("50fF")   -> (5e-14, 'F')
    parse_unit("1GHz")   -> (1e9,   'Hz')
    parse_unit("256KB")  -> (262144, 'B')
    parse_unit("2TB/s")  -> (2199023255552.0, 'B/s')
    parse_unit("0.9V")   -> (0.9, 'V')
    parse_unit(1e9)      -> (1e9, '')   # plain number
    """
    if isinstance(raw, (int, float)):
        return (float(raw), '')

    raw = str(raw).strip()

    # --- bandwidth: number[unit]B/s  e.g. "2TB/s", "900GB/s", "10B/s"
    for suffix in ('TB/s', 'GB/s', 'MB/s', 'KB/s', 'B/s'):
        if raw.endswith(suffix):
            num_str = raw[: len(raw) - len(suffix)]
            byte_unit = suffix[:-2]  # 'TB/s' -> 'TB'  'B/s' -> 'B'... wait
            # Actually suffix[:-2] gives 'TB', 'GB', 'MB', 'KB', 'B'[wait 'B/s'[:-2]='B']
            # Let's be explicit:
            byte_unit = suffix.replace('/s', '')  # 'TB', 'GB', 'MB', 'KB', 'B'
            scale = _BYTE_SCALE.get(byte_unit, 1)
            try:
                return (float(num_str) * scale, 'B/s')
            except ValueError:
                pass

    # --- byte sizes: number[unit]B  e.g. "256KB", "4MB", "1GB"
    # Must check longer suffixes first to avoid 'B' eating 'KB'
    for suffix in ('PB', 'TB', 'GB', 'MB', 'KB', 'B'):
        if raw.endswith(suffix) and '/' not in raw:
            num_str = raw[: len(raw) - len(suffix)]
            if num_str:
                try:
                    return (float(num_str) * _BYTE_SCALE[suffix], 'B')
                except ValueError:
                    pass

    # --- FLOP/s  e.g. "10TFLOP/s", "2.5GFLOP/s"
    for prefix, scale in _FLOPS_PREFIXES:
        token = prefix + 'FLOP/s'
        if raw.endswith(token):
            num_str = raw[: len(raw) - len(token)]
            if num_str:
                try:
                    return (float(num_str) * scale, 'FLOP/s')
                except ValueError:
                    pass

    # --- TFLOP/GFLOP/MFLOP count and ops counts  e.g. "2TFLOP", "500Mops"
    for prefix, scale in _FLOPS_PREFIXES:
        for base in ('FLOP', 'ops'):
            token = prefix + base
            if raw.endswith(token):
                num_str = raw[: len(raw) - len(token)]
                if num_str:
                    try:
                        return (float(num_str) * scale, base)
                    except ValueError:
                        pass

    # --- Known unit tokens (longest first to avoid prefix ambiguity)
    for unit in sorted(_UNIT_TABLE.keys(), key=len, reverse=True):
        if not unit:
            continue
        if raw.endswith(unit):
            num_str = raw[: len(raw) - len(unit)]
            if not num_str:
                continue
            scale, canonical = _UNIT_TABLE[unit]
            try:
                return (float(num_str) * scale, canonical)
            except ValueError:
                continue

    # --- plain number with no unit
    try:
        return (float(raw), '')
    except ValueError:
        raise ValueError(f"Cannot parse unit string: {repr(raw)}")


# ---------------------------------------------------------------------------
# ConflictWarning
# ---------------------------------------------------------------------------

class ConflictWarning(UserWarning):
    """Raised when a user-set property contradicts a derived value."""


# ---------------------------------------------------------------------------
# PropertyNode
# ---------------------------------------------------------------------------

@dataclass
class PropertyNode:
    """One property slot in a PropertySchema."""
    name: str
    value: Optional[float] = None   # SI value; None = unset
    unit: str = ''                  # canonical unit string
    source: str = 'unset'           # 'unset' | 'user' | 'derived'

    def is_set(self) -> bool:
        return self.value is not None

    def __repr__(self):
        if self.value is None:
            return f"PropertyNode({self.name!r}, unset)"
        return f"PropertyNode({self.name!r}, {self.value:.6g} {self.unit})"


# ---------------------------------------------------------------------------
# PropertySchema — the main public class
# ---------------------------------------------------------------------------

class PropertySchema:
    """
    Owns a collection of PropertyNodes linked by physics equation groups.

    Usage
    -----
    schema = PropertySchema()
    schema.set("Cdyn", "50fF")
    schema.set("voltage", "0.9V")
    schema.set("frequency", "1GHz")
    print(schema.get("P_dynamic"))   # -> 0.0405  (Watts = 40.5 mW)
    """

    # All property names and their canonical units
    _PROPERTY_UNITS: Dict[str, str] = {
        # --- power group
        'Cdyn':        'F',
        'voltage':     'V',
        'frequency':   'Hz',
        'I_leak':      'A',
        'P_dynamic':   'W',
        'P_static':    'W',
        'P_total':     'W',
        # --- energy group
        'time':        's',
        'throughput':  'FLOP/s',
        'energy':      'J',
        'E_per_op':    'J',
        # --- bandwidth group
        'width_bytes':        'B',   # bus/link width in bytes
        'BW':                 'B/s', # peak bandwidth in bytes/s
        'BW_bytes_per_cycle': 'B',   # bandwidth in bytes/cycle
        'transfer_bytes':     'B',   # bytes in ONE transfer request (for latency calc)
        'latency_s':          's',   # transfer latency = transfer_bytes / BW
        # --- storage (NOT linked to bandwidth equation)
        'capacity_bytes':     'B',   # total storage capacity
        # --- compute group
        'ops_per_cycle':          'FLOP',
        'throughput_per_cycle':   'FLOP',
        'actual_ops':             'FLOP',
        'peak_ops':               'FLOP',
        'utilization':            '',
        # --- thermal group
        'T_ambient':   'C',
        'theta_ja':    'C/W',
        'T_junction':  'C',
        # --- timing group
        'cycles':      'cycles',
        # time already in power group; reused here
    }

    def __init__(self):
        self._nodes: Dict[str, PropertyNode] = {
            name: PropertyNode(name=name, unit=unit)
            for name, unit in self._PROPERTY_UNITS.items()
        }
        self._user_set: set = set()  # names explicitly set by user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, name: str, value_raw) -> 'PropertySchema':
        """
        Set a property by name and raw value string (or number).
        Triggers the solver after setting.
        Returns self for chaining.
        """
        if name not in self._nodes:
            raise KeyError(f"Unknown property {name!r}. "
                           f"Known: {sorted(self._nodes)}")
        si_val, _unit = parse_unit(value_raw)
        node = self._nodes[name]
        node.value = si_val
        node.source = 'user'
        self._user_set.add(name)
        self._solve()
        return self

    def get(self, name: str) -> Optional[float]:
        """Return the SI value for a property, or None if unknown."""
        if name not in self._nodes:
            raise KeyError(f"Unknown property {name!r}.")
        return self._nodes[name].value

    def get_node(self, name: str) -> PropertyNode:
        """Return the full PropertyNode for a property."""
        if name not in self._nodes:
            raise KeyError(f"Unknown property {name!r}.")
        return self._nodes[name]

    def missing(self):
        """Return list of property names that are still unset."""
        return [n for n, node in self._nodes.items() if not node.is_set()]

    def conflicts(self):
        """Return list of (name, user_value, derived_value) conflicts."""
        return list(self._conflicts)

    def to_dict(self) -> Dict[str, Any]:
        """Return all set properties as {name: value} dict."""
        return {
            name: node.value
            for name, node in self._nodes.items()
            if node.is_set()
        }

    # ------------------------------------------------------------------
    # Solver  (fixed-point iteration over equation groups)
    # ------------------------------------------------------------------

    def _solve(self):
        """Run fixed-point iteration until no new values are derived."""
        self._conflicts = []
        changed = True
        max_iter = 20
        iteration = 0
        while changed and iteration < max_iter:
            changed = False
            changed |= self._power_group()
            changed |= self._energy_group()
            changed |= self._bandwidth_group()
            changed |= self._compute_group()
            changed |= self._thermal_group()
            changed |= self._timing_group()
            iteration += 1

    def _try_set(self, name: str, value: float) -> bool:
        """
        Attempt to set a derived value. Returns True if anything changed.
        Issues ConflictWarning if the derived value contradicts a user value.
        """
        if value is None or math.isnan(value) or math.isinf(value):
            return False
        node = self._nodes[name]
        if node.source == 'user':
            # Conflict check: derived contradicts explicit user value
            if node.value is not None and abs(node.value - value) > 1e-9 * max(abs(node.value), abs(value), 1e-30):
                self._conflicts.append((name, node.value, value))
                warnings.warn(
                    f"Property '{name}': user set {node.value:.6g} but "
                    f"equations derive {value:.6g}.",
                    ConflictWarning,
                    stacklevel=4,
                )
            return False  # user value wins
        if node.value is None or abs(node.value - value) > 1e-12 * max(abs(value), 1e-30):
            node.value = value
            node.source = 'derived'
            return True
        return False

    def _v(self, name: str) -> Optional[float]:
        """Return value or None (short alias)."""
        return self._nodes[name].value

    def _derivable(self, name: str) -> bool:
        """True if this property can be (re-)derived — i.e. NOT user-set."""
        return self._nodes[name].source != 'user'

    # ------------------------------------------------------------------
    # Equation groups
    # ------------------------------------------------------------------

    def _power_group(self) -> bool:
        """
        P_dynamic = Cdyn * voltage^2 * frequency
        P_static  = I_leak * voltage
        P_total   = P_dynamic + P_static
        """
        changed = False
        Cdyn = self._v('Cdyn')
        V    = self._v('voltage')
        f    = self._v('frequency')
        Il   = self._v('I_leak')
        Pd   = self._v('P_dynamic')
        Ps   = self._v('P_static')
        Pt   = self._v('P_total')

        # P_dynamic = Cdyn * V^2 * f
        if self._derivable('P_dynamic') and Cdyn is not None and V is not None and f is not None:
            changed |= self._try_set('P_dynamic', Cdyn * V * V * f)
            Pd = self._v('P_dynamic')
        elif Cdyn is None and Pd is not None and V is not None and f is not None and V * V * f != 0:
            changed |= self._try_set('Cdyn', Pd / (V * V * f))
        elif V is None and Pd is not None and Cdyn is not None and f is not None and Cdyn * f != 0:
            # V = sqrt(P_dynamic / (Cdyn * f))
            val = Pd / (Cdyn * f)
            if val >= 0:
                changed |= self._try_set('voltage', math.sqrt(val))
                V = self._v('voltage')
        elif f is None and Pd is not None and Cdyn is not None and V is not None and Cdyn * V * V != 0:
            changed |= self._try_set('frequency', Pd / (Cdyn * V * V))
            f = self._v('frequency')

        # P_static = I_leak * V
        if self._derivable('P_static') and Il is not None and V is not None:
            changed |= self._try_set('P_static', Il * V)
            Ps = self._v('P_static')
        elif Il is None and Ps is not None and V is not None and V != 0:
            changed |= self._try_set('I_leak', Ps / V)
        elif V is None and Ps is not None and Il is not None and Il != 0:
            changed |= self._try_set('voltage', Ps / Il)
            V = self._v('voltage')

        # P_total = P_dynamic + P_static
        Pd = self._v('P_dynamic')
        Ps = self._v('P_static')
        Pt = self._v('P_total')
        if self._derivable('P_total') and Pd is not None and Ps is not None:
            changed |= self._try_set('P_total', Pd + Ps)
        elif Pd is None and Pt is not None and Ps is not None:
            changed |= self._try_set('P_dynamic', Pt - Ps)
        elif Ps is None and Pt is not None and Pd is not None:
            changed |= self._try_set('P_static', Pt - Pd)

        return changed

    def _energy_group(self) -> bool:
        """
        energy   = P_total * time
        E_per_op = P_total / throughput   (J/op)
        """
        changed = False
        Pt = self._v('P_total')
        t  = self._v('time')
        E  = self._v('energy')
        tp = self._v('throughput')
        Ep = self._v('E_per_op')

        # energy = P_total * time
        if self._derivable('energy') and Pt is not None and t is not None:
            changed |= self._try_set('energy', Pt * t)
        elif t is None and E is not None and Pt is not None and Pt != 0:
            changed |= self._try_set('time', E / Pt)
        elif Pt is None and E is not None and t is not None and t != 0:
            changed |= self._try_set('P_total', E / t)
            Pt = self._v('P_total')

        # E_per_op = P_total / throughput
        if self._derivable('E_per_op') and Pt is not None and tp is not None and tp != 0:
            changed |= self._try_set('E_per_op', Pt / tp)
        elif tp is None and Pt is not None and Ep is not None and Ep != 0:
            changed |= self._try_set('throughput', Pt / Ep)
        elif Pt is None and Ep is not None and tp is not None:
            changed |= self._try_set('P_total', Ep * tp)

        return changed

    def _bandwidth_group(self) -> bool:
        """
        BW                 = width_bytes * frequency     (bytes/s)
        BW_bytes_per_cycle = BW / frequency              (bytes/cycle)
        latency_s          = transfer_bytes / BW         (transfer latency)

        Note: capacity_bytes (storage size) is NOT part of this group.
        """
        changed = False
        wb = self._v('width_bytes')
        f  = self._v('frequency')
        BW = self._v('BW')
        Bc = self._v('BW_bytes_per_cycle')
        sz = self._v('transfer_bytes')    # one request size, not total capacity
        lt = self._v('latency_s')

        # BW = width_bytes * frequency
        if self._derivable('BW') and wb is not None and f is not None:
            changed |= self._try_set('BW', wb * f)
            BW = self._v('BW')
        elif wb is None and BW is not None and f is not None and f != 0:
            changed |= self._try_set('width_bytes', BW / f)
        elif f is None and BW is not None and wb is not None and wb != 0:
            changed |= self._try_set('frequency', BW / wb)
            f = self._v('frequency')

        # BW_bytes_per_cycle = BW / frequency
        BW = self._v('BW')
        f  = self._v('frequency')
        if self._derivable('BW_bytes_per_cycle') and BW is not None and f is not None and f != 0:
            changed |= self._try_set('BW_bytes_per_cycle', BW / f)
        elif BW is None and Bc is not None and f is not None:
            changed |= self._try_set('BW', Bc * f)
            BW = self._v('BW')

        # latency_s = transfer_bytes / BW
        BW = self._v('BW')
        if self._derivable('latency_s') and sz is not None and BW is not None and BW != 0:
            changed |= self._try_set('latency_s', sz / BW)
        elif sz is None and lt is not None and BW is not None:
            changed |= self._try_set('transfer_bytes', lt * BW)
        elif BW is None and lt is not None and sz is not None and lt != 0:
            changed |= self._try_set('BW', sz / lt)

        return changed

    def _compute_group(self) -> bool:
        """
        throughput           = ops_per_cycle * frequency   (FLOP/s)
        throughput_per_cycle = throughput / frequency       (FLOP/cycle)
        utilization          = actual_ops / peak_ops
        """
        changed = False
        opc = self._v('ops_per_cycle')
        f   = self._v('frequency')
        tp  = self._v('throughput')
        tpc = self._v('throughput_per_cycle')
        aop = self._v('actual_ops')
        pop = self._v('peak_ops')
        ut  = self._v('utilization')

        # throughput = ops_per_cycle * frequency
        if self._derivable('throughput') and opc is not None and f is not None:
            changed |= self._try_set('throughput', opc * f)
            tp = self._v('throughput')
        elif opc is None and tp is not None and f is not None and f != 0:
            changed |= self._try_set('ops_per_cycle', tp / f)
        elif f is None and tp is not None and opc is not None and opc != 0:
            changed |= self._try_set('frequency', tp / opc)
            f = self._v('frequency')

        # throughput_per_cycle = throughput / frequency  (= ops_per_cycle)
        tp = self._v('throughput')
        f  = self._v('frequency')
        if self._derivable('throughput_per_cycle') and tp is not None and f is not None and f != 0:
            changed |= self._try_set('throughput_per_cycle', tp / f)
        elif tp is None and tpc is not None and f is not None:
            changed |= self._try_set('throughput', tpc * f)

        # utilization = actual_ops / peak_ops
        if self._derivable('utilization') and aop is not None and pop is not None and pop != 0:
            changed |= self._try_set('utilization', aop / pop)
        elif aop is None and ut is not None and pop is not None:
            changed |= self._try_set('actual_ops', ut * pop)
        elif pop is None and ut is not None and aop is not None and ut != 0:
            changed |= self._try_set('peak_ops', aop / ut)

        return changed

    def _thermal_group(self) -> bool:
        """
        T_junction = T_ambient + P_total * theta_ja
        """
        changed = False
        Ta  = self._v('T_ambient')
        Pt  = self._v('P_total')
        tja = self._v('theta_ja')
        Tj  = self._v('T_junction')

        if self._derivable('T_junction') and Ta is not None and Pt is not None and tja is not None:
            changed |= self._try_set('T_junction', Ta + Pt * tja)
        elif Ta is None and Tj is not None and Pt is not None and tja is not None:
            changed |= self._try_set('T_ambient', Tj - Pt * tja)
        elif Pt is None and Tj is not None and Ta is not None and tja is not None and tja != 0:
            changed |= self._try_set('P_total', (Tj - Ta) / tja)
        elif tja is None and Tj is not None and Ta is not None and Pt is not None and Pt != 0:
            changed |= self._try_set('theta_ja', (Tj - Ta) / Pt)

        return changed

    def _timing_group(self) -> bool:
        """
        time_s = cycles / frequency
        """
        changed = False
        cy = self._v('cycles')
        f  = self._v('frequency')
        t  = self._v('time')

        if self._derivable('time') and cy is not None and f is not None and f != 0:
            changed |= self._try_set('time', cy / f)
        elif cy is None and t is not None and f is not None:
            changed |= self._try_set('cycles', t * f)
        elif f is None and t is not None and cy is not None and t != 0:
            changed |= self._try_set('frequency', cy / t)

        return changed

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self):
        set_props = {n: node for n, node in self._nodes.items() if node.is_set()}
        lines = [f"PropertySchema ({len(set_props)} set / {len(self._nodes)} total):"]
        for name, node in sorted(set_props.items()):
            src = '*' if node.source == 'user' else ' '
            lines.append(f"  {src} {name:<28} = {node.value:.6g} {node.unit}")
        return '\n'.join(lines)
