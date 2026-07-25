#!/usr/bin/env python3
"""
Parse a Benders decomposition micro-iterations log and produce
one interactive stacked-bar chart per subproblem.

Each bar represents one master iteration. The bar is split into
colored segments — one per micro iteration — proportional to the
solve time of that micro iteration.

Output is interactive HTML (Plotly).
"""

from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px


def parse_log(filepath: str) -> dict[str, list[list[float]]]:
    """
    Returns:
        data[sub_name] = list of length num_master_iters,
        where each element is a list of micro-iteration times (in ms).
    """
    # Intermediate: {sub_name: {master_iter: [times]}}
    raw: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("warm_start"):
                continue
            if line.startswith("master iteration"):
                continue

            # Format: sub/sub_15.mps ; 1 ; 1 ; 1419819
            # Some lines have spaces inside the number: "1 418 564"
            parts = line.split(";")
            if len(parts) < 4:
                continue

            sub_name = parts[0].strip()
            master_iter = int(parts[1].strip())
            # Time field may contain spaces (e.g., "1 418 564"), strip them
            time_str = parts[3].strip().replace(" ", "")
            time_us = float(time_str)
            time_ms = time_us / 1e3  # convert to milliseconds

            raw[sub_name][master_iter].append(time_ms)

    # Convert to ordered list-of-lists
    data: dict[str, list[list[float]]] = {}
    for sub_name in sorted(raw.keys()):
        iters_dict = raw[sub_name]
        max_iter = max(iters_dict.keys())
        data[sub_name] = [iters_dict[i] for i in range(1, max_iter + 1)]

    return data


