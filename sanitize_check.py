#!/usr/bin/env python3
"""
sanitize_check.py - Tool to check for potential sensitive information before committing to GitHub
"""
import os
import re
import glob
import sys

# Ensure output works on all consoles (e.g. Windows cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Define patterns to look for
PATTERNS = [
    # API tokens (placeholder and test-fixture values allowed)
    r'api_token\s*=\s*(?!YOUR_NUKI_API_TOKEN\b|test_token\b|\b)[A-Za-z0-9_\-\.]{10,}',
    r'Bearer\s+(?!YOUR|test_)[A-Za-z0-9_\-\.]{10,}',
    # Telegram tokens
    r'bot_token\s*=\s*(?!YOUR_TELEGRAM_BOT_TOKEN\b|test_bot_token\b)[0-9]{8,10}:[A-Za-z0-9_\-]{35,}',
    # Email credentials (placeholders and test fixtures allowed)
    r'username\s*=\s*(?!your-|test@example\.com\b)[a-zA-Z0-9_.+-]+@(?!example\.com\b|example\.org\b)[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    r'password\s*=\s*(?!your-|test_)["\']?[A-Za-z0-9_!@#$%^&*+\-]{8,}["\']?\s*$',
    # Public IP addresses (private/loopback ranges ignored — not sensitive)
    r'\b(?!127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b',
    # Chat IDs (test fixture value allowed)
    r'chat_id\s*=\s*(?!123456789\b)[0-9]{8,}',
    # Hardcoded paths to a user's machine or old deployment layout
    r'C:\\Users\\[A-Za-z]+',
    r'/root/nukiweb',
]

# Files and directories to ignore
IGNORE_PATHS = [
    '.git',
    'venv',
    '.venv',
    '__pycache__',
    '.pytest_cache',
    'sanitize_check.py',
    '.gitignore',
    'config.ini.example',
    'credentials.ini.example',
    'users.json.example',
]

# Skip binary/non-source extensions entirely
SOURCE_EXTENSIONS = {
    '.py', '.sh', '.bat', '.yml', '.yaml', '.md', '.txt', '.ini',
    '.json', '.example', '.service', '.cfg', '.toml', '.env', '',
}

def should_ignore(path):
    """Determine if the path should be ignored"""
    for ignore_path in IGNORE_PATHS:
        if ignore_path in path:
            return True
    return False

def list_files(project_root):
    """Enumerate git-tracked files when possible; fall back to a directory walk."""
    if os.path.isdir(os.path.join(project_root, '.git')):
        result = os.popen('git -C "%s" ls-files' % project_root)
        tracked = [line.strip() for line in result.read().splitlines() if line.strip()]
        if tracked:
            return [os.path.join(project_root, f) for f in tracked
                    if not should_ignore(f)
                    and os.path.splitext(f)[1] in SOURCE_EXTENSIONS]
    all_files = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
        for file in files:
            filepath = os.path.join(root, file)
            if not should_ignore(filepath) and os.path.isfile(filepath):
                if os.path.splitext(filepath)[1] in SOURCE_EXTENSIONS:
                    all_files.append(filepath)
    return all_files

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
    all_files = list_files(project_root)
    issues_found = False

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
