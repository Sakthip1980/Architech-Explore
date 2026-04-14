"""
Visualization functions for simulation results.

All functions return a matplotlib Figure (no implicit plt.show()).
Use matplotlib's Agg backend for headless environments:
  import matplotlib
  matplotlib.use('Agg')

Functions:
  plot_roofline(results, hw_block)          — roofline with op scatter
  plot_utilization_heatmap(result)          — block × time utilization
  plot_stall_waterfall(result)              — stacked active/stall/idle bars
  plot_pareto_front(results, x_m, y_m)     — Pareto scatter
  plot_sensitivity(results, param, metric) — line plot for sensitivity sweep
"""

from typing import List, Optional, Any


def _get_matplotlib():
    """Import matplotlib and switch to Agg backend if no display."""
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        return matplotlib, plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for visualization. "
            "Install with: pip install matplotlib"
        )


def plot_roofline(
    results,
    hw_block,
    title: str = 'Roofline Model',
    dtype_bytes: int = 2,
):
    """
    Roofline plot.

    X-axis: arithmetic intensity (FLOP/byte)
    Y-axis: throughput (FLOP/cycle)
    Ridge point line, and one scatter point per op colored by bottleneck.

    Parameters
    ----------
    results  : AnalyticalResult or list of OpResult
    hw_block : hardware Block with get_property()
    """
    matplotlib, plt = _get_matplotlib()
    from ..engine.roofline import roofline as rf_fn

    # Extract per-op data
    if hasattr(results, 'per_op'):
        op_results = results.per_op
    else:
        op_results = list(results)

    fig, ax = plt.subplots(figsize=(9, 6))

    # --- Roofline boundaries
    tp = hw_block.get_property('throughput_per_cycle') or 1.0
    bw = hw_block.get_property('BW_bytes_per_cycle') or 1.0
    ridge = tp / bw  # FLOP/byte at balance

    import numpy as np
    ai_range = np.logspace(-2, 4, 300)
    roof = np.minimum(tp, bw * ai_range)
    ax.plot(ai_range, roof, 'k-', linewidth=2.5, label='Roofline')
    ax.axvline(ridge, color='gray', linestyle='--', linewidth=1, label=f'Ridge ({ridge:.2f} FLOP/B)')

    # --- Op scatter
    color_map = {'compute': '#e74c3c', 'memory': '#3498db', 'balanced': '#2ecc71'}
    for r in op_results:
        rf = r.roofline
        color = color_map.get(rf.bottleneck, '#95a5a6')
        ax.scatter(rf.arithmetic_intensity, rf.achieved_throughput,
                   color=color, s=60, zorder=5, alpha=0.8)

    # Legend
    from matplotlib.patches import Patch
    legend_items = [
        Patch(color='#e74c3c', label='Compute-bound'),
        Patch(color='#3498db', label='Memory-bound'),
        Patch(color='#2ecc71', label='Balanced'),
    ]
    ax.legend(handles=legend_items + ax.get_legend_handles_labels()[0][:2],
              loc='upper left')

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Arithmetic Intensity (FLOP / byte)', fontsize=12)
    ax.set_ylabel('Throughput (FLOP / cycle)', fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.grid(True, which='both', alpha=0.3)
    fig.tight_layout()
    return fig


def plot_utilization_heatmap(result, title: str = 'Block Utilization'):
    """
    Heatmap: blocks (rows) × time buckets (columns), color = utilization.
    Uses per-op start/end cycles from result.per_op.
    """
    matplotlib, plt = _get_matplotlib()
    import numpy as np

    if not result.per_op:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No op data', ha='center', va='center')
        return fig

    # Collect unique blocks and time range
    blocks = sorted({r.block_name for r in result.per_op})
    if not blocks:
        blocks = ['default']

    total_cycles = result.total_cycles or 1.0
    n_buckets = min(50, len(result.per_op))
    bucket_size = total_cycles / n_buckets

    # Build utilization matrix: blocks × time_buckets
    matrix = np.zeros((len(blocks), n_buckets))
    block_idx = {b: i for i, b in enumerate(blocks)}

    for r in result.per_op:
        bidx = block_idx.get(r.block_name, 0)
        start_b = int(r.start_cycle / bucket_size)
        end_b   = min(int(r.end_cycle / bucket_size) + 1, n_buckets)
        for b in range(start_b, end_b):
            matrix[bidx, b] = min(matrix[bidx, b] + 1, 1.0)

    # Normalise rows to [0, 1]
    row_max = matrix.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1
    matrix /= row_max

    fig, ax = plt.subplots(figsize=(12, max(3, len(blocks))))
    im = ax.imshow(matrix, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1,
                   interpolation='nearest')
    plt.colorbar(im, ax=ax, label='Utilization')
    ax.set_yticks(range(len(blocks)))
    ax.set_yticklabels(blocks)
    ax.set_xlabel('Time bucket')
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_stall_waterfall(result, title: str = 'Active / Idle Breakdown'):
    """
    Stacked horizontal bar chart: per-block active + idle cycles.
    """
    matplotlib, plt = _get_matplotlib()
    import numpy as np

    # Try to get block stats from power_breakdown
    block_data = {}
    if result.power_breakdown:
        for name, info in result.power_breakdown.items():
            block_data[name] = {
                'active': info.get('active_cycles', 0),
                'idle':   info.get('idle_cycles', 0),
            }

    # Fallback: derive from per_op
    if not block_data and result.per_op:
        for r in result.per_op:
            if r.block_name not in block_data:
                block_data[r.block_name] = {'active': 0.0, 'idle': 0.0}
            block_data[r.block_name]['active'] += r.latency_cycles

        for name, d in block_data.items():
            d['idle'] = max(0.0, result.total_cycles - d['active'])

    if not block_data:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No block data', ha='center', va='center')
        return fig

    names   = list(block_data.keys())
    active  = np.array([block_data[n]['active'] for n in names])
    idle    = np.array([block_data[n]['idle']   for n in names])

    fig, ax = plt.subplots(figsize=(9, max(3, len(names) * 0.5)))
    y = np.arange(len(names))
    ax.barh(y, active, label='Active', color='#2ecc71', height=0.5)
    ax.barh(y, idle, left=active, label='Idle', color='#bdc3c7', height=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel('Cycles')
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_pareto_front(
    results: list,
    x_metric: str = 'total_cycles',
    y_metric: str = 'total_energy_j',
    title: str = 'Pareto Front',
):
    """
    Scatter plot of x_metric vs y_metric for all results.
    Pareto-optimal points highlighted.
    """
    matplotlib, plt = _get_matplotlib()
    from .result import SensitivitySweep

    def _v(r, m):
        if hasattr(r, m):
            return getattr(r, m)
        return r.metadata.get(m, float('nan'))

    pareto = SensitivitySweep.pareto_front(results, x_metric, y_metric)
    pareto_set = set(id(r) for r in pareto)

    xs = [_v(r, x_metric) for r in results]
    ys = [_v(r, y_metric) for r in results]
    colors = ['#e74c3c' if id(r) in pareto_set else '#95a5a6' for r in results]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(xs, ys, c=colors, s=60, zorder=5, alpha=0.8)

    # Connect Pareto front
    if pareto:
        px = [_v(r, x_metric) for r in pareto]
        py = [_v(r, y_metric) for r in pareto]
        ax.plot(px, py, 'r--', linewidth=1.5, alpha=0.7)

    ax.set_xlabel(x_metric, fontsize=12)
    ax.set_ylabel(y_metric, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.grid(True, alpha=0.3)
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color='#e74c3c', label='Pareto-optimal'),
        Patch(color='#95a5a6', label='Dominated'),
    ])
    fig.tight_layout()
    return fig


def plot_sensitivity(
    results: list,
    vary_param: str,
    metric: str = 'total_cycles',
    title: str = '',
    log_x: bool = False,
):
    """
    Line plot: x = vary_param values, y = metric values.
    """
    matplotlib, plt = _get_matplotlib()

    def _v(r, m):
        if hasattr(r, m):
            return getattr(r, m)
        return r.metadata.get(m, float('nan'))

    xs = [r.metadata.get(vary_param, float('nan')) for r in results]
    ys = [_v(r, metric) for r in results]

    # Sort by x
    pairs = sorted(zip(xs, ys))
    xs_s, ys_s = zip(*pairs) if pairs else ([], [])

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs_s, ys_s, 'o-', color='#3498db', linewidth=2)
    if log_x:
        ax.set_xscale('log')
    ax.set_xlabel(vary_param, fontsize=12)
    ax.set_ylabel(metric, fontsize=12)
    ax.set_title(title or f'{metric} vs {vary_param}', fontsize=13)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
