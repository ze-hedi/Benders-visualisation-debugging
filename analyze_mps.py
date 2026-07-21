#!/usr/bin/env python3
"""
Analyze MPS files: extract and summarize rows, columns, and structure.
"""

import sys
from pathlib import Path


def parse_mps(filepath: str) -> dict:
    """Parse an MPS file and return counts and row details."""
    rows = []  # list of (type, name)
    n_columns = 0
    n_rhs = 0
    n_bounds = 0
    section = None
    seen_cols = set()

    with open(filepath) as f:
        for line in f:
            stripped = line.rstrip()

            # Section headers start at column 0 with uppercase
            if stripped and stripped[0] != ' ':
                section = stripped.split()[0]
                continue

            if section == "ROWS":
                parts = stripped.split()
                if len(parts) >= 2:
                    rows.append((parts[0], parts[1]))

            elif section == "COLUMNS":
                parts = stripped.split()
                if parts:
                    seen_cols.add(parts[0])

            elif section == "BOUNDS":
                n_bounds += 1

    n_columns = len(seen_cols)

    # Count rows by type
    type_counts = {}
    for rtype, _ in rows:
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

    return {
        "file": Path(filepath).name,
        "total_rows": len(rows),
        "row_types": type_counts,
        "total_columns": n_columns,
        "total_bounds": n_bounds,
        "rows": rows,
    }


def print_summary(info: dict):
    print(f"=== {info['file']} ===")
    print(f"  Rows:    {info['total_rows']}")
    for rtype, count in sorted(info['row_types'].items()):
        label = {"N": "free (obj)", "L": "<=", "G": ">=", "E": "="}.get(rtype, rtype)
        print(f"    {rtype} ({label}): {count}")
    print(f"  Columns: {info['total_columns']}")
    print(f"  Bounds:  {info['total_bounds']}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.mps> [file2.mps ...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        info = parse_mps(path)
        print_summary(info)
