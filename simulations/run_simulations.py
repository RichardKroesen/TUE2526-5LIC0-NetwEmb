import os
import subprocess
import concurrent
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configuration Paths
OMNET_EXECUTABLE = "/home/richard/omnetpp-6.2.0/bin/opp_run"
FLORA_ROOT = "/home/richard/1-Dev/5LIC0-EmbNetw"
INET_ROOT = "/home/richard/omnetpp-6.2.0/samples/inet4.4" 

# Simulation config
BASE_INI = "omnetpp_base.ini"
RESULTS_DIR = "results"

# Parameter ranges
SPREAD_FACTORS = [7]  # [7, 8, 9, 10, 11, 12]
TRANSMIT_POWERS = [-5]  # [-5, -2, 1, 4, 7, 10]
NODE_COUNTS = [300]  # [300, 500]

# Parallelism
MAX_PARALLEL = 1

def get_ned_paths():
    ned_dirs = []
    
    # Add FLoRa source directory
    flora_src = os.path.join(FLORA_ROOT, "src")
    ned_dirs.append(flora_src)
    
    # Add simulations directory (where package.ned with LoRaNetworkTest is located)
    simulations_dir = os.path.join(FLORA_ROOT, "simulations")
    ned_dirs.append(simulations_dir)
    ned_dirs.append(".")
    
    # INET paths
    if INET_ROOT and os.path.exists(INET_ROOT):
        inet_dirs = [
            "examples",
            "showcases", 
            "src",
            "tests/validation",
            "tests/networks",
            "tutorials"
        ]
        for inet_dir in inet_dirs:
            full_path = os.path.join(INET_ROOT, inet_dir)
            if os.path.exists(full_path):
                ned_dirs.append(full_path)
    
    return ":".join(ned_dirs)

def generate_ini(sf, tp, nodes):
    sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
    out_dir = os.path.join(FLORA_ROOT, "simulations", RESULTS_DIR, sim_name)
    
    with open(BASE_INI, "r") as f:
        base_ini = f.read()

    updated_ini = base_ini
    
    updated_ini += f"\noutput-scalar-file = \"{out_dir}/${{repetition}}/scalars.sca\""
    updated_ini += f"\noutput-vector-file = \"{out_dir}/${{repetition}}/vectors.vec\""
    
    # Simulation specific params
    updated_ini += f"\n**.numberOfNodes = {nodes}"
    updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaSF = {sf}"
    updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaTP = {tp}dBm"

    return updated_ini

def run_simulation(sf, tp, nodes):
    sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
    out_dir = os.path.join(RESULTS_DIR, sim_name)
    os.makedirs(out_dir, exist_ok=True)

    full_ini_content = generate_ini(sf, tp, nodes)
    ini_copy_path = f"omnetpp_{sim_name}.ini"  
    with open(ini_copy_path, "w") as f:
        f.write(full_ini_content)

    print(f"▶️ Starting simulation: {sim_name}")

    # Build command arguments
    cmd_args = [
        OMNET_EXECUTABLE,
        "-u", "Cmdenv",
        "-n", get_ned_paths(),
        "-f", ini_copy_path, 
        "-l", os.path.join(FLORA_ROOT, "src", "flora")
    ]
    
    # Add INET library if specified
    if INET_ROOT:
        inet_lib = os.path.join(INET_ROOT, "src", "INET")
        cmd_args.extend(["-l", inet_lib])
        
        # Add exclusions 
        cmd_args.extend([
            "-x", "inet.common.selfdoc;inet.emulation;inet.showcases.visualizer.osg;inet.examples.emulation;inet.showcases.emulation;inet.visualizer.osg",
            "--image-path", os.path.join(INET_ROOT, "images")
        ])

    try:
        result = subprocess.run(
            cmd_args,
            cwd=os.path.join(FLORA_ROOT, "simulations"),
            capture_output=True,
            text=True
        )

        # Save logs to the results subdirectory
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

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    param_combinations = list(product(SPREAD_FACTORS, TRANSMIT_POWERS, NODE_COUNTS))
    total_jobs = len(param_combinations)

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {
            executor.submit(run_simulation, sf, tp, nodes): (sf, tp, nodes)
            for sf, tp, nodes in param_combinations
        }

        for future in tqdm(as_completed(futures), total=total_jobs, desc="Simulations"):
            try:
                future.result()
            except Exception as e:
                sf, tp, nodes = futures[future]
                print(f"❌ Failed for SF={sf}, TP={tp}, N={nodes}: {e}")

if __name__ == "__main__":
    main()
