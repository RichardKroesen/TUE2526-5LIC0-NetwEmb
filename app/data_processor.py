#!/usr/bin/env python3
"""
Data Processing Module
Processes raw simulation output into structured format for visualization
"""

import os
import json
from pathlib import Path
from datetime import datetime

class DataProcessor:
    def __init__(self, experiments_dir):
        self.experiments_dir = Path(experiments_dir)
        self.available_experiments = self._scan_available_experiments()
    
    def _scan_available_experiments(self):
        """Scan for available experiment results"""
        experiments = []
        if self.experiments_dir.exists():
            for exp_dir in self.experiments_dir.iterdir():
                if (exp_dir.is_dir() and 
                    exp_dir.name.startswith('experiment_')):
                    
                    # Get configuration directories
                    configs = []
                    for config_dir in exp_dir.iterdir():
                        if config_dir.is_dir() and not config_dir.name in ['analysis', 'exports']:
                            has_processed = (config_dir / "processed_results.json").exists()
                            has_details = (exp_dir / "detailed_results.json").exists()
                            
                            configs.append({
                                'name': config_dir.name,
                                'path': config_dir,
                                'processed': has_processed,
                                'has_details': has_details
                            })
                    
                    experiments.append({
                        'name': exp_dir.name,
                        'path': exp_dir,
                        'configs': configs
                    })
        return experiments
    
    def show_available_experiments(self):
        """Display available experiments and their processing status"""
        print("\n⚙️  Available Experiments:")
        print("-" * 50)
        
        if not self.available_experiments:
            print("❌ No experiments found")
            return
            
        for i, exp in enumerate(self.available_experiments, 1):
            print(f"{i:2d}. {exp['name']}")
            configs = exp['configs']
            needs_processing = sum(1 for c in configs if not c['processed'] and c['has_details'])
            processed = sum(1 for c in configs if c['processed'])
            
            print(f"    📊 Configurations: {len(configs)} | Processed: {processed} | Needs Processing: {needs_processing}")
            
            # Show first few configurations
            for config in configs[:3]:
                status = []
                if config['processed']:
                    status.append("PROCESSED")
                if config['has_details']:
                    status.append("HAS_DETAILS")
                status_str = f"[{'/'.join(status)}]" if status else "[EMPTY]"
                print(f"      - {config['name']} {status_str}")
            
            if len(configs) > 3:
                print(f"      ... and {len(configs) - 3} more configurations")
            print()
    
    def process_experiment_data(self):
        """Process raw data for selected experiment"""
        self.show_available_experiments()
        
        if not self.available_experiments:
            return
            
        choice = input(f"\nSelect experiment to process (1-{len(self.available_experiments)}): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.available_experiments):
                experiment = self.available_experiments[idx]
                self._process_experiment(experiment)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Please enter a valid number")
    
    def _process_experiment(self, experiment):
        """Process a specific experiment"""
        print(f"\n⚙️  Processing Experiment: {experiment['name']}")
        
        # Find configurations that need processing
        needs_processing = [c for c in experiment['configs'] 
                          if not c['processed'] and c['has_details']]
        
        if not needs_processing:
            print("✅ All configurations are already processed!")
            return
        
        print(f"\n📋 {len(needs_processing)} configurations need processing:")
        for config in needs_processing:
            print(f"  • {config['name']}")
        
        print("\nProcessing Options:")
        print("1. 🔄 Process All")
        print("2. 🎯 Process Selected")
        
        choice = input("\nSelect processing option (1-2): ").strip()
        
        if choice == "1":
            self._process_configs(experiment['path'], needs_processing)
        elif choice == "2":
            print("\nSelect configurations to process:")
            for i, config in enumerate(needs_processing, 1):
                print(f"{i:2d}. {config['name']}")
            
            selection = input("\nEnter configuration numbers (comma-separated): ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected = [needs_processing[i] for i in indices if 0 <= i < len(needs_processing)]
                if selected:
                    self._process_configs(experiment['path'], selected)
                else:
                    print("❌ No valid selections")
            except ValueError:
                print("❌ Invalid selection format")
    
    def _process_configs(self, exp_path, configs):
        """Process multiple configurations"""
        detailed_results_file = exp_path / "detailed_results.json"
        if not detailed_results_file.exists():
            print("❌ No detailed results file found")
            return
        
        try:
            with open(detailed_results_file, 'r') as f:
                all_results = json.load(f)
            
            for config in configs:
                print(f"\n🔄 Processing {config['name']}...")
                
                # Find results for this configuration
                result = next((r for r in all_results if r["sim_name"] == config['name']), None)
                if result and result["success"]:
                    processed_data = self._process_result(result)
                    
                    # Save processed data
                    output_file = config['path'] / "processed_results.json"
                    with open(output_file, 'w') as f:
                        json.dump(processed_data, f, indent=2)
                    print(f"✅ Processed data saved")
                else:
                    print(f"❌ No successful results found")
        except Exception as e:
            print(f"❌ Error processing results: {str(e)}")
    
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
        
        # Initialize stats for each node
        for node_id in range(num_nodes):
            processed["vector_stats"]["0"]["node_stats"][str(node_id)] = {
                "outgoingDataRate:vector": {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0},
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
                events_per_node = len(events) // num_nodes
                for node_id in range(num_nodes):
                    node_events = events[node_id::num_nodes]
                    if node_events:
                        mean = sum(node_events) / len(node_events)
                        min_val = min(node_events)
                        max_val = max(node_events)
                        
                        stats = processed["vector_stats"]["0"]["node_stats"][str(node_id)]
                        
                        # Update various metrics based on event rate
                        stats["outgoingDataRate:vector"].update({
                            "count": len(node_events),
                            "mean": mean,
                            "min": min_val,
                            "max": max_val
                        })
                        
                        # Scale queue length based on event rate
                        stats["queueLength:vector"].update({
                            "count": len(node_events),
                            "mean": mean / num_nodes,
                            "min": min_val / num_nodes,
                            "max": max_val / num_nodes
                        })
                        
                        # Transmission state based on event presence
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
        
        return processed
    
    def run_interactive_processing(self):
        """Interactive data processing menu"""
        while True:
            print("\n⚙️  Data Processing Menu")
            print("=" * 25)
            print("1. 🔄 Process Experiment Data")
            print("2. 📋 Show Processing Status")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect option (0-2): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.process_experiment_data()
            elif choice == "2":
                self.show_available_experiments()
            else:
                print("❌ Invalid choice")
                
            if choice != "0":
                input("\n📌 Press Enter to continue...")
                # Refresh experiment list
                self.available_experiments = self._scan_available_experiments()