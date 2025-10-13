import os
import subprocess
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json
import re
import multiprocessing as mp
from collections import defaultdict
import numpy as np

# ---------------- CONFIG ----------------
OMNET_EXECUTABLE = "/home/lars/Documents/opp_env/omnetpp-6.0.3/bin/opp_run"
FLORA_ROOT = "/home/lars/Documents/WLAM2/TUE2526-5LIC0-NetwEmb"
INET_ROOT = "/home/lars/Documents/opp_env/inet-4.4.0"

BASE_INI = "omnetpp_base.ini"
RESULTS_DIR = "simulations/results"

# Parameter ranges
SPREAD_FACTORS = [7,12]  # [7, 8, 9, 10, 11, 12]
TRANSMIT_POWERS = [-5]  # [-5, -2, 1, 4, 7, 10]
NODE_COUNTS = [10]  # [300, 500]

MAX_PARALLEL = 8
CHUNK_SIZE_MB = 512  # for aggregation
# ---------------------------------------

node_pattern = re.compile(r"(?:loRaNodes|node)\[(\d+)\]", re.IGNORECASE)

# ---------- NED PATHS ----------
def get_ned_paths():
    ned_dirs = [
        os.path.join(FLORA_ROOT, "src"),
        os.path.join(FLORA_ROOT, "simulations"),
        "."
    ]
    if INET_ROOT and os.path.exists(INET_ROOT):
        inet_dirs = ["examples", "showcases", "src", "tests/validation", "tests/networks", "tutorials"]
        for inet_dir in inet_dirs:
            full_path = os.path.join(INET_ROOT, inet_dir)
            if os.path.exists(full_path):
                ned_dirs.append(full_path)
    return ":".join(ned_dirs)

# ---------- INI GENERATION ----------
def generate_ini(sf, tp, nodes):
    sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
    out_dir = os.path.join(FLORA_ROOT, RESULTS_DIR, sim_name)
    
    with open(BASE_INI, "r") as f:
        base_ini = f.read()

    updated_ini = base_ini
    updated_ini += f"\noutput-scalar-file = \"{out_dir}/${{repetition}}/scalars.sca\""
    updated_ini += f"\noutput-vector-file = \"{out_dir}/${{repetition}}/vectors.vec\""
    updated_ini += f"\n**.numberOfNodes = {nodes}"
    updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaSF = {sf}"
    updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaTP = {tp}dBm"

    return updated_ini

# ---------- RUN ONE SIMULATION ----------
def run_simulation(sf, tp, nodes):
    sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
    out_dir = os.path.join(FLORA_ROOT, RESULTS_DIR, sim_name)
    os.makedirs(out_dir, exist_ok=True)

    ini_path = f"omnetpp_{sim_name}.ini"
    with open(ini_path, "w") as f:
        f.write(generate_ini(sf, tp, nodes))

    cmd_args = [
        OMNET_EXECUTABLE,
        "-u", "Cmdenv",
        "-n", get_ned_paths(),
        "-f", ini_path,
        "-l", os.path.join(FLORA_ROOT, "src", "flora")
    ]

    if INET_ROOT:
        inet_lib = os.path.join(INET_ROOT, "src", "INET")
        cmd_args.extend(["-l", inet_lib])
        cmd_args.extend([
            "-x", "inet.common.selfdoc;inet.emulation;inet.showcases.visualizer.osg;"
                  "inet.examples.emulation;inet.showcases.emulation;inet.visualizer.osg",
            "--image-path", os.path.join(INET_ROOT, "images")
        ])

    try:
        result = subprocess.run(cmd_args, cwd=os.path.join(FLORA_ROOT, "simulations"),
                                capture_output=True, text=True)
        with open(os.path.join(out_dir, "stdout.txt"), "w") as f:
            f.write(result.stdout)
        with open(os.path.join(out_dir, "stderr.txt"), "w") as f:
            f.write(result.stderr)

        if result.returncode == 0:
            print(f"✅ Finished: {sim_name}")
        else:
            print(f"❌ Error in {sim_name} — see stderr.txt")
    except Exception as e:
        print(f"❌ Exception in {sim_name}: {e}")

