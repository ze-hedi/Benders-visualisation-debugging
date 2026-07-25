#!/usr/bin/env python3
"""
Compare subproblem solve times between two strategies:
  - cacheprob (cached problems)
  - memoptim (memory optimized)

Produces one interactive grouped bar chart per subproblem, with paired bars
(cacheprob vs memoptim) for each master iteration.

Output is interactive HTML (Plotly).
"""

import argparse
from pathlib import Path

import plotly.graph_objects as go


def load_solutions(directory: str, prefix: str) -> dict[str, list[float]]:
    """
    Load files named <prefix>_i.txt (i = 1, 2, ...) from directory.
    Each file has lines: sub/sub_<k>.mps <time_ms>

    Returns: {sub_name: [time_iter1, time_iter2, ...]}
    """
    dir_path = Path(directory)
    data: dict[str, list[float]] = {}
    i = 1
    while True:
        filepath = dir_path / f"{prefix}_{i}.txt"
        if not filepath.exists():
            break
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                sub_name = parts[0]
                time_ms = float(parts[1])
                if sub_name not in data:
                    data[sub_name] = []
                data[sub_name].append(time_ms)
        i += 1
    return data


def plot_grouped_bars(
    cache_data: dict[str, list[float]],
    memoptim_data: dict[str, list[float]],
    output_dir: str,
):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    figures = []
    for sub_name in sorted(cache_data.keys()):
        cache_times = list(cache_data[sub_name])
        memoptim_times = list(memoptim_data.get(sub_name, []))

        n_iters = max(len(cache_times), len(memoptim_times))
        # Pad shorter list with 0s
        cache_times += [0.0] * (n_iters - len(cache_times))
        memoptim_times += [0.0] * (n_iters - len(memoptim_times))

        x = list(range(1, n_iters + 1))

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x,
            y=cache_times,
            name="cacheprob",
            marker_color="#4C72B0",
            hovertemplate=(
                "Master iter: %{x}<br>"
                "cacheprob: %{y:.2f} ms<extra></extra>"
            ),
        ))
        fig.add_trace(go.Bar(
            x=x,
            y=memoptim_times,
            name="memoptim",
            marker_color="#DD8452",
            hovertemplate=(
                "Master iter: %{x}<br>"
                "memoptim: %{y:.2f} ms<extra></extra>"
            ),
        ))

        short_name = sub_name.replace("sub/", "").replace(".mps", "")
        fig.update_layout(
            barmode="group",
            title=f"Subproblem {short_name} — cacheprob vs memoptim",
            xaxis_title="Master iteration",
            yaxis_title="Time (ms)",
            xaxis=dict(tickmode="linear", dtick=1),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
            template="plotly_white",
            width=1200,
            height=500,
        )

        figures.append(fig)

    # Build a single HTML page with all figures stacked vertically
    divs = []
    for fig in figures:
        divs.append(fig.to_html(full_html=False, include_plotlyjs=False))

    html = (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>\n'
        "</head>\n<body>\n"
        + "\n<hr>\n".join(divs)
        + "\n</body>\n</html>"
    )
    fname = out_path / "benchmark_all.html"
    Path(fname).write_text(html)
    print(f"Saved to {fname}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark cacheprob vs memoptim subproblem solve times"
    )
    parser.add_argument("cache_dir", help="Directory containing cacheprob_sub_solution_i.txt files")
    parser.add_argument("memoptim_dir", help="Directory containing memoptim_sub_solution_i.txt files")
    parser.add_argument("output_dir", help="Directory where output HTML files will be stored")
    args = parser.parse_args()

    cache_data = load_solutions(args.cache_dir, "cacheprob_sub_solution")
    memoptim_data = load_solutions(args.memoptim_dir, "memoptim_sub_solution")

    for sub in sorted(cache_data.keys()):
        print(f"{sub}: {len(cache_data[sub])} iterations (cacheprob)")
    for sub in sorted(memoptim_data.keys()):
        print(f"{sub}: {len(memoptim_data[sub])} iterations (memoptim)")

    plot_grouped_bars(cache_data, memoptim_data, args.output_dir)
