import os
import json
import matplotlib.pyplot as plt
import numpy as np

# ---------- CONFIG ----------
SETUP_PATHS = [
    "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations/results/aggregated_vector_stats.json",
    # add other setup JSON paths here to compare
]
OUTPUT_DIR = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations/results/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ----------------------------

def load_aggregated_stats(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data["aggregated_node_stats"], data.get("repetitions", [])

# load all setups
all_setups = {}
for path in SETUP_PATHS:
    setup_name = os.path.basename(os.path.dirname(path))
    node_stats, reps = load_aggregated_stats(path)
    all_setups[setup_name] = node_stats
    print(f"✅ Loaded setup '{setup_name}' ({len(node_stats)} nodes, {len(reps)} repetitions)")

# determine all signals across setups
all_signals = set()
for node_stats in all_setups.values():
    for node_id, signals in node_stats.items():
        all_signals.update(signals.keys())

# ---------- PLOT ----------
for signal in sorted(all_signals):
    plt.figure(figsize=(12,6))
    for setup_name, node_stats in all_setups.items():
        nodes = sorted(node_stats.keys(), key=int)
        means = [node_stats[n].get(signal, {}).get("mean", np.nan) for n in nodes]
        stds = [node_stats[n].get(signal, {}).get("std", 0.0) for n in nodes]
        plt.errorbar(nodes, means, yerr=stds, fmt='o', label=setup_name, capsize=3)

    plt.title(f"Metric: {signal}")
    plt.xlabel("Node ID")
    plt.ylabel(signal)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    out_file = os.path.join(OUTPUT_DIR, f"{signal}.png")
    plt.savefig(out_file)
    plt.close()
    print(f"✅ Plot saved: {out_file}")

print("✅ All metrics plotted.")
