# Benders Visualisation Debugging

Visualization tools for analyzing and comparing Benders decomposition solve times with and without micro iterations.

## What it does

`plot_micro_iterations.py` parses a micro-iterations log file and produces one stacked-bar chart (PNG) per subproblem. Each bar represents a master iteration, split into colored segments for each micro iteration (bottom to top: micro iter 1, 2, 3, ...). Baseline solve times (without micro iterations) are overlaid as red dots for comparison.

## Expected input

**Micro iterations directory** — must contain `micro_iterations_proc_0.log` with lines formatted as:

```
master iteration 1 elapsed time : 24933 ms
sub/sub_15.mps ; 1 ; 1 ; 1419819
sub/sub_15.mps ; 1 ; 2 ; 3278616
```

Fields: `subproblem ; master_iter ; micro_iter ; time_in_microseconds`

**Baseline directory** — must contain `sub_i.mps_solve_times.txt` files, one solve time per line in milliseconds.

## Usage

```bash
python3 plot_micro_iterations.py <micro_iterations_dir> <baseline_dir> [-o output.png]
```

Example:

```bash
python3 plot_micro_iterations.py \
    ~/studies/cas_tests_THT400/THT400_15-19_200_micro_it \
    ~/studies/cas_tests_THT400/THT400_15-19_200_base/sub \
    -o results.png
```

This produces one PNG per subproblem: `results_sub_15.png`, `results_sub_16.png`, etc.

## Dependencies

- Python 3.10+
- matplotlib
- numpy
