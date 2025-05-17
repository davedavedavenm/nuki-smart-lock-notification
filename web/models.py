import os
import json
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class UserDatabase:
    """Simple file-based user database"""
    
    def __init__(self, base_dir):
        """Initialize the database with a base directory"""
        self.base_dir = base_dir
        self.users_file = os.path.join(base_dir, 'config', 'users.json')
        self.users = self._load_users()
        
        # Create default admin user if no users exist
        if not self.users:
            self.add_user('admin', 'nukiadmin', 'admin', True)
    
    def _load_users(self):
        """Load users from the users file"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading users: {e}")
                return {}
        return {}
    
    def _save_users(self):
        """Save users to the users file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            
            # Secure the file
            os.chmod(self.users_file, 0o600)
            
            return True
        except IOError as e:
            print(f"Error saving users: {e}")
            return False
    
    def add_user(self, username, password, role='agent', active=True):
        """Add a new user or update existing user"""
        if not username or not password:
            return False
            
        # Validate role (default to agent if invalid role provided)
        if role not in ['admin', 'agent']:
            role = 'agent'
            
        self.users[username] = {
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
            'role': role,
            'active': active,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'theme': 'dark'  # Default theme - dark mode
        }
        
        return self._save_users()
    
    def get_user(self, username):
        """Get a user by username"""
        return self.users.get(username)
    
    def authenticate(self, username, password):
        """Authenticate a user"""
        user = self.get_user(username)
        if not user:
            return False
            
        if not user.get('active', True):
            return False
            
        if check_password_hash(user.get('password_hash', ''), password):
            # Update last login time
            self.users[username]['last_login'] = datetime.now().isoformat()
            self._save_users()
            return True
            
        return False
    
    def update_password(self, username, new_password):
        """Update a user's password"""
        if not username in self.users:
            return False
            
        self.users[username]['password_hash'] = generate_password_hash(new_password, method='pbkdf2:sha256')
        return self._save_users()
    
    def update_role(self, username, new_role):
        """Update a user's role"""
        if not username in self.users:
            return False
        
        # Validate role (only allow specific roles)
        if new_role not in ['admin', 'agent']:
            return False
            
        self.users[username]['role'] = new_role
        return self._save_users()
    
    def update_active(self, username, active):
        """Update a user's active status"""
        if not username in self.users:
            return False
            
        self.users[username]['active'] = active
        return self._save_users()
    
    def update_theme(self, username, theme):
        """Update a user's theme preference"""
        if not username in self.users:
            return False
            
        self.users[username]['theme'] = theme
        return self._save_users()
    
    def delete_user(self, username):
        """Delete a user"""
        if not username in self.users:
            return False
            
        if username == 'admin':
            return False  # Prevent deletion of admin user
            
        del self.users[username]
        return self._save_users()
    
    def get_all_users(self):
        """Get all users"""
        users_list = []
        for username, data in self.users.items():
            user = data.copy()
            user['username'] = username
            # Don't expose password hash
            user.pop('password_hash', None)
            users_list.append(user)
        
        return users_list
    
    def user_exists(self, username):
        """Check if a user exists"""
        return username in self.users

class User:
    """User class for Flask-Login compatibility"""
    
    def __init__(self, username, role, active=True, theme='dark'):
        self.username = username
        self.role = role
        self.active = active
        self.theme = theme
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return self.active
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_agent(self):
        return self.role == 'agent'
    
    @classmethod
    def from_db_user(cls, db_user, username):
        """Create a User object from database user dictionary"""
        if not db_user:
            return None
            
        return cls(
            username=username,
            role=db_user.get('role', 'agent'),
            active=db_user.get('active', True),
            theme=db_user.get('theme', 'dark')
        )
