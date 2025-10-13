import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------- CONFIG ----------
FLORA_ROOT = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations"
RESULTS_DIR = "results"
REPETITION_FOLDER = "0"
input_json = os.path.join(FLORA_ROOT, RESULTS_DIR, REPETITION_FOLDER, "vector_stats_parallel.json")
output_dir = os.path.join(FLORA_ROOT, RESULTS_DIR, REPETITION_FOLDER, "plots_classic")
os.makedirs(output_dir, exist_ok=True)
# ----------------------------

print(f"📂 Loading data from {input_json} ...")
with open(input_json, "r") as f:
    data = json.load(f)

node_stats = data.get("node_stats", {})
print(f"✅ Loaded stats for {len(node_stats)} nodes")

# ---------- MAP RAW SIGNALS TO CLASSIC METRICS ----------
signal_mapping = {
    "queueLength:vector": "queue_length",
    "queueBitLength:vector": "queue_bits",
    "powerConsumption:vector": "energy",
    "residualEnergyCapacity:vector": "residual_energy",
    "incomingDataRate:vector": "rx_rate",
    "outgoingDataRate:vector": "tx_rate",
    "incomingPacketLengths:vector": "rx_packets",
    "outgoingPacketLengths:vector": "tx_packets",
    "temperature:vector": "temperature",
    "humidity:vector": "humidity",
    "no2:vector": "no2",
    "queueingTime:vector": "queue_time",
    "transmissionState:vector": "tx_state",
    "receptionState:vector": "rx_state",
}

# ---------- BUILD DATAFRAME ----------
rows = []
for node_id, signals in node_stats.items():
    for signal, stats in signals.items():
        metric = signal_mapping.get(signal)
        if not metric:
            continue
        rows.append({
            "node": int(node_id),
            "metric": metric,
            "count": stats.get("count", 0),
            "sum": stats.get("sum", 0.0),
            "mean": stats.get("sum", 0.0)/stats.get("count", 1) if stats.get("count", 0) > 0 else 0,
            "min": stats.get("min", 0.0),
            "max": stats.get("max", 0.0)
        })

df = pd.DataFrame(rows)
print(f"✅ Dataframe shape: {df.shape}")

# ---------- PLOT TOTALS / MEANS PER NODE ----------
metrics_to_plot = df['metric'].unique()
for metric in metrics_to_plot:
    subset = df[df['metric'] == metric].sort_values('node')
    
    plt.figure(figsize=(12, 5))
    plt.bar(subset['node'], subset['mean'], color='skyblue')
    plt.xlabel("Node ID")
    plt.ylabel(f"{metric} (mean per node)")
    plt.title(f"{metric} per node")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    filename = os.path.join(output_dir, f"{metric}.png")
    plt.savefig(filename)
    plt.close()
    print(f"✅ Plot saved: {filename}")

# ---------- OPTIONAL: Global summary plots ----------
plt.figure(figsize=(10,6))
summary = df.groupby('metric')['mean'].mean()
summary.plot(kind='bar', color='coral')
plt.ylabel("Average across all nodes")
plt.title("Global Metric Summary")
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "global_summary.png"))
plt.close()
print("✅ Global summary plot saved.")

print("✅ All classic metrics plotted.")
