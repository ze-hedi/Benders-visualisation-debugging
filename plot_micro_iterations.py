#!/usr/bin/env python3
"""
Parse a Benders decomposition micro-iterations log and produce
one stacked-bar histogram per subproblem.

Each bar represents one master iteration. The bar is split into
colored segments — one per micro iteration — proportional to the
solve time of that micro iteration.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def parse_log(filepath: str) -> dict[str, list[list[float]]]:
    """
    Returns:
        data[sub_name] = list of length num_master_iters,
        where each element is a list of micro-iteration times (in seconds).
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
            # micro_iter = int(parts[2].strip())  # not needed, order is implicit
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
    """Load baseline solve times (no micro iterations) from sub_i.mps_solve_times.txt.
    Times in the files are in milliseconds, converted to seconds.
    Returns: {sub_name: [time_s per master iter]}
    """
    base_path = Path(base_dir)
    result = {}
    for txt_file in sorted(base_path.glob("sub_*.mps_solve_times.txt")):
        # Extract sub name to match the key format from parse_log: "sub/sub_15.mps"
        mps_name = txt_file.name.replace("_solve_times.txt", "")  # "sub_15.mps"
        sub_key = f"sub/{mps_name}"
        times = []
        with open(txt_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    times.append(float(line))  # already in ms
        result[sub_key] = times
    return result


def plot_stacked_bars(data: dict[str, list[list[float]]], output_path: str | None = None,
                      base_times: dict[str, list[float]] | None = None):
    sub_names = sorted(data.keys())
    n_subs = len(sub_names)

    # Find the max number of micro iterations across all subs and all master iters
    max_micros = max(
        len(times) for sub_data in data.values() for times in sub_data
    )

    # Color map for micro iterations
    colors = plt.cm.Set2(np.linspace(0, 1, max(max_micros, 3)))

    for sub_name in sub_names:
        fig, ax = plt.subplots(figsize=(14, 5))
        n_iters = len(data[sub_name])
        x = np.arange(1, n_iters + 1)

        # Build stacked bars bottom-up
        bottoms = np.zeros(n_iters)
        for micro_idx in range(max_micros):
            heights = []
            for master_idx in range(n_iters):
                times = data[sub_name][master_idx]
                if micro_idx < len(times):
                    heights.append(times[micro_idx])
                else:
                    heights.append(0.0)
            heights = np.array(heights)
            ax.bar(
                x, heights, bottom=bottoms,
                color=colors[micro_idx],
                edgecolor="white", linewidth=0.5,
            )
            bottoms += heights

        short_name = sub_name.replace("sub/", "").replace(".mps", "")
        ax.set_ylabel("Time (ms)")
        ax.set_xlabel("Master iteration")
        ax.set_title(f"Subproblem {short_name} — solve time per master iteration")
        ax.set_xticks(x)

        # Overlay baseline solve times as points at the horizontal middle of each bar
        if base_times and sub_name in base_times:
            bt = base_times[sub_name][:n_iters]
            ax.scatter(x[:len(bt)], bt, color="red", zorder=5, s=30,
                       label="No micro-iterations")
            ax.legend(loc="upper right", fontsize=8)

        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()

        if output_path:
            out = Path(output_path)
            fname = out.parent / f"{out.stem}_{short_name}{out.suffix}"
            fig.savefig(fname, dpi=150, bbox_inches="tight")
            print(f"Saved to {fname}")
        else:
            plt.show()
        plt.close(fig)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Plot Benders micro-iterations breakdown")
    parser.add_argument("micro_dir", help="Directory containing micro_iterations_proc_0.log")
    parser.add_argument("base_dir", help="Directory containing sub_i.mps_solve_times.txt files")
    parser.add_argument("-o", "--output", default="micro_iterations.png",
                        help="Output filename pattern (default: micro_iterations.png)")
    args = parser.parse_args()

    log_file = str(Path(args.micro_dir) / "micro_iterations_proc_0.log")
    data = parse_log(log_file)

    for sub, iters in data.items():
        micro_counts = [len(m) for m in iters]
        print(f"{sub}: {len(iters)} master iters, micro iters per master: {micro_counts}")

    base_times = load_base_solve_times(args.base_dir)

    plot_stacked_bars(data, output_path=args.output, base_times=base_times)