# ---------- AGGREGATION ----------
def parse_chunk(path, start, end, vector_info):
    vector_stats = defaultdict(lambda: {"count":0,"sum":0.0,"min":float('inf'),"max":float('-inf')})
    node_stats = defaultdict(lambda: defaultdict(lambda: {"count":0,"sum":0.0,"min":float('inf'),"max":float('-inf')}))
    with open(path, "rb") as f:
        f.seek(start)
        if start != 0: f.readline()
        while f.tell() < end:
            line = f.readline()
            if not line: break
            line = line.decode(errors="ignore").strip()
            if not line or line.startswith("vector "): continue
            parts = line.split()
            if len(parts) < 4 or not parts[0].isdigit(): continue
            try: vec_id, value = int(parts[0]), float(parts[3])
            except ValueError: continue
            if vec_id not in vector_info: continue
            module, signal = vector_info[vec_id]
            vstats = vector_stats[vec_id]
            vstats["count"] += 1; vstats["sum"] += value
            vstats["min"] = min(vstats["min"], value)
            vstats["max"] = max(vstats["max"], value)
            node_match = node_pattern.search(module)
            if node_match:
                node_id = int(node_match.group(1))
                nstats = node_stats[node_id][signal]
                nstats["count"] += 1; nstats["sum"] += value
                nstats["min"] = min(nstats["min"], value)
                nstats["max"] = max(nstats["max"], value)
    return dict(vector_stats), {str(k): dict(v) for k,v in node_stats.items()}, 0

def parse_repetition(vec_path):
    vector_info = {}
    with open(vec_path,"r",encoding="utf-8",errors="ignore") as f:
        for line in f:
            if line.startswith("vector "):
                parts = line.strip().split()
                if len(parts)>=4:
                    vec_id = int(parts[1])
                    vector_info[vec_id] = (parts[2], parts[3])
    file_size = os.path.getsize(vec_path)
    chunk_size = CHUNK_SIZE_MB*1024*1024
    offsets = list(range(0,file_size,chunk_size))
    chunks = [(s,min(s+chunk_size,file_size)) for s in offsets]
    cpu_count = min(mp.cpu_count(),len(chunks))
    with mp.Pool(cpu_count) as pool:
        results = pool.starmap(parse_chunk, [(vec_path,s,e,vector_info) for s,e in chunks])
    final_vector_stats = defaultdict(lambda: {"count":0,"sum":0.0,"min":float('inf'),"max":float('-inf')})
    final_node_stats = defaultdict(lambda: defaultdict(lambda: {"count":0,"sum":0.0,"min":float('inf'),"max":float('-inf')}))
    for vstats,nstats,_ in results:
        for vid,s in vstats.items():
            fvs = final_vector_stats[vid]; fvs["count"] += s["count"]; fvs["sum"] += s["sum"]
            fvs["min"] = min(fvs["min"],s["min"]); fvs["max"]=max(fvs["max"],s["max"])
        for nid,signals in nstats.items():
            for sig,s in signals.items():
                ns = final_node_stats[nid][sig]; ns["count"]+=s["count"]; ns["sum"]+=s["sum"]
                ns["min"]=min(ns["min"],s["min"]); ns["max"]=max(ns["max"],s["max"])
    return final_vector_stats, final_node_stats, vector_info

def aggregate_setup(setup_name):
    setup_path = os.path.join(FLORA_ROOT, RESULTS_DIR)
    repetitions = sorted([f for f in os.listdir(setup_path) if f.isdigit()])
    all_reps_node_stats = []
    vector_info_global = {}
    for rep in repetitions:
        vec_path = os.path.join(setup_path, rep, "vectors.vec")
        vstats,nstats,vector_info = parse_repetition(vec_path)
        all_reps_node_stats.append(nstats)
        vector_info_global = vector_info
    aggregated_node_stats = defaultdict(dict)
    for node_id in all_reps_node_stats[0].keys():
        for signal in all_reps_node_stats[0][node_id].keys():
            values = []
            for rep_stats in all_reps_node_stats:
                if signal in rep_stats.get(node_id,{}):
                    s=rep_stats[node_id][signal]
                    if s["count"]>0:
                        values.append(s["sum"]/s["count"])
            if values:
                aggregated_node_stats[node_id][signal] = {"mean": float(np.mean(values)),"std": float(np.std(values))}
    output_json = os.path.join(setup_path, setup_name,"aggregated_vector_stats.json")
    with open(output_json,"w") as f:
        json.dump({
            "vector_info": {str(k):v for k,v in vector_info_global.items()},
            "aggregated_node_stats": {str(k):v for k,v in aggregated_node_stats.items()},
            "repetitions": repetitions
        },f,indent=2)
    print(f"✅ Aggregated JSON saved for setup '{setup_name}'")

# ---------- MAIN ----------
def main():
    os.makedirs(os.path.join(FLORA_ROOT, RESULTS_DIR), exist_ok=True)
    param_combinations = list(product(SPREAD_FACTORS, TRANSMIT_POWERS, NODE_COUNTS))
    
    for sf, tp, nodes in param_combinations:
        setup_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
        print(f"\n▶️ Running setup: {setup_name}")

        # Run the simulation once; repetitions are handled by the .ini
        run_simulation(sf, tp, nodes)

        # Aggregate results immediately after the run finishes
        print(f"\n📊 Aggregating results for {setup_name} ...")
        aggregate_setup(setup_name)

if __name__ == "__main__":
    main()

