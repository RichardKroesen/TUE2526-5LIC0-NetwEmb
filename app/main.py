#!/usr/bin/env python3
"""
FLoRa Simulation Manager
Main interface for managing FLoRa simulations and experiments
"""

# ---------------- GLOBAL CONFIG ----------------
# Paths to Dependencies
OMNET_EXECUTABLE = "/home/richard/omnetpp-6.2.0/bin/opp_run"
FLORA_ROOT = "/home/richard/1-Dev/5LIC0-EmbNetw"
INET_ROOT = "/home/richard/omnetpp-6.2.0/samples/inet4.4"

# Directory paths
SIMULATIONS_DIR = "/home/richard/1-Dev/5LIC0-EmbNetw/simulations"
EXPERIMENTS_DIR = "/home/richard/1-Dev/5LIC0-EmbNetw/experiments"

# Simulation general settings
BASE_INI = "template_base.ini"
MAX_PARALLEL = 8
CHUNK_SIZE_MB = 512  # for data aggregation

# ----------------------------------------------

# ---------------- IMPORTS ---------------------
from simulation_config import SimulationConfig
from data_processor import DataProcessor
from data_analyzer import DataAnalyzer
from results_manager import ResultsManager

# ---------------- MAIN ENTRY ------------------
def main():
    # Initialize modules with global config
    sim_config = SimulationConfig(SIMULATIONS_DIR, EXPERIMENTS_DIR, OMNET_EXECUTABLE, FLORA_ROOT, INET_ROOT)
    data_analyzer = DataAnalyzer(EXPERIMENTS_DIR)
    results_manager = ResultsManager(EXPERIMENTS_DIR)
    
    print("WLAM FLoRa Simulation Manager")
    print("=" * 30)
    print(f"🏠 Flora Root: {FLORA_ROOT}")
    print(f"🔧 OMNeT++: {OMNET_EXECUTABLE}")
    print(f"📂 Experiments: {EXPERIMENTS_DIR}")
    
    while True:
        print("\n📋 Main Menu:")
        print("1. ⚙️  Configure & Run Simulations")
        print("2. 📊 Analyze & Visualize Results")
        print("3. 🗂️  Manage Experiments")
        print("4. ❓ Help & Status")
        print("0. 🚪 Exit")
        
        choice = input("\nSelect option (0-4): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            sim_config.run_interactive_config()
        elif choice == "2":
            data_analyzer.run_interactive_analysis()
        elif choice == "3":
            results_manager.run_interactive_management()
        elif choice == "4":
            show_help_and_status(SIMULATIONS_DIR, EXPERIMENTS_DIR)
        else:
            print("❌ Invalid choice")

def show_help_and_status(simulations_dir, experiments_dir):
    """Show help information and system status"""
    print("\n❓ FLoRa Simulation Manager Help")
    print("=" * 35)
    
    print("\n📚 Quick Guide:")
    print("1. Configure & Run: Set up experiment parameters and run simulations")
    print("2. Process Data: Convert raw simulation output to analyzable format")
    print("3. Analyze Results: Generate visualizations and performance analysis")
    print("4. Manage: Clean up, backup, and organize experiment data")
    
    print("\n📁 Directory Structure:")
    print(f"Simulations: {simulations_dir}")
    print(f"Experiments: {experiments_dir}")
    
    print("\n🔄 Workflow:")
    print("1. Run simulations → generates .vec/.sca files")
    print("2. Process data → creates .json files")
    print("3. Analyze data → generates plots and reports")
    
    print("\n💡 Tips:")
    print("• Each experiment gets a timestamped folder")
    print("• Configuration files are copied to experiments for reproducibility")
    print("• Use 'Process Data' before 'Analyze Results'")
    print("• Regular cleanup helps manage disk space")

if __name__ == "__main__":
    main()