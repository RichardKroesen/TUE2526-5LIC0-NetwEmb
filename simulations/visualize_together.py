import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------- CONFIG ----------
FLORA_ROOT = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb/simulations"
RESULTS_DIR = "results"
OUTPUT_DIR = os.path.join(FLORA_ROOT, RESULTS_DIR, "plots_classic_setups")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# ---------- FIND ALL SETUP JSON FILES ----------
setup_folders = [
    f for f in os.listdir(os.path.join(FLORA_ROOT, RESULTS_DIR))
    if os.path.isdir(os.path.join(FLORA_ROOT, RESULTS_DIR, f))
]

setup_data = {}

for setup in setup_folders:
    json_path = os.path.join(FLORA_ROOT, RESULTS_DIR, setup, "aggregated_vector_stats.json")
    if not os.path.exists(json_path):
        continue

    with open(json_path, "r") as f:
        data = json.load(f)
    node_stats = data.get("aggregated_node_stats", {})

    # Convert to dataframe
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
    setup_data[setup] = df
    print(f"✅ Loaded setup '{setup}' with {len(df)} metric entries")

# ---------- PLOT PER METRIC ACROSS SETUPS ----------
all_metrics = set()
for df in setup_data.values():
    all_metrics.update(df['metric'].unique())

for metric in sorted(all_metrics):
    plt.figure(figsize=(12,6))
    
    for setup_name, df in setup_data.items():
        subset = df[df['metric'] == metric].sort_values('node')
        if subset.empty:
            continue
        nodes = subset['node']
        means = subset['mean']
        stds = subset['std']
        plt.errorbar(nodes, means, yerr=stds, fmt='o-', capsize=3, label=setup_name)
    
    plt.xlabel("Node ID")
    plt.ylabel(f"{metric} (mean ± std)")
    plt.title(f"{metric} across setups")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    filename = os.path.join(OUTPUT_DIR, f"{metric}_setups.png")
    plt.savefig(filename)
    plt.close()
    print(f"✅ Plot saved: {filename}")

# ---------- GLOBAL SUMMARY ----------
plt.figure(figsize=(10,6))
summary_data = {}
for setup_name, df in setup_data.items():
    summary_data[setup_name] = df.groupby('metric')['mean'].mean()
summary_df = pd.DataFrame(summary_data)
summary_df.plot(kind='bar', figsize=(12,6), rot=45)
plt.ylabel("Average across all nodes & repetitions")
plt.title("Global Metric Summary per Setup")
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "global_summary_setups.png"))
plt.close()
print("✅ Global summary plot saved")

print("✅ All setup comparison plots completed.")
