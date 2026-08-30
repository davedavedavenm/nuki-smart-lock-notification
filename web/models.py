import os
import json
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Authentication policy: which sign-in methods a user may use.
DEFAULT_AUTH = {'password': True, 'passkey': 'optional'}
PASSKEY_POLICIES = ('optional', 'required', 'disabled')


def _default_auth():
    return dict(DEFAULT_AUTH)


class UserDatabase:
    """Simple file-based user database"""

    def __init__(self, data_dir):
        """Initialize the database with a data directory"""
        self.data_dir = data_dir
        self.users_file = os.path.join(self.data_dir, 'users.json')
        self.load_error = None
        self.users = self._load_users()
        # NOTE: no default user is created automatically. The first admin
        # account is created by the setup wizard (POST /api/setup), so a
        # fresh deployment never has known default credentials.

    def _load_users(self):
        """Load users from the users file.

        A MISSING file means a fresh install (empty database). A CORRUPT file
        must fail closed: load_error is set and users_exist() reports True so
        the setup wizard cannot be re-opened by an attacker by truncating the
        users file.
        """
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError('users.json must contain a JSON object')
                return data
            except (json.JSONDecodeError, ValueError, OSError) as e:
                print(f"Error loading users file {self.users_file}: {e}")
                self.load_error = f"users.json is corrupt: {e}"
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
            'theme': 'dark',  # Default theme - dark mode
            'auth': _default_auth(),
        }

        return self._save_users()

    # ------------------------------------------------------------------
    # Authentication policy (per-user password / passkey settings)
    # ------------------------------------------------------------------

    def get_auth(self, username):
        """Return the auth policy for a user, normalised."""
        user = self.get_user(username)
        if not user:
            return None
        auth = user.get('auth')
        if not isinstance(auth, dict):
            auth = _default_auth()
        policy = {
            'password': bool(auth.get('password', True) and user.get('password_hash')),
            'passkey': auth.get('passkey', 'optional'),
        }
        if policy['passkey'] not in PASSKEY_POLICIES:
            policy['passkey'] = 'optional'
        return policy

    def _user_has_passkey(self, username):
        user = self.get_user(username) or {}
        return bool(user.get('passkeys'))

    def _user_can_log_in(self, username):
        """True if the user still has at least one usable sign-in method."""
        user = self.get_user(username) or {}
        auth = self.get_auth(username)
        if auth is None:
            return False
        if auth['password'] and user.get('password_hash'):
            return True
        if auth['passkey'] != 'disabled' and self._user_has_passkey(username):
            return True
        return False

    def _snapshot(self, username):
        user = self.users[username]
        return {'auth': dict(user.get('auth', {})), 'password_hash': user.get('password_hash')}

    def _restore(self, username, snapshot):
        self.users[username]['auth'] = snapshot['auth']
        self.users[username]['password_hash'] = snapshot['password_hash']

    def _admin_with_working_login_exists(self):
        """True if at least one active admin retains a usable sign-in method."""
        for name, data in self.users.items():
            if data.get('role') != 'admin' or not data.get('active', True):
                continue
            auth = self.get_auth(name)
            if auth['password'] and data.get('password_hash'):
                return True
            if auth['passkey'] != 'disabled' and data.get('passkeys'):
                return True
        return False

    def set_password_enabled(self, username, enabled):
        """Enable or disable (remove) password sign-in for a user."""
        user = self.get_user(username)
        if not user:
            return False, 'User not found'

        if enabled:
            # Re-enabling requires an actual password; admin must set one via
            # the password update flow first.
            if not user.get('password_hash'):
                return False, 'No password is stored for this user — set a new password first'
            user.setdefault('auth', _default_auth())['password'] = True
        else:
            snapshot = self._snapshot(username)
            user.setdefault('auth', _default_auth())['password'] = False
            user['password_hash'] = None  # password removed entirely
            if not self._admin_with_working_login_exists():
                self._restore(username, snapshot)
                return False, 'Refused: this change would leave no admin able to sign in'

        if not self._save_users():
            return False, 'Failed to save users file'
        return True, None

    def set_passkey_policy(self, username, policy):
        """Set the passkey policy: optional, required or disabled."""
        user = self.get_user(username)
        if not user:
            return False, 'User not found'
        if policy not in PASSKEY_POLICIES:
            return False, 'Invalid passkey policy'

        snapshot = self._snapshot(username)
        user.setdefault('auth', _default_auth())['passkey'] = policy
        if policy == 'disabled' and not self._admin_with_working_login_exists():
            self._restore(username, snapshot)
            return False, 'Refused: this change would leave no admin able to sign in'
        if policy == 'disabled' and not self._user_can_log_in(username):
            self._restore(username, snapshot)
            return False, 'Cannot disable passkeys: this user would have no way to sign in'

        if not self._save_users():
            return False, 'Failed to save users file'
        return True, None

    def remove_password(self, username):
        """Alias with clearer intent: disable password and drop the hash."""
        ok, err = self.set_password_enabled(username, False)
        return ok, err
    
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

        if not user.get('password_hash'):
            return False  # password sign-in removed for this account

        if check_password_hash(user['password_hash'], password):
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
        """Get all users with management metadata"""
        users_list = []
        for username, data in self.users.items():
            user = data.copy()
            user['username'] = username
            # Don't expose password hash
            has_password = bool(user.pop('password_hash', None))
            user['has_password'] = has_password
            user['passkey_count'] = len(user.get('passkeys', []))
            user['auth'] = self.get_auth(username)
            users_list.append(user)

        return users_list
    
    def user_exists(self, username):
        """Check if a user exists"""
        return username in self.users

    def users_exist(self):
        """Check if any user account exists.

        Returns True too when the users file is corrupt (fail closed) so the
        setup wizard stays locked for a running system.
        """
        return bool(self.users) or self.load_error is not None

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
