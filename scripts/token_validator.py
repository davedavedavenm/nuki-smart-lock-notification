#!/usr/bin/env python3
"""
Nuki API Token Validator
A comprehensive tool to validate and diagnose Nuki API token issues.
"""

import os
import sys
import requests
import configparser
import json
import base64
import re

def header():
    print("\n=================================================")
    print("🔑 NUKI API TOKEN VALIDATOR & DIAGNOSTIC TOOL 🔍")
    print("=================================================\n")

def load_token_from_file(file_path):
    """Load token from credentials.ini file"""
    if not os.path.exists(file_path):
        print(f"❌ Error: Credentials file not found at {file_path}")
        return None
        
    try:
        config = configparser.ConfigParser()
        config.read(file_path)
        token = config.get('Nuki', 'api_token', fallback='')
        
        if not token:
            print("❌ Error: No API token found in credentials.ini")
            return None
            
        return token
    except Exception as e:
        print(f"❌ Error loading token: {e}")
        return None

def analyze_token_format(token):
    """Analyze the token format for common issues"""
    print("\n📋 TOKEN FORMAT ANALYSIS:")
    print("-" * 40)
    
    # Check token length
    token_length = len(token)
    print(f"Token length: {token_length} characters")
    
    if token_length < 20:
        print("⚠️ Warning: Token seems unusually short")
    elif token_length > 500:
        print("⚠️ Warning: Token seems unusually long")
    
    # Check for whitespace
    if token.strip() != token:
        print("❌ Error: Token contains leading or trailing whitespace")
        print(f"Raw token (with whitespace highlighted): '{token}'")
        print(f"Stripped token: '{token.strip()}'")
    
    # Check for invalid characters
    if not re.match(r'^[A-Za-z0-9\-_=\.]+$', token):
        print("⚠️ Warning: Token contains characters that may not be valid")
        print(f"Invalid characters: {[c for c in token if not re.match(r'[A-Za-z0-9\-_=\.]', c)]}")
    
    # Check if it's a JWT token (many APIs use this format)
    if re.match(r'^[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+$', token):
        print("ℹ️ Info: Token appears to be in JWT format")
        
        # Try to decode the JWT payload
        try:
            # Split the token into parts
            parts = token.split('.')
            
            # Parse the payload (middle part)
            payload_part = parts[1]
            
            # Add padding if needed
            padding = 4 - (len(payload_part) % 4)
            if padding < 4:
                payload_part += '=' * padding
            
            # Decode the payload
            payload = base64.b64decode(payload_part.translate(str.maketrans('-_', '+/')))
            payload_json = json.loads(payload)
            
            # Check for expiration
            if 'exp' in payload_json:
                import time
                exp_time = payload_json['exp']
                current_time = time.time()
                
                if exp_time < current_time:
                    print(f"❌ Error: Token is expired (expired at: {exp_time})")
                else:
                    print(f"✅ Token is valid until: {exp_time}")
                    
            # Check for scopes or permissions
            if 'scope' in payload_json:
                print(f"Scopes: {payload_json['scope']}")
                
                # Check for specific required permissions
                required_scopes = ['smartlock', 'account']
                missing_scopes = [scope for scope in required_scopes if scope not in payload_json['scope']]
                
                if missing_scopes:
                    print(f"❌ Error: Missing required scopes: {missing_scopes}")
        except Exception as e:
            print(f"Note: Could not decode JWT payload: {e}")
    
    return token.strip()  # Return token with whitespace removed

def test_endpoints(token):
    """Test various Nuki API endpoints with the token"""
    print("\n🌐 API ENDPOINT TESTS:")
    print("-" * 40)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    endpoints = [
        {"name": "Account", "url": "https://api.nuki.io/account", "success_code": 200},
        {"name": "Smartlock", "url": "https://api.nuki.io/smartlock", "success_code": 200},
        {"name": "Auth", "url": "https://api.nuki.io/smartlock/auth", "success_code": 200},
    ]
    
    overall_success = True
    success_count = 0
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint['name']} endpoint ({endpoint['url']})...")
            response = requests.get(
                endpoint['url'],
                headers=headers,
                timeout=10
            )
            
            status_code = response.status_code
            
            if status_code == endpoint['success_code']:
                print(f"✅ {endpoint['name']} endpoint: SUCCESS (Status {status_code})")
                success_count += 1
                
                # Additional details for successful responses
                if endpoint['name'] == 'Smartlock':
                    try:
                        data = response.json()
                        lock_count = len(data)
                        print(f"   Found {lock_count} smartlocks in your account")
                        
                        if lock_count > 0:
                            # Try the logs endpoint with the first smartlock ID
                            smartlock_id = data[0].get('smartlockId')
                            print(f"\nTesting logs endpoint for smartlock ID: {smartlock_id}...")
                            
                            log_response = requests.get(
                                f"https://api.nuki.io/smartlock/{smartlock_id}/log",
                                headers=headers,
                                timeout=10
                            )
                            
                            if log_response.status_code == 200:
                                print(f"✅ Logs endpoint: SUCCESS (Status {log_response.status_code})")
                                logs = log_response.json()
                                print(f"   Retrieved {len(logs)} log entries")
                            else:
                                print(f"❌ Logs endpoint: FAILED (Status {log_response.status_code})")
                                print(f"   Error: {log_response.text}")
                                overall_success = False
                    except Exception as json_e:
                        print(f"   Error parsing JSON response: {json_e}")
            elif status_code == 401:
                print(f"❌ {endpoint['name']} endpoint: FAILED (Status 401 Unauthorized)")
                print(f"   Error: {response.text}")
                overall_success = False
            else:
                print(f"⚠️ {endpoint['name']} endpoint: WARNING (Status {status_code})")
                print(f"   Response: {response.text}")
                overall_success = overall_success and (status_code < 400)
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint['name']} endpoint: FAILED (Connection error)")
            overall_success = False
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint['name']} endpoint: FAILED (Timeout)")
            overall_success = False
        except Exception as e:
            print(f"❌ {endpoint['name']} endpoint: FAILED (Error: {e})")
            overall_success = False
    
    return {
        "overall_success": overall_success,
        "success_count": success_count,
        "total_endpoints": len(endpoints)
    }

