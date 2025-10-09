import os
import subprocess
import concurrent
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Simulation config
OMNET_EXECUTABLE = "/home/lars/Documents/opp_env/omnetpp-6.0.3/bin/opp_run"
BASE_INI = "omnetpp_base.ini"
RESULTS_DIR = "results"

# Parameter ranges
SPREAD_FACTORS = [7]  # [7, 8, 9, 10, 11, 12]
TRANSMIT_POWERS = [-5]  # [-5, -2, 1, 4, 7, 10]
NODE_COUNTS = [300]  # [300, 500]

# Parallelism
MAX_PARALLEL = 1

# NED paths
ned_dirs = [
    "../src",
    ".",
    "/home/lars/Documents/opp_env/inet-4.4.0/examples",
    "/home/lars/Documents/opp_env/inet-4.4.0/showcases",
    "/home/lars/Documents/opp_env/inet-4.4.0/src",
    "/home/lars/Documents/opp_env/inet-4.4.0/tests/validation",
    "/home/lars/Documents/opp_env/inet-4.4.0/tests/networks",
    "/home/lars/Documents/opp_env/inet-4.4.0/tutorials"
]
ned_path_arg = ":".join(ned_dirs)


def generate_ini(sf, tp, nodes):
    with open(BASE_INI, "r") as f:
        base_ini = f.read()

    updated_ini = base_ini
    updated_ini += f"\n**.numberOfNodes = {nodes}"
    updated_ini += f"\n**.loRaNodes[*].**initialLoRaSF = {sf}"
    updated_ini += f"\n**.loRaNodes[*].**initialLoRaTP = {tp}dBm"

    return updated_ini


def run_simulation(sf, tp, nodes):
    sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
    out_dir = os.path.join(RESULTS_DIR, sim_name)
    os.makedirs(out_dir, exist_ok=True)

    # Generate .ini content and write to file
    full_ini_content = generate_ini(sf, tp, nodes)
    ini_copy_path = os.path.join(out_dir, "omnetpp.ini")
    with open(ini_copy_path, "w") as f:
        f.write(full_ini_content)

    print(f"▶️ Starting simulation: {sim_name}")

    try:
        result = subprocess.run(
            [
                OMNET_EXECUTABLE,
                "-u", "Cmdenv",
                "-n", ned_path_arg,
                "-f", ini_copy_path,  # use modified ini file!
                "-l", "../src/flora",
                "-l", "/home/lars/Documents/opp_env/inet-4.4.0/src/INET",
                "-x", "inet.common.selfdoc;inet.emulation;inet.showcases.visualizer.osg;inet.examples.emulation;inet.showcases.emulation;inet.visualizer.osg",
                "--image-path", "/home/lars/Documents/opp_env/inet-4.4.0/images",
            ],
            cwd=".",  # Adjust if needed
            capture_output=True,
            text=True
        )

        # Save logs
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
