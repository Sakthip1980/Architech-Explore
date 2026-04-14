"""
simulator.results — Simulation results, sensitivity sweep, and visualization

Public API
----------
BlockStats         - per-block active/stall/idle cycles, bytes_transferred, utilization
SimResult          - unified result wrapper; from_analytical() class method
SensitivitySweep   - vary(property, values) -> List[SimResult]
                     pareto_front(results, x_metric, y_metric) -> List[SimResult]

Visualization (all return matplotlib.Figure):
  plot_roofline(result, hw_block)
  plot_utilization_heatmap(result)
  plot_stall_waterfall(result)
  plot_pareto_front(results, x_metric, y_metric)
  plot_sensitivity(results, vary_param, metric)
"""

from .result import BlockStats, SimResult, SensitivitySweep
from .viz import (
    plot_roofline,
    plot_utilization_heatmap,
    plot_stall_waterfall,
    plot_pareto_front,
    plot_sensitivity,
)

__all__ = [
    'BlockStats', 'SimResult', 'SensitivitySweep',
    'plot_roofline', 'plot_utilization_heatmap', 'plot_stall_waterfall',
    'plot_pareto_front', 'plot_sensitivity',
]
