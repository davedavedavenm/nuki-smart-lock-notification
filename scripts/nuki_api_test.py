#!/usr/bin/env python3
import os
import sys
import requests
import json
import configparser

# Get base directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load credentials
credentials_path = os.path.join(base_dir, "config", "credentials.ini")
config = configparser.ConfigParser()

if not os.path.exists(credentials_path):
    print(f"Error: Credentials file not found at {credentials_path}")
    sys.exit(1)

config.read(credentials_path)
API_TOKEN = config.get('Nuki', 'api_token', fallback='')

if not API_TOKEN:
    print("Error: No API token found in credentials.ini")
    sys.exit(1)

# API settings
base_url = "https://api.nuki.io"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}

# Test 1: Get all smartlocks
print("=== Testing GET /smartlock ===")
response = requests.get(f"{base_url}/smartlock", headers=headers)
print(f"Response Status: {response.status_code}")

if response.status_code == 200:
    smartlocks = response.json()
    print(f"Found {len(smartlocks)} smartlocks:")
    for lock in smartlocks:
        lock_id = lock.get('smartlockId')
        lock_name = lock.get('name', 'Unknown')
        print(f"Lock: {lock_name}, ID: {lock_id}")
        
        # Test 2: Get logs for each lock
        print(f"\n=== Testing GET /smartlock/{lock_id}/log ===")
        log_response = requests.get(f"{base_url}/smartlock/{lock_id}/log", headers=headers)
        print(f"Response Status: {log_response.status_code}")
        
        if log_response.status_code == 200:
            logs = log_response.json()
            print(f"Successfully retrieved {len(logs)} log entries")
            if logs:
                print(f"Most recent activity: {logs[0].get('name', 'Unknown action')}")
        else:
            print(f"Error retrieving logs: {log_response.text}")
else:
    print(f"Error retrieving smartlocks: {response.text}")

# Test 3: Explicitly try the problematic smartlock ID
problematic_id = 18255246837
print(f"\n=== Testing GET /smartlock/{problematic_id}/log (Explicit ID) ===")
problem_response = requests.get(f"{base_url}/smartlock/{problematic_id}/log", headers=headers)
print(f"Response Status: {problem_response.status_code}")
print(f"Response: {problem_response.text}")

print("\n=== Testing Complete ===")
