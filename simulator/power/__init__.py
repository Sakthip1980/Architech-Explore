"""
simulator.power — Activity-based power and thermal model

Public API
----------
PowerBreakdown     - per-block energy: dynamic, static, total, utilization
PowerDomainModel   - compute_energy(block, active_cycles, idle_cycles, ops, bytes)
                     thermal_check(breakdown, theta_ja, T_ambient, T_budget)
SystemPowerModel   - add_block() + aggregate() for multi-block systems
"""

from .model import PowerBreakdown, PowerDomainModel, SystemPowerModel

__all__ = ['PowerBreakdown', 'PowerDomainModel', 'SystemPowerModel']
