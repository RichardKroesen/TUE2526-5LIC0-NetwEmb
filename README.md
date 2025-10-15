# Networked Embedded Systems Project (5LIC0)
This is a repository of our course Netwoked Embedded Systems project (5LIC0) at Technical University of Eindhoven. The course is scoped perticularly around Wireless Sensor Networks. 

## Background
The project focuses on the design of a Wireless Sensor Network (WSN) for Wildlife Area Monitoring (WLAM). 
The goal of the network/application is to collect environmental data within a wildlife reserve to support ecological investigation.
This could be data of temperature, humidity, wildlife activity, and nitrogen dioxide (NO2) levels, all of which provide valuable insights into animal health, habitat quality, and potential environmental stressors. As the nodes operates in remote areas, low energy consumption is essential for long-term monitoring.

The project explores the technical challenges of a WSN within wetland environment.

## Research 
The network design follows a controlled experimental approach using simulation-based testing with systematic parameter variation.
The decision is made to a utilize simulation platform for initial network design verification. The FLoRa (Framework for LoRa) will be used for end-to-end simulation of LoRa networks.

# Experimental Setup 

This section provides usage instructions of the experimental setup that is used for simulation environment creation and doing experiments in a structured manner. The simulation setup is LoRa-based Wireless Sensor Networks (WSNs) using the FLoRa framework and Python scripts for data collection automation, analysis, and visualization.

> [!WARNING]  

RUNNING SIMULATIONS MAY TAKE A LONG TIME AND CONSUME SIGNIFICANT COMPUTATIONAL RESOURCES. ENSURE YOUR YOU HAVE ENOUGH DISK SPACE AND BEFORE INITIATING TIME-SENSITIVE EXPERIMENTS. 
As an example running 1 day of experiment with 100 nodes takes 2.3 GB of disk space and around 10 minutes of processing (estimation not verified, since I run multilple experiments in parallel). Keep this in mind when starting a longer experiment configuration. 

## 1) Building and Running FLoRa Simulations

FLoRa (Framework for LoRa) is used for simulating LoRa networks. To build and run FLoRa:

### Prerequisites

- OMNET++ 6.2.0 (or at least 6.0, only verified on 6.2.0)
- INET 4.4.0
- FLoRa 1.1.0 (This repository contains modified FLoRa source code in the `src/` directory)

### Build Steps

1. **Install OMNeT++:**
	- Download and install OMNeT++ from https://omnetpp.org/download/
	- Follow the OMNeT++ installation instructions for your platform.

2. **Clone FLoRa:**
	- Clone this repository:
      ```bash
        git clone https://github.com/RichardKroesen/TUE2526-5LIC0-NetwEmb.git
        ``` 

3. **Build FLoRa:**
	- Navigate to the FLoRa source directory (e.g., `src/`):
	  ```bash
	  cd src
	  make
	  ```
	- Ensure all dependencies are met (INET, etc.).

4. **Test Run Simulation:**
	- Use OMNeT++ IDE or command line to run simulations:
	  ```bash
	  ./run_flora -u Cmdenv -c <ConfigName> -n .:../simulations
	  ```
	- Simulation results will be saved in the specified output directories.

---
## 2) Data Analysis & Visualization Usage

This repository includes Python scripts for analyzing and visualizing results from FLoRa-based wireless sensor network simulations.

### Prerequisites

- Python 3.8+
- Install required packages from requirements.txt:
  ```bash
  pip install -r requirements.txt
  ```

### How to Run Analysis

1. **Navigate to the scripts folder:**
	```bash
	cd app
	```

2. **Run the main analysis script:**
	```bash
	python main.py
	```

3. **Interactive Menu:**
The script will present an interactive menu:
    1. Run Experiment: Start a new experiment, the prompt will guide you through setting up parameters and configurations.
    2. Analyze Experiment: Select and analyze a specific experiment. Follow the prompts to choose analysis options, and export of data into different formats.
    3. Show Available Experiments: List all detected experiments and configurations.
    4. Back to Main Menu: Exit the analysis tool.

4. **Features:**
	- Visualize metrics for individual configurations.
	- Compare all configurations in an experiment.
	- Generate Packet Delivery Rate (PDR) analysis.
	- Export experiment data (CSV, JSON, summary report).

### Folder Structure

- `experiments/` — Contains experiment results of the simulations with dated time stamp. Within each experiment run each simulation run with its configurations, and intermediated processed data (processed_data.json) are found.
- `scripts/` — Contains manual analysis and processing scripts, note that some of these are already integrated in the interactive app (in a generative way).
- `simulations/` — Contains simulation configuration files and temporary results, you should only manually change the template_base.ini or config files like energy.xml.

### Example Usage

After running `python main.py`, follow the prompts to select experiments and analysis options. Plots and exported data will be saved in the corresponding experiment folders (e.g., `analysis/`, `exports/`).

---
## Adding Custom Analysis Scripts

You can add your own Python scripts for post-processing or custom analysis. All processed results are stored as JSON files in the experiment folders.
