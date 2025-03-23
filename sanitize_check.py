#!/usr/bin/env python3
"""
sanitize_check.py - Tool to check for potential sensitive information before committing to GitHub
"""
import os
import re
import glob
import sys

# Define patterns to look for
PATTERNS = [
    # API tokens
    r'api_token\s*=\s*(?!YOUR_NUKI_API_TOKEN)[A-Za-z0-9_\-\.]{10,}',
    r'Bearer\s+[A-Za-z0-9_\-\.]{10,}',
    # Telegram tokens
    r'bot_token\s*=\s*(?!YOUR_TELEGRAM_BOT_TOKEN)[0-9]{8,10}:[A-Za-z0-9_\-]{35,}',
    # Email credentials
    r'username\s*=\s*(?!your-email@example\.com)[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    r'password\s*=\s*(?!your-email-password).{8,}',
    # IP addresses
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    # Chat IDs
    r'chat_id\s*=\s*[0-9]{8,}',
    # Hardcoded paths to user's system
    r'C:\\Users\\Dave',
    r'/root/nukiweb',
    # Look for .ini and .json files that should be examples 
    r'credentials\.ini$',
    r'config\.ini$',
    r'users\.json$',
]

# Files and directories to ignore
IGNORE_PATHS = [
    '.git',
    'venv',
    'sanitize_check.py',
    '.gitignore',
    'config.ini.example',
    'credentials.ini.example',
    'users.json.example',
]

def should_ignore(path):
    """Determine if the path should be ignored"""
    for ignore_path in IGNORE_PATHS:
        if ignore_path in path:
            return True
    return False

def check_file(filepath):
    """Check a single file for sensitive information"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            content = f.read()
            line_num = 1
            issues = []
            
            for line in content.split('\n'):
                for pattern in PATTERNS:
                    if re.search(pattern, line):
                        # Check if it's an example file where the pattern is expected
                        if 'example' in filepath.lower():
                            continue
                        
                        issues.append((line_num, pattern, line.strip()))
                line_num += 1
                
            return issues
        except Exception as e:
            print(f"Error checking {filepath}: {e}")
            return []

def main():
    """Main function to check all files in the project"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    all_files = []
    issues_found = False
    
    # Find all files
    for root, dirs, files in os.walk(project_root):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
        
        for file in files:
            filepath = os.path.join(root, file)
            if not should_ignore(filepath) and os.path.isfile(filepath):
                all_files.append(filepath)
    
    print(f"Checking {len(all_files)} files for potential sensitive information...")
    
    for filepath in all_files:
        relative_path = os.path.relpath(filepath, project_root)
        issues = check_file(filepath)
        
        if issues:
            issues_found = True
            print(f"\n⚠️  Potential sensitive info in {relative_path}:")
            for line_num, pattern, line in issues:
                print(f"  Line {line_num}: {line}")
                print(f"  Matched pattern: {pattern}\n")
    
    if issues_found:
        print("\n⚠️  WARNING: Potential sensitive information found!")
        print("Please review the issues above before pushing to GitHub.")
        return 1
    else:
        print("\n✅ No potential sensitive information found!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