def print_recommendations(format_analysis_result, endpoint_tests_result):
    """Print recommendations based on the test results"""
    print("\n🔍 DIAGNOSTIC RESULTS & RECOMMENDATIONS:")
    print("-" * 60)
    
    if endpoint_tests_result["overall_success"]:
        print("✅ OVERALL STATUS: TOKEN IS VALID AND WORKING")
        
        if endpoint_tests_result["success_count"] == endpoint_tests_result["total_endpoints"]:
            print("All API endpoints are accessible with this token")
        else:
            print(f"Some API endpoints ({endpoint_tests_result['success_count']}/{endpoint_tests_result['total_endpoints']}) are accessible with this token")
            print("This partial access might be due to permission limitations")
    else:
        print("❌ OVERALL STATUS: TOKEN IS NOT WORKING CORRECTLY")
        
        # Give more specific recommendations based on the results
        if endpoint_tests_result["success_count"] == 0:
            print("\nRECOMMENDED ACTIONS:")
            print("1. Generate a new token in the Nuki Web portal (https://web.nuki.io/)")
            print("2. When generating the token, ensure ALL permissions are checked, especially:")
            print("   - 'View smartlocks'")
            print("   - 'View activity logs and get log notifications'")
            print("3. Copy the token carefully (use copy button if available)")
            print("4. Update credentials.ini file with the new token:")
            print("   - SSH into the Raspberry Pi")
            print("   - Edit the file with 'nano ~/nukiweb/config/credentials.ini'")
            print("   - Replace the token value with the new one")
            print("   - Make sure there are no extra spaces or characters")
            print("5. Restart the Docker containers:")
            print("   - Run 'cd ~/nukiweb && docker compose down && docker compose up -d'")
        else:
            print("\nRECOMMENDED ACTIONS:")
            print("1. Generate a new token in the Nuki Web portal with ALL permissions")
            print("2. Update credentials.ini file with the new token")
            print("3. Restart the Docker containers")
    
    print("\n📝 ADDITIONAL NOTES:")
    print("- Tokens may be account-specific or device-specific")
    print("- If you have multiple Nuki accounts, ensure you're using the correct one")
    print("- Check if your IP address is blocked or restricted in the Nuki Web portal")
    print("- Consider revoking old tokens to avoid confusion")

def main():
    """Main function"""
    header()
    
    # Determine the credentials file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if CONFIG_DIR environment variable is set (for Docker)
    config_dir = os.environ.get('CONFIG_DIR', os.path.join(base_dir, 'config'))
    credentials_path = os.path.join(config_dir, 'credentials.ini')
    
    print(f"Looking for credentials file at: {credentials_path}")
    
    # Load token from file
    token = load_token_from_file(credentials_path)
    
    if not token:
        print("\nNo token found in credentials file.")
        manual_token = input("Would you like to enter a token manually? (y/n): ").strip().lower()
        
        if manual_token == 'y':
            token = input("Enter your Nuki API token: ").strip()
        else:
            sys.exit(1)
    
    # Analyze token format
    cleaned_token = analyze_token_format(token)
    
    # Confirm with user
    print("\nWould you like to test this token against the Nuki API endpoints?")
    confirm = input("This will send requests to the Nuki API (y/n): ").strip().lower()
    
    if confirm == 'y':
        # Test endpoints
        endpoint_tests_result = test_endpoints(cleaned_token)
        
        # Print recommendations
        print_recommendations(cleaned_token, endpoint_tests_result)
    else:
        print("\nEndpoint tests skipped by user.")

if __name__ == "__main__":
    main()
