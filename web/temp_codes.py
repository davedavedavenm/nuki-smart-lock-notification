#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime

class TemporaryCodeDatabase:
    """File-based database for temporary access codes"""
    
    def __init__(self, data_dir):
        """Initialize the database with a data directory"""
        self.data_dir = data_dir
        self.codes_file = os.path.join(self.data_dir, 'temp_codes.json')
        self.codes = self._load_codes()
    
    def _load_codes(self):
        """Load codes from the codes file"""
        if os.path.exists(self.codes_file):
            try:
                with open(self.codes_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading temporary codes: {e}")
                return {}
        return {}
    
    def _save_codes(self):
        """Save codes to the codes file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.codes_file), exist_ok=True)
            
            with open(self.codes_file, 'w') as f:
                json.dump(self.codes, f, indent=2)
            
            # Secure the file
            os.chmod(self.codes_file, 0o600)
            
            return True
        except IOError as e:
            print(f"Error saving temporary codes: {e}")
            return False
    
    def add_code(self, code_id, code, name, created_by, expiry):
        """Add a new temporary code"""
        if not code or not name or not created_by or not expiry:
            return False
        
        # Convert expiry to ISO format if it's a datetime object
        if isinstance(expiry, datetime):
            expiry = expiry.isoformat()
            
        self.codes[code_id] = {
            'code': code,
            'name': name,
            'created_by': created_by,
            'created_at': datetime.now().isoformat(),
            'expiry': expiry,
            'is_active': True,
            'last_used': None
        }
        
        return self._save_codes()
    
    def get_code(self, code_id):
        """Get a code by its ID"""
        return self.codes.get(str(code_id))
    
    def get_code_by_value(self, code_value):
        """Get a code by its value (the actual code)"""
        for code_id, code_data in self.codes.items():
            if code_data.get('code') == code_value:
                code_data['id'] = code_id
                return code_data
        return None
    
    def update_code(self, code_id, data):
        """Update a code with new data"""
        if str(code_id) not in self.codes:
            return False
            
        # Update only the provided fields
        for key, value in data.items():
            if key in self.codes[str(code_id)]:
                self.codes[str(code_id)][key] = value
                
        return self._save_codes()
    
    def delete_code(self, code_id):
        """Delete a code"""
        if str(code_id) not in self.codes:
            return False
            
        del self.codes[str(code_id)]
        return self._save_codes()
    
    def get_all_codes(self):
        """Get all codes"""
        codes_list = []
        for code_id, data in self.codes.items():
            code = data.copy()
            code['id'] = code_id
            codes_list.append(code)
        
        return codes_list
    
    def get_codes_by_creator(self, username):
        """Get all codes created by a specific user"""
        return [
            {**data, 'id': code_id} 
            for code_id, data in self.codes.items() 
            if data.get('created_by') == username
        ]
    
    def clean_expired_codes(self):
        """Remove expired codes"""
        now = datetime.now()
        expired_codes = []
        
        for code_id, data in self.codes.items():
            expiry = data.get('expiry')
            if expiry:
                try:
                    expiry_date = datetime.fromisoformat(expiry)
                    if expiry_date < now and data.get('is_active', True):
                        data['is_active'] = False
                        expired_codes.append(code_id)
                except (ValueError, TypeError):
                    pass
        
        if expired_codes:
            return self._save_codes()
        return True
    
    def get_active_codes(self):
        """Get all active (non-expired) codes"""
        now = datetime.now()
        active_codes = []
        
        for code_id, data in self.codes.items():
            expiry = data.get('expiry')
            is_active = data.get('is_active', True)
            
            if expiry and is_active:
                try:
                    expiry_date = datetime.fromisoformat(expiry)
                    if expiry_date > now:
                        code = data.copy()
                        code['id'] = code_id
                        active_codes.append(code)
                except (ValueError, TypeError):
                    pass
        
        return active_codes