def load_base_solve_times(base_dir: str) -> dict[str, list[float]]:
    """Load baseline solve times (no micro iterations) from sub_<i>.txt.
    Returns: {sub_name: [time_ms per master iter]}
    """
    base_path = Path(base_dir)
    result = {}
    for txt_file in sorted(base_path.glob("sub_*.txt")):
        base_name = txt_file.stem  # "sub_15"
        sub_key = f"sub/{base_name}.mps"
        times = []
        with open(txt_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    times.append(float(line))  # already in ms
        result[sub_key] = times
    return result


def load_added_families(families_dir: str) -> dict[str, list[list[int]]]:
    """Load the number of added families per micro iteration from files.

    Files are named: micro_iter_<i>_master_<j>_sub_<k>.txt
    where i = micro iteration, j = master iteration, k = subproblem number.
    Each file contains one family name per line.

    Returns: {sub_name: list of length num_master_iters,
              where each element is a list of family counts per micro iteration}
    """
    families_path = Path(families_dir)
    raw: dict[str, dict[int, dict[int, int]]] = defaultdict(lambda: defaultdict(dict))

    for txt_file in sorted(families_path.glob("micro_iter_*_master_*_sub_*.txt")):
        stem = txt_file.stem  # micro_iter_1_master_2_sub_15
        parts = stem.split("_")
        # parts: ['micro', 'iter', '<i>', 'master', '<j>', 'sub', '<k>']
        micro_iter = int(parts[2])
        master_iter = int(parts[4])
        sub_number = parts[6]
        sub_key = f"sub/sub_{sub_number}.mps"

        with open(txt_file) as f:
            n_lines = sum(1 for line in f if line.strip())
        raw[sub_key][master_iter][micro_iter] = n_lines

    result: dict[str, list[list[int]]] = {}
    for sub_key in sorted(raw.keys()):
        iters_dict = raw[sub_key]
        max_master = max(iters_dict.keys())
        master_list = []
        for m in range(1, max_master + 1):
            if m in iters_dict:
                micro_dict = iters_dict[m]
                max_micro = max(micro_dict.keys())
                micro_list = [micro_dict.get(mi, 0) for mi in range(1, max_micro + 1)]
            else:
                micro_list = []
            master_list.append(micro_list)
        result[sub_key] = master_list

    return result


def plot_stacked_bars(data: dict[str, list[list[float]]], output_path: str | None = None,
                      base_times: dict[str, list[float]] | None = None,
                      added_families: dict[str, list[list[int]]] | None = None):
    sub_names = sorted(data.keys())

    # Find the max number of micro iterations across all subs and all master iters
    max_micros = max(
        len(times) for sub_data in data.values() for times in sub_data
    )

    colors = px.colors.qualitative.Set2
    figures = []

    for sub_name in sub_names:
        fig = go.Figure()
        n_iters = len(data[sub_name])
        x = list(range(1, n_iters + 1))

        # Build stacked bars bottom-up
        for micro_idx in range(max_micros):
            heights = []
            custom_data = []
            for master_idx in range(n_iters):
                times = data[sub_name][master_idx]
                if micro_idx < len(times):
                    heights.append(times[micro_idx])
                else:
                    heights.append(0.0)

                # Get added families count for this micro/master/sub
                n_fam = 0
                if added_families and sub_name in added_families:
                    fam_data = added_families[sub_name]
                    if master_idx < len(fam_data) and micro_idx < len(fam_data[master_idx]):
                        n_fam = fam_data[master_idx][micro_idx]
                custom_data.append(n_fam)

            has_families = added_families and sub_name in added_families
            hover = (
                "Master iter: %{x}<br>"
                f"Micro iter: {micro_idx + 1}<br>"
                "Time: %{y:.2f} ms<br>"
                "n_added_families: %{customdata}<extra></extra>"
            ) if has_families else (
                "Master iter: %{x}<br>"
                f"Micro iter: {micro_idx + 1}<br>"
                "Time: %{y:.2f} ms<extra></extra>"
            )

            fig.add_trace(go.Bar(
                x=x,
                y=heights,
                name=f"Micro iter {micro_idx + 1}",
                marker_color=colors[micro_idx % len(colors)],
                customdata=custom_data if has_families else None,
                hovertemplate=hover,
            ))

        # Overlay baseline solve times as scatter points
        if base_times and sub_name in base_times:
            bt = base_times[sub_name][:n_iters]
            fig.add_trace(go.Scatter(
                x=x[:len(bt)],
                y=bt,
                mode="markers",
                name="No micro-iterations",
                marker=dict(color="red", size=8),
                hovertemplate=(
                    "Master iter: %{x}<br>"
                    "Baseline: %{y:.2f} ms<extra></extra>"
                ),
            ))

        short_name = sub_name.replace("sub/", "").replace(".mps", "")
        fig.update_layout(
            barmode="stack",
            title=f"Subproblem {short_name} — solve time per master iteration",
            xaxis_title="Master iteration",
            yaxis_title="Time (ms)",
            xaxis=dict(tickmode="linear", dtick=1),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
            legend=dict(x=1.02, y=1, xanchor="left"),
            template="plotly_white",
            width=1200,
            height=500,
        )

        figures.append(fig)

    if output_path:
        # Build a single HTML page with all figures stacked vertically
        divs = []
        for i, fig in enumerate(figures):
            # Include plotly.js only in the first div
            divs.append(fig.to_html(full_html=False, include_plotlyjs=(i == 0)))

        html = (
            "<!DOCTYPE html>\n<html>\n<head></head>\n<body>\n"
            + "\n<hr>\n".join(divs)
            + "\n</body>\n</html>"
        )
        Path(output_path).write_text(html)
        print(f"Saved to {output_path}")
    else:
        for fig in figures:
            fig.show()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Plot Benders micro-iterations breakdown")
    parser.add_argument("--micro-dir", required=True, help="Directory containing micro_iterations_proc_0.log")
    parser.add_argument("--base-dir", help="Directory containing sub_<i>.txt files")
    parser.add_argument("--families-dir", help="Directory containing micro_iter_<i>_master_<j>_sub_<k>.txt files")
    parser.add_argument("--output-dir", required=True, help="Directory where output HTML files will be stored")
    args = parser.parse_args()

    log_file = str(Path(args.micro_dir) / "micro_iterations_proc_0.log")
    data = parse_log(log_file)

    for sub, iters in data.items():
        micro_counts = [len(m) for m in iters]
        print(f"{sub}: {len(iters)} master iters, micro iters per master: {micro_counts}")

    base_times = load_base_solve_times(args.base_dir) if args.base_dir else None
    families = load_added_families(args.families_dir) if args.families_dir else None

    print(f"Log sub keys: {sorted(data.keys())}")
    if base_times:
        print(f"Base sub keys: {sorted(base_times.keys())}")
    if families:
        print(f"Families sub keys: {sorted(families.keys())}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(out_dir / "micro_iterations_all.html")

    plot_stacked_bars(data, output_path=output_path, base_times=base_times, added_families=families)
