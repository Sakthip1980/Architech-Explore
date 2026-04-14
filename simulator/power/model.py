"""
Activity-based power and thermal model.

PowerBreakdown      — per-block energy split: dynamic, static, total
PowerDomainModel    — compute_energy(block, active_cycles, idle_cycles, ...)
SystemPowerModel    — aggregate across all blocks; thermal check
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List


@dataclass
class PowerBreakdown:
    """Energy breakdown for one block over a simulation run."""
    block_name: str
    dynamic_energy_j: float = 0.0
    static_energy_j:  float = 0.0
    total_energy_j:   float = 0.0
    avg_power_w:      float = 0.0
    peak_power_w:     float = 0.0
    active_cycles:    float = 0.0
    idle_cycles:      float = 0.0
    frequency_hz:     float = 1e9

    @property
    def total_cycles(self) -> float:
        return self.active_cycles + self.idle_cycles

    @property
    def utilization(self) -> float:
        t = self.total_cycles
        return self.active_cycles / t if t > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'block': self.block_name,
            'dynamic_energy_j': self.dynamic_energy_j,
            'static_energy_j':  self.static_energy_j,
            'total_energy_j':   self.total_energy_j,
            'avg_power_w':      self.avg_power_w,
            'peak_power_w':     self.peak_power_w,
            'utilization':      self.utilization,
            'active_cycles':    self.active_cycles,
            'idle_cycles':      self.idle_cycles,
        }


class PowerDomainModel:
    """
    Compute energy for a single hardware block based on activity.

    Model:
      E_dynamic = ops * E_per_op + bytes * energy_per_bit_j
      E_static  = I_leak * V * total_time   (clock-gating: 10% when idle)
      E_total   = E_dynamic + E_static
    """

    # Clock-gating idle power fraction (industry typical: 5-15%)
    IDLE_POWER_FRACTION = 0.10

    def compute_energy(
        self,
        block,
        active_cycles: float,
        idle_cycles: float,
        ops: float,
        bytes_transferred: float,
        frequency_hz: Optional[float] = None,
    ) -> PowerBreakdown:
        """
        Compute energy for one block given its activity profile.

        Parameters
        ----------
        block             : hardware Block with property schema
        active_cycles     : cycles block was doing useful work
        idle_cycles       : cycles block was idle (clock-gated)
        ops               : total FLOPs executed
        bytes_transferred : total bytes read + written
        frequency_hz      : override frequency (if not in block properties)
        """
        # --- Extract hardware parameters
        f    = self._prop(block, 'frequency',  frequency_hz or 1e9)
        Pt   = self._prop(block, 'P_total',    None)
        Pd   = self._prop(block, 'P_dynamic',  None)
        Ps   = self._prop(block, 'P_static',   None)
        Ep   = self._prop(block, 'E_per_op',   None)

        total_cycles = active_cycles + idle_cycles
        total_time_s = total_cycles / f if f > 0 else 0.0
        active_time_s = active_cycles / f if f > 0 else 0.0
        idle_time_s   = idle_cycles / f if f > 0 else 0.0

        # --- Dynamic energy
        if Ep is not None and ops > 0:
            E_dynamic = ops * Ep
        elif Pd is not None:
            E_dynamic = Pd * active_time_s
        elif Pt is not None:
            # Estimate: assume Pd ≈ 80% of P_total
            E_dynamic = Pt * 0.8 * active_time_s
        else:
            E_dynamic = 0.0

        # Add memory traffic energy if energy_per_bit is set
        # (energy_per_bit not in schema yet; use 1 pJ/bit heuristic)
        mem_energy_per_bit = 1e-12  # 1 pJ/bit for on-chip, ~10 pJ/bit off-chip
        E_memory = bytes_transferred * 8 * mem_energy_per_bit
        E_dynamic += E_memory

        # --- Static (leakage) energy
        if Ps is not None:
            E_static_active = Ps * active_time_s
            E_static_idle   = Ps * self.IDLE_POWER_FRACTION * idle_time_s
        elif Pt is not None:
            Ps_est = Pt * 0.2  # estimate: 20% static
            E_static_active = Ps_est * active_time_s
            E_static_idle   = Ps_est * self.IDLE_POWER_FRACTION * idle_time_s
        else:
            E_static_active = E_static_idle = 0.0

        E_static = E_static_active + E_static_idle
        E_total  = E_dynamic + E_static
        avg_power = E_total / total_time_s if total_time_s > 0 else 0.0
        peak_power = Pt or (Pd or 0) + (Ps or 0) or avg_power

        return PowerBreakdown(
            block_name=getattr(block, 'name', 'unknown'),
            dynamic_energy_j=E_dynamic,
            static_energy_j=E_static,
            total_energy_j=E_total,
            avg_power_w=avg_power,
            peak_power_w=peak_power,
            active_cycles=active_cycles,
            idle_cycles=idle_cycles,
            frequency_hz=f,
        )

    @staticmethod
    def _prop(block, name: str, default):
        if hasattr(block, 'get_property'):
            val = block.get_property(name)
            if val is not None:
                return val
        return default

    def thermal_check(
        self,
        breakdown: PowerBreakdown,
        theta_ja: float = 10.0,   # C/W junction-to-ambient thermal resistance
        T_ambient: float = 25.0,  # ambient temperature in Celsius
        T_budget: float = 100.0,  # max allowed junction temperature
    ) -> Dict[str, Any]:
        """
        Compute junction temperature from power breakdown.

        T_junction = T_ambient + P_total * theta_ja
        """
        T_j = T_ambient + breakdown.avg_power_w * theta_ja
        return {
            'T_junction_c': T_j,
            'T_ambient_c': T_ambient,
            'theta_ja': theta_ja,
            'within_budget': T_j <= T_budget,
            'margin_c': T_budget - T_j,
        }


class SystemPowerModel:
    """
    Aggregate power model across all blocks in a simulation.

    Usage
    -----
    spm = SystemPowerModel()
    for name, blk in blocks.items():
        spm.add_block(blk, active_cycles[name], idle_cycles[name], ...)
    report = spm.aggregate()
    """

    def __init__(self):
        self._model = PowerDomainModel()
        self._breakdowns: List[PowerBreakdown] = []

    def add_block(
        self,
        block,
        active_cycles: float,
        idle_cycles: float,
        ops: float = 0.0,
        bytes_transferred: float = 0.0,
        frequency_hz: Optional[float] = None,
    ) -> PowerBreakdown:
        bd = self._model.compute_energy(
            block, active_cycles, idle_cycles, ops, bytes_transferred, frequency_hz
        )
        self._breakdowns.append(bd)
        return bd

    def aggregate(self) -> Dict[str, Any]:
        """Return system-total and per-block breakdown."""
        total_dynamic = sum(b.dynamic_energy_j for b in self._breakdowns)
        total_static  = sum(b.static_energy_j  for b in self._breakdowns)
        total_energy  = sum(b.total_energy_j   for b in self._breakdowns)
        total_cycles  = max((b.total_cycles for b in self._breakdowns), default=0)
        total_time_s  = max(
            (b.total_cycles / b.frequency_hz for b in self._breakdowns if b.frequency_hz > 0),
            default=0.0,
        )
        avg_power = total_energy / total_time_s if total_time_s > 0 else 0.0

        return {
            'system': {
                'total_dynamic_energy_j': total_dynamic,
                'total_static_energy_j':  total_static,
                'total_energy_j':         total_energy,
                'avg_power_w':            avg_power,
                'total_time_s':           total_time_s,
            },
            'per_block': [b.to_dict() for b in self._breakdowns],
        }
