#!/usr/bin/env python3
"""
Results Management Module
Interactive management of FLoRa experiment results
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

class ResultsManager:
    def __init__(self, experiments_dir):
        self.experiments_dir = Path(experiments_dir)
        self.available_experiments = self._scan_experiments()
        
    def _scan_experiments(self):
        """Scan for available experiments"""
        experiments = []
        if self.experiments_dir.exists():
            for exp_dir in self.experiments_dir.iterdir():
                if (exp_dir.is_dir() and 
                    exp_dir.name.startswith('experiment_')):
                    
                    # Get experiment info
                    size = self._get_directory_size(exp_dir)
                    modified = datetime.fromtimestamp(exp_dir.stat().st_mtime)
                    
                    # Count configurations
                    results_dir = exp_dir / "results"
                    config_count = 0
                    if results_dir.exists():
                        config_count = len([d for d in results_dir.iterdir() if d.is_dir()])
                    
                    # Read experiment info if available
                    info_file = exp_dir / "experiment_info.json"
                    description = ""
                    if info_file.exists():
                        try:
                            with open(info_file, 'r') as f:
                                info = json.load(f)
                            description = info.get('description', '')
                        except:
                            pass
                    
                    experiments.append({
                        'name': exp_dir.name,
                        'path': exp_dir,
                        'size_mb': size / (1024 * 1024),
                        'modified': modified,
                        'config_count': config_count,
                        'description': description
                    })
        
        return sorted(experiments, key=lambda x: x['modified'], reverse=True)
    
    def _get_directory_size(self, directory):
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError):
            pass
        return total_size
    
    def show_experiments_overview(self):
        """Display overview of all experiments"""
        print("\n🗂️  Experiments Overview:")
        print("-" * 80)
        
        if not self.available_experiments:
            print("❌ No experiments found")
            return
            
        print(f"{'#':<3} {'Name':<30} {'Size (MB)':<10} {'Configs':<8} {'Modified':<12}")
        print("-" * 80)
        
        for i, exp in enumerate(self.available_experiments, 1):
            modified_str = exp['modified'].strftime("%m-%d %H:%M")
            
            print(f"{i:<3} {exp['name']:<30} {exp['size_mb']:<10.1f} "
                  f"{exp['config_count']:<8} {modified_str:<12}")
            
            if exp['description']:
                desc_short = exp['description'][:60] + "..." if len(exp['description']) > 60 else exp['description']
                print(f"    📝 {desc_short}")
        
        total_size = sum(e['size_mb'] for e in self.available_experiments)
        total_configs = sum(e['config_count'] for e in self.available_experiments)
        print("-" * 80)
        print(f"Total: {len(self.available_experiments)} experiments, {total_configs} configurations, {total_size:.1f} MB")
    
    def delete_experiments(self):
        """Delete selected experiments"""
        self.show_experiments_overview()
        
        if not self.available_experiments:
            return
            
        print("\nSelect experiments to delete (comma-separated numbers, or 'all'):")
        print("⚠️  WARNING: This action cannot be undone!")
        selection = input("Selection: ").strip()
        
        if not selection:
            print("❌ No selection made")
            return
            
        if selection.lower() == 'all':
            experiments_to_delete = self.available_experiments
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                experiments_to_delete = [self.available_experiments[i] for i in indices 
                                       if 0 <= i < len(self.available_experiments)]
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return
        
        if not experiments_to_delete:
            print("❌ No valid experiments selected")
            return
            
        # Show what will be deleted
        total_size = sum(e['size_mb'] for e in experiments_to_delete)
        total_configs = sum(e['config_count'] for e in experiments_to_delete)
        print(f"\nWill delete {len(experiments_to_delete)} experiments ({total_configs} configs, {total_size:.1f} MB):")
        for exp in experiments_to_delete:
            print(f"  - {exp['name']} ({exp['config_count']} configs)")
        
        confirm = input(f"\nAre you sure? Type 'DELETE' to confirm: ").strip()
        
        if confirm == 'DELETE':
            deleted_count = 0
            for exp in experiments_to_delete:
                try:
                    shutil.rmtree(exp['path'])
                    deleted_count += 1
                    print(f"✅ Deleted: {exp['name']}")
                except OSError as e:
                    print(f"❌ Failed to delete {exp['name']}: {e}")
            
            print(f"\n✅ Successfully deleted {deleted_count}/{len(experiments_to_delete)} experiments")
            # Refresh the experiments list
            self.available_experiments = self._scan_experiments()
        else:
            print("❌ Deletion cancelled")
    
    def archive_old_experiments(self):
        """Archive old experiments"""
        print("\n📦 Archive Old Experiments")
        print("-" * 30)
        
        # Find experiments older than specified days
        days_old = input("Archive experiments older than how many days? [default: 30]: ").strip()
        try:
            days_threshold = int(days_old) if days_old else 30
        except ValueError:
            print("❌ Invalid number of days")
            return
        
        cutoff_date = datetime.now().timestamp() - (days_threshold * 24 * 60 * 60)
        old_experiments = [e for e in self.available_experiments 
                          if e['modified'].timestamp() < cutoff_date]
        
        if not old_experiments:
            print(f"✅ No experiments older than {days_threshold} days found")
            return
        
        print(f"\nFound {len(old_experiments)} experiments older than {days_threshold} days:")
        for exp in old_experiments:
            age_days = (datetime.now() - exp['modified']).days
            print(f"  - {exp['name']} ({age_days} days old, {exp['size_mb']:.1f} MB)")
        
        # Create archive directory
        archive_dir = self.experiments_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        confirm = input(f"\nArchive these {len(old_experiments)} experiments? (y/N): ").strip().lower()
        
        if confirm == 'y':
            archived_count = 0
            for exp in old_experiments:
                try:
                    archive_path = archive_dir / exp['name']
                    shutil.move(str(exp['path']), str(archive_path))
                    archived_count += 1
                    print(f"📦 Archived: {exp['name']}")
                except OSError as e:
                    print(f"❌ Failed to archive {exp['name']}: {e}")
            
            print(f"\n✅ Successfully archived {archived_count}/{len(old_experiments)} experiments")
            # Refresh the experiments list
            self.available_experiments = self._scan_experiments()
        else:
            print("❌ Archiving cancelled")
    
    def backup_experiments(self):
        """Create backup of important experiments"""
        print("\n💾 Backup Experiments")
        print("-" * 22)
        
        self.show_experiments_overview()
        
        if not self.available_experiments:
            return
        
        selection = input(f"\nSelect experiments to backup (comma-separated numbers, or 'all'): ").strip()
        
        if selection.lower() == 'all':
            experiments_to_backup = self.available_experiments
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                experiments_to_backup = [self.available_experiments[i] for i in indices 
                                       if 0 <= i < len(self.available_experiments)]
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return
        
        if not experiments_to_backup:
            print("❌ No valid experiments selected")
            return
        
        # Get backup location
        backup_location = input("Enter backup directory path [default: ./backup]: ").strip()
        backup_dir = Path(backup_location) if backup_location else Path("./backup")
        
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"❌ Cannot create backup directory: {e}")
            return
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = backup_dir / f"flora_experiments_backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        print(f"\n💾 Creating backup in: {backup_subdir}")
        
        # Backup options
        print("Backup options:")
        print("1. Full backup (all data)")
        print("2. Processed data only (configs + JSON results)")
        print("3. Configs only")
        
        backup_choice = input("Select backup type (1-3): ").strip()
        
        backed_up_count = 0
        for exp in experiments_to_backup:
            try:
                backup_path = backup_subdir / exp['name']
                backup_path.mkdir(exist_ok=True)
                
                if backup_choice == "1":  # Full backup
                    shutil.copytree(exp['path'], backup_path, dirs_exist_ok=True)
                elif backup_choice == "2":  # Processed data only
                    # Copy configs
                    configs_src = exp['path'] / "configs"
                    if configs_src.exists():
                        shutil.copytree(configs_src, backup_path / "configs", dirs_exist_ok=True)
                    
                    # Copy processed results (JSON files)
                    results_src = exp['path'] / "results"
                    if results_src.exists():
                        results_backup = backup_path / "results"
                        results_backup.mkdir(exist_ok=True)
                        
                        for config_dir in results_src.iterdir():
                            if config_dir.is_dir():
                                config_backup = results_backup / config_dir.name
                                config_backup.mkdir(exist_ok=True)
                                
                                # Copy JSON files
                                for json_file in config_dir.glob("*.json"):
                                    shutil.copy2(json_file, config_backup)
                    
                    # Copy experiment info
                    info_file = exp['path'] / "experiment_info.json"
                    if info_file.exists():
                        shutil.copy2(info_file, backup_path)
                        
                elif backup_choice == "3":  # Configs only
                    configs_src = exp['path'] / "configs"
                    if configs_src.exists():
                        shutil.copytree(configs_src, backup_path / "configs", dirs_exist_ok=True)
                    
                    info_file = exp['path'] / "experiment_info.json"
                    if info_file.exists():
                        shutil.copy2(info_file, backup_path)
                
                backed_up_count += 1
                print(f"💾 Backed up: {exp['name']}")
                
            except OSError as e:
                print(f"❌ Failed to backup {exp['name']}: {e}")
        
        print(f"\n✅ Successfully backed up {backed_up_count}/{len(experiments_to_backup)} experiments")
        print(f"📁 Backup location: {backup_subdir}")
    
    def cleanup_empty_experiments(self):
        """Clean up empty or incomplete experiments"""
        print("\n🧹 Cleaning Up Empty Experiments")
        print("-" * 35)
        
        empty_experiments = []
        for exp in self.available_experiments:
            if exp['config_count'] == 0:
                empty_experiments.append(exp)
        
        if not empty_experiments:
            print("✅ No empty experiments found")
            return
        
        print(f"Found {len(empty_experiments)} empty experiments:")
        for exp in empty_experiments:
            print(f"  - {exp['name']}")
        
        confirm = input(f"\nDelete these {len(empty_experiments)} empty experiments? (y/N): ").strip().lower()
        
        if confirm == 'y':
            deleted_count = 0
            for exp in empty_experiments:
                try:
                    shutil.rmtree(exp['path'])
                    deleted_count += 1
                    print(f"🗑️  Deleted: {exp['name']}")
                except OSError as e:
                    print(f"❌ Failed to delete {exp['name']}: {e}")
            
            print(f"\n✅ Successfully deleted {deleted_count}/{len(empty_experiments)} empty experiments")
            # Refresh the experiments list
            self.available_experiments = self._scan_experiments()
        else:
            print("❌ Cleanup cancelled")
    
    def experiment_details(self):
        """Show detailed information about an experiment"""
        self.show_experiments_overview()
        
        if not self.available_experiments:
            return
            
        choice = input(f"\nSelect experiment for details (1-{len(self.available_experiments)}): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.available_experiments):
                exp = self.available_experiments[idx]
                self._show_experiment_details(exp)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Please enter a valid number")
    
    def _show_experiment_details(self, experiment):
        """Show detailed information about a specific experiment"""
        print(f"\n📊 Experiment Details: {experiment['name']}")
        print("=" * 60)
        
        print(f"Size: {experiment['size_mb']:.1f} MB")
        print(f"Modified: {experiment['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configurations: {experiment['config_count']}")
        
        if experiment['description']:
            print(f"Description: {experiment['description']}")
        
        # Show configurations with details
        results_dir = experiment['path'] / "results"
        if results_dir.exists():
            print(f"\n📁 Configurations:")
            for config_dir in results_dir.iterdir():
                if config_dir.is_dir():
                    # Check data availability
                    has_vectors = any(config_dir.glob("*.vec"))
                    has_scalars = any(config_dir.glob("*.sca"))
                    has_processed = (config_dir / "aggregated_vector_stats.json").exists()
                    
                    status = []
                    if has_vectors:
                        status.append("VEC")
                    if has_scalars:
                        status.append("SCA")
                    if has_processed:
                        status.append("JSON")
                    
                    status_str = f"[{'/'.join(status)}]" if status else "[EMPTY]"
                    size = self._get_directory_size(config_dir) / (1024 * 1024)
                    
                    print(f"  📊 {config_dir.name:<25} {status_str:<15} ({size:.1f} MB)")
        
        # Show analysis and exports if they exist
        analysis_dir = experiment['path'] / "analysis"
        if analysis_dir.exists():
            print(f"\n📈 Analysis available:")
            for analysis_type in analysis_dir.iterdir():
                if analysis_type.is_dir():
                    print(f"  📊 {analysis_type.name}")
        
        exports_dir = experiment['path'] / "exports"
        if exports_dir.exists():
            print(f"\n💾 Exports available:")
            for export_file in exports_dir.iterdir():
                if export_file.is_file():
                    size = export_file.stat().st_size / 1024
                    print(f"  📄 {export_file.name} ({size:.1f} KB)")
    
    def run_interactive_management(self):
        """Interactive experiment management menu"""
        while True:
            print("\n🗂️  Experiment Management")
            print("=" * 28)
            print("1. 📋 Show Experiments Overview")
            print("2. 🔍 Experiment Details")
            print("3. 🗑️  Delete Experiments")
            print("4. 📦 Archive Old Experiments")
            print("5. 💾 Backup Experiments")
            print("6. 🧹 Clean Empty Experiments")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect option (0-6): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.show_experiments_overview()
            elif choice == "2":
                self.experiment_details()
            elif choice == "3":
                self.delete_experiments()
            elif choice == "4":
                self.archive_old_experiments()
            elif choice == "5":
                self.backup_experiments()
            elif choice == "6":
                self.cleanup_empty_experiments()
            else:
                print("❌ Invalid choice")
                
            if choice != "0":
                input("\n📌 Press Enter to continue...")