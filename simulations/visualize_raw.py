import os
import json
import pandas as pd
import matplotlib.pyplot as plt

# ---------- CONFIG ----------
FLORA_ROOT = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations"
RESULTS_DIR = "results"
REPETITION_FOLDER = "0"
input_json = os.path.join(FLORA_ROOT, RESULTS_DIR, REPETITION_FOLDER, "vector_stats_parallel.json")
OUTPUT_DIR = os.path.join(FLORA_ROOT, RESULTS_DIR, REPETITION_FOLDER, "plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ----------------------------

print(f"📂 Loading data from {input_json} ...")
with open(input_json, "r") as f:
    data = json.load(f)

node_stats = data.get("node_stats", {})
print(f"✅ Loaded stats for {len(node_stats)} nodes")

# ---------- BUILD DATAFRAME ----------
rows = []
for node_id, signals in node_stats.items():
    for signal, stats in signals.items():
        row = {
            "node": int(node_id),
            "signal": signal,
            "count": stats.get("count", 0),
            "sum": stats.get("sum", 0.0),
            "mean": stats.get("sum", 0.0)/stats.get("count", 1) if stats.get("count", 0) > 0 else 0,
            "min": stats.get("min", 0.0),
            "max": stats.get("max", 0.0)
        }
        rows.append(row)

df = pd.DataFrame(rows)
print(f"✅ Dataframe shape: {df.shape}")

# ---------- PLOT EACH SIGNAL ----------
signals = df['signal'].unique()
for signal in signals:
    subset = df[df['signal'] == signal].sort_values('node')
    plt.figure(figsize=(10, 5))
    plt.bar(subset['node'], subset['mean'], color='skyblue')
    plt.xlabel("Node ID")
    plt.ylabel(f"Average {signal}")
    plt.title(f"Signal: {signal} (per node)")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    filename = os.path.join(OUTPUT_DIR, f"{signal}.png")
    plt.savefig(filename)
    plt.close()
    print(f"✅ Plot saved: {filename}")

print("✅ All signals plotted.")
