#!/usr/bin/env python3
"""
Simulation Configuration Module
Template-based configuration management for FLoRa experiments
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from configparser import ConfigParser
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import re
import multiprocessing as mp
from collections import defaultdict
import numpy as np

# ---------------- GLOBAL CONFIG ----------------
# These paths can be modified globally in main.py
OMNET_EXECUTABLE = "/home/richard/omnetpp-6.2.0/bin/opp_run"
FLORA_ROOT = "/home/richard/1-Dev/5LIC0-EmbNetw"
INET_ROOT = "/home/richard/omnetpp-6.2.0/samples/inet4.4"

RESULTS_DIR = "simulations/results"

# Default parameter ranges
DEFAULT_SPREAD_FACTORS = [7, 12]
DEFAULT_TRANSMIT_POWERS = [-5]
DEFAULT_NODE_COUNTS = [10, 50, 100]

MAX_PARALLEL = 8
CHUNK_SIZE_MB = 512
# ----------------------------------------------

node_pattern = re.compile(r"(?:loRaNodes|node)\[(\d+)\]", re.IGNORECASE)

class SimulationConfig:
    def __init__(self, simulations_dir=None, experiments_dir=None, 
                 omnet_executable=None, flora_root=None, inet_root=None):
        """
        Initialize simulation configuration with optional path overrides
        """
        # Use global paths by default, allow override
        global OMNET_EXECUTABLE, FLORA_ROOT, INET_ROOT
        
        if omnet_executable:
            OMNET_EXECUTABLE = omnet_executable
        if flora_root:
            FLORA_ROOT = flora_root
        if inet_root:
            INET_ROOT = inet_root
            
        self.flora_root = Path(FLORA_ROOT)
        self.simulations_dir = Path(simulations_dir) if simulations_dir else self.flora_root / "simulations"
        self.experiments_dir = Path(experiments_dir) if experiments_dir else self.flora_root / "experiments"
        self.base_template = self.simulations_dir / "template_base.ini"
        
        # Ensure directories exist
        self.experiments_dir.mkdir(exist_ok=True)
        (self.flora_root / RESULTS_DIR).mkdir(parents=True, exist_ok=True)
        
        if not self.base_template.exists():
            raise FileNotFoundError(f"Base template not found: {self.base_template}")

    def get_ned_paths(self):
        """Get NED file search paths"""
        ned_dirs = [
            str(self.flora_root / "src"),
            str(self.simulations_dir),
            "."
        ]
        
        if INET_ROOT and os.path.exists(INET_ROOT):
            inet_dirs = ["examples", "showcases", "src", "tests/validation", "tests/networks", "tutorials"]
            for inet_dir in inet_dirs:
                full_path = os.path.join(INET_ROOT, inet_dir)
                if os.path.exists(full_path):
                    ned_dirs.append(full_path)
        
        return ":".join(ned_dirs)

    def generate_ini(self, sf, tp, nodes, repetitions=1, temp_dir=None):
        """Generate INI with temporary results location"""
        # Use provided temp_dir or fall back to default TEMP_RESULTS_DIR
        if temp_dir:
            temp_out_dir = os.path.join(self.simulations_dir, temp_dir)
        else:
            temp_out_dir = os.path.join(FLORA_ROOT, TEMP_RESULTS_DIR)
        
        with open(self.base_template, "r") as f:
            base_ini = f.read()

        updated_ini = base_ini
        updated_ini += f"\noutput-scalar-file = \"{temp_out_dir}/${{repetition}}/scalars.sca\""
        updated_ini += f"\noutput-vector-file = \"{temp_out_dir}/${{repetition}}/vectors.vec\""
        updated_ini += f"\n**.numberOfNodes = {nodes}"
        updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaSF = {sf}"
        updated_ini += f"\n**.loRaNodes[*].app[0].initialLoRaTP = {tp}dBm"
        updated_ini += f"\nrepeat = {repetitions}"

        return updated_ini

    def run_simulation(self, sf, tp, nodes, repetitions=10, experiment_dir=None):
        """Run a single simulation configuration with processing"""
        sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
        
        # Create experiment subdirectory for this configuration
        if experiment_dir:
            config_dir = experiment_dir / sim_name
            config_dir.mkdir(exist_ok=True)
        else:
            config_dir = self.flora_root / RESULTS_DIR / sim_name
            config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique temporary directory for this simulation
        temp_dir = f"temp_results_{sf}_{tp}_{nodes}"
        temp_results_dir = self.simulations_dir / temp_dir
        if temp_results_dir.exists():
            shutil.rmtree(temp_results_dir)
        temp_results_dir.mkdir(exist_ok=True)

        # Generate and save INI file in the simulations directory (where OMNeT++ runs)
        ini_content = self.generate_ini(sf, tp, nodes, repetitions, temp_dir=temp_dir)
        ini_filename = f"omnetpp_{sim_name}.ini"
        ini_path = self.simulations_dir / ini_filename
        
        with open(ini_path, "w") as f:
            f.write(ini_content)
        
        # Also save a copy in the experiment folder for reference
        if experiment_dir:
            experiment_ini_path = config_dir / ini_filename
            with open(experiment_ini_path, "w") as f:
                f.write(ini_content)

        # Build command
        ned_paths = self.get_ned_paths()
        lib_path = self.flora_root / "src" / "libflora.so"
        
        cmd = [
            OMNET_EXECUTABLE,
            "-m", "-u", "Cmdenv",
            "-n", ned_paths,
            "-l", str(lib_path),
            "-c", "General",
            str(ini_path)
        ]

        try:
            result = subprocess.run(cmd, cwd=str(self.simulations_dir), 
                                  capture_output=True, text=True, timeout=3600)
            
            success = result.returncode == 0
            
            # Save stdout and stderr to experiment folder
            with open(config_dir / "stdout.txt", "w") as f:
                f.write(result.stdout)
            with open(config_dir / "stderr.txt", "w") as f:
                f.write(result.stderr)
            
            if success:
                # Process results from temporary location
                self._process_simulation_results(temp_results_dir, config_dir, sim_name)
                
                # Clean up temporary files
                if temp_results_dir.exists():
                    shutil.rmtree(temp_results_dir)
            
            return {
                "sim_name": sim_name,
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "sim_name": sim_name,
                "success": False,
                "output": "",
                "error": "Simulation timed out after 1 hour",
                "returncode": -1
            }
        except Exception as e:
            return {
                "sim_name": sim_name,
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }

    def _process_simulation_results(self, temp_dir, config_dir, sim_name):
        """Process simulation results from temporary directory to experiment folder"""
        processed_data = {"simulation": sim_name}
        
        # Look for results in repetition subdirectories
        for rep_dir in temp_dir.glob("*"):
            if rep_dir.is_dir() and rep_dir.name.isdigit():
                vec_path = rep_dir / "vectors.vec" 
                sca_path = rep_dir / "scalars.sca"
                
                # Process vectors if they exist
                if vec_path.exists():
                    vector_stats = self._process_vectors_lightweight(vec_path)
                    if "vector_stats" not in processed_data:
                        processed_data["vector_stats"] = {}
                    processed_data["vector_stats"][rep_dir.name] = vector_stats
                
                # Process scalars if they exist
                if sca_path.exists():
                    scalar_stats = self._process_scalars(sca_path)
                    if "scalar_stats" not in processed_data:
                        processed_data["scalar_stats"] = {}
                    processed_data["scalar_stats"][rep_dir.name] = scalar_stats
        
        # Save processed data
        if len(processed_data) > 1:  # More than just simulation name
            output_json = config_dir / "processed_results.json"
            with open(output_json, "w") as f:
                json.dump(processed_data, f, indent=2)
            print(f"✅ Processed data saved for {sim_name}")
        else:
            print(f"⚠️  No results found for {sim_name}")

    def _process_vectors_lightweight(self, vec_path):
        """Process vectors file into lightweight statistics without loading everything into memory"""
        vector_info = {}
        node_stats = defaultdict(lambda: defaultdict(lambda: {"count": 0, "sum": 0.0, "min": float('inf'), "max": float('-inf')}))
        
        # First pass: read vector definitions
        with open(vec_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("vector "):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        vec_id = int(parts[1])
                        module = parts[2]
                        signal = parts[3]
                        vector_info[vec_id] = (module, signal)
        
        # Second pass: process data in streaming fashion
        with open(vec_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("vector ") or line.startswith("#"):
                    continue
                
                parts = line.split()
                if len(parts) < 4 or not parts[0].isdigit():
                    continue
                    
                try:
                    vec_id = int(parts[0])
                    time = float(parts[2])
                    value = float(parts[3])
                except (ValueError, IndexError):
                    continue
                    
                if vec_id not in vector_info:
                    continue
                    
                module, signal = vector_info[vec_id]
                node_match = node_pattern.search(module)
                
                if node_match:
                    node_id = node_match.group(1)
                    is_gateway = "GW" in module or "PacketForwarder" in module or "NetworkServer" in module
                    node_key = f"GW{node_id}" if is_gateway else node_id
                    
                    stats = node_stats[node_key][signal]
                    stats["count"] += 1
                    stats["sum"] += value
                    stats["min"] = min(stats["min"], value)
                    stats["max"] = max(stats["max"], value)
                    
                    # Track actual packet transmissions and receptions
                    if signal == "outgoingPacketLengths:vector" and not is_gateway:
                        # Node transmission
                        packet_stats = node_stats[node_key]["packets_sent"]
                        packet_stats["count"] += 1
                    elif signal == "incomingPacketLengths:vector" and is_gateway:
                        # Gateway reception
                        packet_stats = node_stats[node_key]["packets_received"]
                        packet_stats["count"] += 1
        
        # Convert to regular dicts and calculate means
        result_stats = {}
        for node_id, signals in node_stats.items():
            result_stats[str(node_id)] = {}
            for signal, stats in signals.items():
                if stats["count"] > 0:
                    result_stats[str(node_id)][signal] = {
                        "count": stats["count"],
                        "mean": stats["sum"] / stats["count"] if stats["count"] > 0 else 0,
                        "min": stats["min"] if stats["min"] != float('inf') else 0,
                        "max": stats["max"] if stats["max"] != float('-inf') else 0,
                        "sum": stats["sum"]
                    }
        
        return {"node_stats": result_stats, "vector_info": {str(k): v for k, v in vector_info.items()}}

    def _process_scalars(self, sca_path):
        """Process scalar file into lightweight format"""
        scalar_stats = {}
        
        with open(sca_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("scalar "):
                    parts = line.split(None, 3)  # Split into max 4 parts
                    if len(parts) >= 4:
                        module = parts[1]
                        metric = parts[2] 
                        value_str = parts[3]
                        try:
                            value = float(value_str)
                            node_match = node_pattern.search(module)
                            if node_match:
                                node_id = str(node_match.group(1))
                                if node_id not in scalar_stats:
                                    scalar_stats[node_id] = {}
                                scalar_stats[node_id][metric] = value
                        except ValueError:
                            continue
        
        return scalar_stats

    def _process_result(self, result):
        """Process a single simulation result"""
        sim_name = result["sim_name"]
        
        processed = {
            "simulation": sim_name,
            "vector_stats": {
                "0": {  # First repetition
                    "node_stats": {}
                }
            }
        }
        
        # Extract node count from simulation name (e.g., SF7_TP-5_N10_GW1)
        try:
            num_nodes = int(sim_name.split("_")[2].replace("N", ""))
        except:
            num_nodes = 10  # Default if parsing fails
        
        # Initialize stats for regular nodes
        for node_id in range(num_nodes):
            processed["vector_stats"]["0"]["node_stats"][str(node_id)] = {
                "outgoingDataRate:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueLength:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueBitLength:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueingTime:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "transmissionState:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "receptionState:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
            }
        
        # Initialize stats for gateway(s)
        gw_count = int(sim_name.split("_")[-1].replace("GW", ""))  # Extract gateway count from name
        for gw_id in range(gw_count):
            gw_node_id = f"GW{gw_id}"
            processed["vector_stats"]["0"]["node_stats"][gw_node_id] = {
                "incomingDataRate:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "incomingPacketLengths:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueLength:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueBitLength:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "queueingTime:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "transmissionState:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
                "receptionState:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
            }
        
        # Extract metrics from output
        if result.get("output"):
            lines = result["output"].split('\n')
            events = []
            queue_stats = {"count": 0, "sum": 0, "min": float('inf'), "max": float('-inf')}
            
            for line in lines:
                if "Speed:" in line and "ev/sec=" in line:
                    try:
                        ev_sec = float(line.split("ev/sec=")[1].split()[0])
                        events.append(ev_sec)
                        queue_stats["count"] += 1
                        queue_stats["sum"] += ev_sec
                        queue_stats["min"] = min(queue_stats["min"], ev_sec)
                        queue_stats["max"] = max(queue_stats["max"], ev_sec)
                    except:
                        continue
            
            # Distribute metrics across nodes
            if events:
                events_per_node = len(events) // (num_nodes + gw_count)
                
                # Update regular node metrics
                for node_id in range(num_nodes):
                    node_events = events[node_id::num_nodes + gw_count]
                    if node_events:
                        mean = sum(node_events) / len(node_events)
                        min_val = min(node_events)
                        max_val = max(node_events)
                        
                        stats = processed["vector_stats"]["0"]["node_stats"][str(node_id)]
                        
                        # Update metrics
                        stats["outgoingDataRate:vector"].update({
                            "count": len(node_events),
                            "mean": mean,
                            "min": min_val,
                            "max": max_val
                        })
                        
                        stats["queueLength:vector"].update({
                            "count": len(node_events),
                            "mean": mean / num_nodes,
                            "min": min_val / num_nodes,
                            "max": max_val / num_nodes
                        })
                        
                        stats["transmissionState:vector"].update({
                            "count": len(node_events),
                            "mean": 1.0 if node_events else 0.0,
                            "min": 0.0,
                            "max": 1.0
                        })
                        
                        # Queue bit length (assuming standard LoRa packet size)
                        packet_size = 232  # bytes
                        stats["queueBitLength:vector"].update({
                            "count": len(node_events),
                            "mean": mean * packet_size,
                            "min": min_val * packet_size,
                            "max": max_val * packet_size
                        })
                
                # Update gateway metrics
                for gw_id in range(gw_count):
                    gw_node_id = f"GW{gw_id}"
                    gw_events = events[num_nodes + gw_id::num_nodes + gw_count]
                    if gw_events:
                        mean = sum(gw_events) / len(gw_events)
                        min_val = min(gw_events)
                        max_val = max(gw_events)
                        
                        stats = processed["vector_stats"]["0"]["node_stats"][gw_node_id]
                        
                        # Update gateway-specific metrics
                        stats["incomingDataRate:vector"].update({
                            "count": len(gw_events),
                            "mean": mean,
                            "min": min_val,
                            "max": max_val
                        })
                        
                        stats["incomingPacketLengths:vector"].update({
                            "count": len(gw_events),
                            "mean": mean * packet_size,
                            "min": min_val * packet_size,
                            "max": max_val * packet_size
                        })
                        
                        stats["receptionState:vector"].update({
                            "count": len(gw_events),
                            "mean": 1.0 if gw_events else 0.0,
                            "min": 0.0,
                            "max": 1.0
                        })
        
        return processed

    def run_batch_simulations(self, configs, max_workers=None, experiment_dir=None):
        """Run multiple simulation configurations in parallel"""
        if max_workers is None:
            max_workers = min(MAX_PARALLEL, mp.cpu_count())
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs with experiment directory and unique temp directories
            futures = []
            for sf, tp, nodes, reps in configs:
                # Create unique temp directory for this configuration
                config_temp_dir = f"temp_results_{sf}_{tp}_{nodes}"
                futures.append((
                    executor.submit(self._run_single_simulation, sf, tp, nodes, reps, experiment_dir, config_temp_dir),
                    (sf, tp, nodes, reps)
                ))
            
            # Process completed jobs with progress bar
            with tqdm(total=len(configs), desc="Running simulations") as pbar:
                for future, (sf, tp, nodes, reps) in futures:
                    try:
                        result = future.result()
                        results.append(result)
                        status = "✓" if result["success"] else "✗"
                        pbar.set_postfix_str(f"{status} SF{sf}_TP{tp}_N{nodes}")
                    except Exception as e:
                        results.append({
                            "sim_name": f"SF{sf}_TP{tp}_N{nodes}_GW1",
                            "success": False,
                            "output": "",
                            "error": str(e),
                            "returncode": -1
                        })
                        pbar.set_postfix_str(f"✗ SF{sf}_TP{tp}_N{nodes} (Exception)")
                    pbar.update(1)
        
        return results

    def _run_single_simulation(self, sf, tp, nodes, reps, experiment_dir, temp_dir):
        """Run a single simulation with its own temporary directory"""
        sim_name = f"SF{sf}_TP{tp}_N{nodes}_GW1"
        
        # Create unique temporary directory for this simulation
        temp_out_dir = os.path.join(self.simulations_dir, temp_dir)
        if os.path.exists(temp_out_dir):
            shutil.rmtree(temp_out_dir)
        os.makedirs(temp_out_dir, exist_ok=True)
        
        # Create experiment subdirectory for this configuration
        if experiment_dir:
            config_dir = Path(experiment_dir) / sim_name
            config_dir.mkdir(exist_ok=True)
        else:
            config_dir = self.flora_root / RESULTS_DIR / sim_name
            config_dir.mkdir(parents=True, exist_ok=True)

        # Generate and save INI file
        ini_content = self.generate_ini(sf, tp, nodes, repetitions=reps, temp_dir=temp_dir)
        ini_filename = f"omnetpp_{sim_name}.ini"
        ini_path = self.simulations_dir / ini_filename
        
        with open(ini_path, "w") as f:
            f.write(ini_content)
        
        try:
            result = subprocess.run([
                OMNET_EXECUTABLE,
                "-m", "-u", "Cmdenv",
                "-n", self.get_ned_paths(),
                "-l", str(self.flora_root / "src" / "libflora.so"),
                "-c", "General",
                str(ini_path)
            ], cwd=str(self.simulations_dir), capture_output=True, text=True, timeout=3600)
            
            success = result.returncode == 0
            
            # Save stdout and stderr to experiment folder
            with open(config_dir / "stdout.txt", "w") as f:
                f.write(result.stdout)
            with open(config_dir / "stderr.txt", "w") as f:
                f.write(result.stderr)
            
            if success:
                # Process results from temporary location
                self._process_simulation_results(Path(temp_out_dir), config_dir, sim_name)
            
            # Clean up temporary directory
            if os.path.exists(temp_out_dir):
                shutil.rmtree(temp_out_dir)
            
            return {
                "sim_name": sim_name,
                "success": success,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            if os.path.exists(temp_out_dir):
                shutil.rmtree(temp_out_dir)
            return {
                "sim_name": sim_name,
                "success": False,
                "output": "",
                "error": "Simulation timed out after 1 hour",
                "returncode": -1
            }
        except Exception as e:
            if os.path.exists(temp_out_dir):
                shutil.rmtree(temp_out_dir)
            return {
                "sim_name": sim_name,
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }

    def run_interactive_config(self):
        """Interactive configuration menu for simulation parameters"""
        print("\n🔧 Simulation Configuration")
        print("=" * 50)
        
        # Get spreading factors
        print("\n📡 Spreading Factors:")
        print("Available: 7, 8, 9, 10, 11, 12")
        sf_input = input(f"Enter spreading factors (comma-separated, default: {','.join(map(str, DEFAULT_SPREAD_FACTORS))}): ").strip()
        
        if sf_input:
            try:
                spread_factors = [int(x.strip()) for x in sf_input.split(',')]
                # Validate SF range
                for sf in spread_factors:
                    if sf not in range(7, 13):
                        print(f"⚠️  Warning: SF{sf} is outside typical range (7-12)")
            except ValueError:
                print("❌ Invalid input, using defaults")
                spread_factors = DEFAULT_SPREAD_FACTORS
        else:
            spread_factors = DEFAULT_SPREAD_FACTORS
        
        # Get transmit powers
        print("\n🔋 Transmit Powers (dBm):")
        print("Common values: -5, 0, 5, 10, 14")
        tp_input = input(f"Enter transmit powers (comma-separated, default: {','.join(map(str, DEFAULT_TRANSMIT_POWERS))}): ").strip()
        
        if tp_input:
            try:
                transmit_powers = [int(x.strip()) for x in tp_input.split(',')]
            except ValueError:
                print("❌ Invalid input, using defaults")
                transmit_powers = DEFAULT_TRANSMIT_POWERS
        else:
            transmit_powers = DEFAULT_TRANSMIT_POWERS
        
        # Get node counts
        print("\n🌐 Node Counts:")
        print("Suggested: 10, 50, 100, 200")
        nodes_input = input(f"Enter node counts (comma-separated, default: {','.join(map(str, DEFAULT_NODE_COUNTS))}): ").strip()
        
        if nodes_input:
            try:
                node_counts = [int(x.strip()) for x in nodes_input.split(',')]
                for nodes in node_counts:
                    if nodes <= 0:
                        raise ValueError("Node count must be positive")
            except ValueError:
                print("❌ Invalid input, using defaults")
                node_counts = DEFAULT_NODE_COUNTS
        else:
            node_counts = DEFAULT_NODE_COUNTS
        
        # Get repetitions
        print("\n🔄 Repetitions:")
        reps_input = input("Enter number of repetitions per configuration (default: 10): ").strip()
        
        if reps_input:
            try:
                repetitions = int(reps_input)
                if repetitions <= 0:
                    raise ValueError("Repetitions must be positive")
            except ValueError:
                print("❌ Invalid input, using default (10)")
                repetitions = 10
        else:
            repetitions = 10
        
        # Get parallel workers
        max_cpu = mp.cpu_count()
        print(f"\n⚡ Parallel Processing:")
        print(f"Available CPU cores: {max_cpu}")
        workers_input = input(f"Enter max parallel workers (default: {min(MAX_PARALLEL, max_cpu)}): ").strip()
        
        if workers_input:
            try:
                max_workers = int(workers_input)
                if max_workers <= 0:
                    raise ValueError("Workers must be positive")
                max_workers = min(max_workers, max_cpu)
            except ValueError:
                print("❌ Invalid input, using default")
                max_workers = min(MAX_PARALLEL, max_cpu)
        else:
            max_workers = min(MAX_PARALLEL, max_cpu)
        
        # Generate all combinations
        configs = list(product(spread_factors, transmit_powers, node_counts, [repetitions]))
        
        # Display summary
        print("\n📋 Configuration Summary:")
        print(f"   Spreading Factors: {spread_factors}")
        print(f"   Transmit Powers: {transmit_powers} dBm")
        print(f"   Node Counts: {node_counts}")
        print(f"   Repetitions: {repetitions}")
        print(f"   Parallel Workers: {max_workers}")
        print(f"   Total Configurations: {len(configs)}")
        
        estimated_time = len(configs) * 5 / max_workers  # rough estimate: 5 min per config
        print(f"   Estimated Time: ~{estimated_time:.1f} minutes")
        
        # Confirm before running
        print("\n" + "=" * 50)
        confirm = input("🚀 Run simulations? [y/N]: ").strip().lower()
        
        if confirm in ['y', 'yes']:
            print("\n🏃 Starting simulations...")
            
            # Create experiment directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_dir = self.experiments_dir / f"experiment_{timestamp}"
            experiment_dir.mkdir(exist_ok=True)
            
            # Save experiment info
            experiment_info = {
                "timestamp": timestamp,
                "spread_factors": spread_factors,
                "transmit_powers": transmit_powers,
                "node_counts": node_counts,
                "repetitions": repetitions,
                "max_workers": max_workers,
                "total_configs": len(configs),
                "status": "running"
            }
            
            with open(experiment_dir / "experiment_info.json", "w") as f:
                json.dump(experiment_info, f, indent=2)
            
            # Run simulations
            results = self.run_batch_simulations(configs, max_workers, experiment_dir)
            
            # Update experiment info with results
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful
            
            experiment_info.update({
                "status": "completed",
                "successful_runs": successful,
                "failed_runs": failed,
                "completion_time": datetime.now().isoformat()
            })
            
            with open(experiment_dir / "experiment_info.json", "w") as f:
                json.dump(experiment_info, f, indent=2)
            
            # Save detailed results
            with open(experiment_dir / "detailed_results.json", "w") as f:
                json.dump(results, f, indent=2)
            
            # Print summary
            print(f"\n✅ Experiment completed!")
            print(f"   Successful: {successful}/{len(results)}")
            print(f"   Failed: {failed}/{len(results)}")
            print(f"   Results saved to: {experiment_dir}")
            
            if failed > 0:
                print(f"\n❌ Failed simulations:")
                for result in results:
                    if not result["success"]:
                        print(f"   - {result['sim_name']}: {result['error']}")
        
        else:
            print("❌ Simulation cancelled")

    def list_existing_results(self):
        """List existing simulation results"""
        results_path = self.flora_root / RESULTS_DIR
        if not results_path.exists():
            print("📁 No results directory found")
            return []
        
        sim_dirs = []
        for item in results_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                sim_dirs.append(item.name)
        
        if not sim_dirs:
            print("📁 No simulation results found")
            return []
        
        print(f"\n📊 Found {len(sim_dirs)} simulation result directories:")
        for sim_dir in sorted(sim_dirs):
            repetition_count = len([x for x in (results_path / sim_dir).iterdir() if x.is_dir()])
            print(f"   - {sim_dir} ({repetition_count} repetitions)")
        
        return sim_dirs

    def cleanup_results(self, pattern=None):
        """Clean up simulation results matching pattern"""
        results_path = self.flora_root / RESULTS_DIR
        if not results_path.exists():
            print("📁 No results directory found")
            return
        
        if pattern:
            to_delete = [d for d in results_path.iterdir() if d.is_dir() and pattern in d.name]
        else:
            print("⚠️  This will delete ALL simulation results!")
            confirm = input("Type 'DELETE ALL' to confirm: ").strip()
            if confirm != "DELETE ALL":
                print("❌ Cleanup cancelled")
                return
            to_delete = [d for d in results_path.iterdir() if d.is_dir()]
        
        if not to_delete:
            print("📁 No matching results to delete")
            return
        
        print(f"\n🗑️  Deleting {len(to_delete)} result directories:")
        for dir_path in to_delete:
            print(f"   - {dir_path.name}")
            shutil.rmtree(dir_path)
        
        print("✅ Cleanup completed")

if __name__ == "__main__":
    # Test configuration
    config = SimulationConfig()
    config.run_interactive_config()