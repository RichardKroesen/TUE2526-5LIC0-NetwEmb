import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------- CONFIG ----------
FLORA_ROOT = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations"
RESULTS_DIR = "results"
AGG_JSON = os.path.join(FLORA_ROOT, RESULTS_DIR, "aggregated_vector_stats.json")  # your aggregated file
OUTPUT_DIR = os.path.join(FLORA_ROOT, RESULTS_DIR, "plots_classic_aggregated")
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ----------------------------

# ---------- SIGNAL TO CLASSIC METRIC MAPPING ----------
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

# ---------- LOAD AGGREGATED JSON ----------
print(f"📂 Loading aggregated stats from {AGG_JSON} ...")
with open(AGG_JSON, "r") as f:
    data = json.load(f)

node_stats = data.get("aggregated_node_stats", {})
repetitions = data.get("repetitions", [])
print(f"✅ Loaded stats for {len(node_stats)} nodes across {len(repetitions)} repetitions")

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
            "mean": stats.get("mean", 0.0),
            "std": stats.get("std", 0.0)
        })

df = pd.DataFrame(rows)
print(f"✅ Dataframe shape: {df.shape}")

# ---------- PLOT PER METRIC ----------
metrics_to_plot = df['metric'].unique()
for metric in metrics_to_plot:
    subset = df[df['metric'] == metric].sort_values('node')
    
    plt.figure(figsize=(12,5))
    plt.bar(subset['node'], subset['mean'], yerr=subset['std'], color='skyblue', capsize=3)
    plt.xlabel("Node ID")
    plt.ylabel(f"{metric} (mean ± std across repetitions)")
    plt.title(f"{metric} per node (aggregated)")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    filename = os.path.join(OUTPUT_DIR, f"{metric}_aggregated.png")
    plt.savefig(filename)
    plt.close()
    print(f"✅ Plot saved: {filename}")

# ---------- GLOBAL SUMMARY ----------
plt.figure(figsize=(10,6))
summary = df.groupby('metric')['mean'].mean()
summary.plot(kind='bar', color='coral')
plt.ylabel("Average across all nodes & repetitions")
plt.title("Global Metric Summary (aggregated)")
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "global_summary_aggregated.png"))
plt.close()
print("✅ Global summary plot saved.")

print("✅ All aggregated classic metrics plotted.")
