#!/usr/bin/env python3

import os
import json
import sys
import argparse
from datetime import datetime
from werkzeug.security import generate_password_hash

def main():
    parser = argparse.ArgumentParser(description='Reset users database and create admin user')
    parser.add_argument('--base-dir', default='/app', help='Base directory of the application')
    parser.add_argument('--username', default='admin', help='Admin username')
    parser.add_argument('--password', default='nukiadmin', help='Admin password')
    args = parser.parse_args()
    
    users_file = os.path.join(args.base_dir, 'config', 'users.json')
    users_dir = os.path.dirname(users_file)
    
    # Create directory if it doesn't exist
    if not os.path.exists(users_dir):
        os.makedirs(users_dir, exist_ok=True)
    
    # Create new admin user
    users = {
        args.username: {
            'password_hash': generate_password_hash(args.password, method='pbkdf2:sha256'),
            'role': 'admin',
            'active': True,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'theme': 'light'
        }
    }
    
    # Save the new users database
    try:
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        # Secure the file
        os.chmod(users_file, 0o600)
        
        print(f"User database reset. Created admin user '{args.username}'")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
