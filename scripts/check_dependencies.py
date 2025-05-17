#!/usr/bin/env python3
"""
Dependency checking script for Nuki Smart Lock Notification System.
Verifies that all required packages are installed and at the correct versions.
"""
import os
import sys
import subprocess
import argparse
import pkg_resources
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dependency_checker')

def parse_requirements(file_path):
    """
    Parse a requirements file into a set of dependency specifications.
    
    Args:
        file_path (str): Path to the requirements file
        
    Returns:
        list: List of requirement specifications
    """
    requirements = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-r'):
                requirements.append(line)
    return requirements

def check_dependencies(requirements_list):
    """
    Check if all dependencies are installed and at the correct versions.
    
    Args:
        requirements_list (list): List of requirement specifications
        
    Returns:
        tuple: (list of missing dependencies, list of incorrect versions)
    """
    missing = []
    incorrect_version = []
    
    for req_line in requirements_list:
        try:
            req = pkg_resources.Requirement.parse(req_line)
            pkg_name = req.project_name
            
            # Check if package is installed
            try:
                dist = pkg_resources.get_distribution(pkg_name)
                
                # Check version
                if dist.version not in req:
                    incorrect_version.append((pkg_name, dist.version, str(req)))
            except pkg_resources.DistributionNotFound:
                missing.append(pkg_name)
        except ValueError as e:
            logger.warning(f"Skipping invalid requirement: {req_line} - {e}")
    
    return missing, incorrect_version

def check_requirements_file(file_path):
    """
    Check all dependencies in a requirements file.
    
    Args:
        file_path (str): Path to the requirements file
        
    Returns:
        bool: True if all dependencies are satisfied, False otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"Requirements file not found: {file_path}")
        return False
    
    logger.info(f"Checking dependencies in: {file_path}")
    requirements = parse_requirements(file_path)
    
    # Get referenced requirements files
    referenced_files = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('-r '):
                ref_file = line[3:].strip()
                # Get absolute path of referenced file
                if not os.path.isabs(ref_file):
                    ref_file = os.path.join(os.path.dirname(file_path), ref_file)
                referenced_files.append(ref_file)
    
    # Check all referenced files first
    all_satisfied = True
    for ref_file in referenced_files:
        if not check_requirements_file(ref_file):
            all_satisfied = False
    
    # Check this file's requirements
    missing, incorrect_version = check_dependencies(requirements)
    
    if missing:
        logger.error("Missing dependencies:")
        for pkg in missing:
            logger.error(f"  - {pkg}")
        all_satisfied = False
    
    if incorrect_version:
        logger.error("Incorrect versions:")
        for pkg, current, required in incorrect_version:
            logger.error(f"  - {pkg}: found {current}, required {required}")
        all_satisfied = False
    
    if all_satisfied:
        logger.info(f"All dependencies in {file_path} are satisfied")
    
    return all_satisfied

def install_missing_dependencies(requirements_file, upgrade=False):
    """
    Install missing dependencies using pip.
    
    Args:
        requirements_file (str): Path to the requirements file
        upgrade (bool): Whether to upgrade existing packages
        
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        if upgrade:
            cmd.insert(4, "--upgrade")
        
        logger.info(f"Installing dependencies from {requirements_file}")
        subprocess.check_call(cmd)
        
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing dependencies: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Nuki Smart Lock Notification System Dependency Checker')
    parser.add_argument('--requirements', '-r', default='requirements.txt', 
                        help='Path to the requirements file to check (default: requirements.txt)')
    parser.add_argument('--install', '-i', action='store_true', 
                        help='Install missing dependencies')
    parser.add_argument('--upgrade', '-u', action='store_true',
                        help='Upgrade existing packages to required versions')
    parser.add_argument('--check-all', '-a', action='store_true',
                        help='Check all requirements files (core, web, dev)')
    args = parser.parse_args()
    
    # Get the base directory
    base_dir = Path(__file__).parent.parent
    
    if args.check_all:
        # Check all requirements files
        req_files = [
            os.path.join(base_dir, 'requirements.txt'),
            os.path.join(base_dir, 'requirements-web.txt'),
            os.path.join(base_dir, 'requirements-dev.txt')
        ]
        
        all_satisfied = True
        for req_file in req_files:
            logger.info(f"\nChecking {os.path.basename(req_file)}:")
            satisfied = check_requirements_file(req_file)
            
            if not satisfied and args.install:
                install_missing_dependencies(req_file, args.upgrade)
                satisfied = check_requirements_file(req_file)
            
            all_satisfied = all_satisfied and satisfied
            print()  # Add a blank line for readability
        
        if all_satisfied:
            logger.info("All dependency checks passed")
            return 0
        else:
            logger.error("Some dependency checks failed")
            return 1
    else:
        # Check a single requirements file
        req_file = os.path.join(base_dir, args.requirements) if not os.path.isabs(args.requirements) else args.requirements
        satisfied = check_requirements_file(req_file)
        
        if not satisfied and args.install:
            install_missing_dependencies(req_file, args.upgrade)
            satisfied = check_requirements_file(req_file)
        
        if satisfied:
            logger.info("Dependency check passed")
            return 0
        else:
            logger.error("Dependency check failed")
            return 1

if __name__ == "__main__":
    sys.exit(main())
