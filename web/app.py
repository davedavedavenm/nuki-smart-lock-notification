#!/usr/bin/env python3
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

# Enable lenient mode for web interface to allow setup wizard
os.environ["ALLOW_MISSING_TOKEN"] = "true"

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_session import Session

# Add parent directory to path to import nuki modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from scripts.nuki.config import ConfigManager
from scripts.nuki.api import NukiAPI
from scripts.nuki.utils import ActivityTracker
from web.models import UserDatabase, User
from web.temp_codes import TemporaryCodeDatabase
from web.dark_mode import init_app
from web import passkeys as pk

# Configure logging with fallback to console if file logging fails
log_handlers = []
try:
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(parent_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Attempt to add file handler
    log_file = os.path.join(logs_dir, "nuki_web.log")
    file_handler = logging.FileHandler(log_file)
    log_handlers.append(file_handler)
except (PermissionError, IOError) as e:
    print(f"WARNING: Could not set up file logging: {e}")
    print("File logging will be disabled. Check directory permissions.")
    print("See TROUBLESHOOTING.md for information on fixing permission issues.")

# Always add console handler as fallback
log_handlers.append(logging.StreamHandler())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('nuki_web')

if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.warning("File logging is disabled due to permission issues. Using console logging only.")
    logger.warning("To fix this, ensure the container has write access to the logs directory.")
    logger.warning("See TROUBLESHOOTING.md for more information.")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))  # Use persistent secret key if available
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.environ.get('SESSION_FILE_DIR', os.path.join(parent_dir, 'flask_session'))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Longer session lifetime
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('WEB_HTTPS', 'false').lower() == 'true'  # set WEB_HTTPS=true behind an HTTPS reverse proxy
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security best practice

# Initialize Flask-Session
Session(app)

# Behind a reverse proxy that terminates TLS (Pangolin, Nginx, Caddy...):
# trust the forwarded headers so request.is_secure / request.host reflect
# the real client-facing scheme. Required for correct session cookies and
# passkey (WebAuthn) origin handling. Enable with PROXY_FIX=true.
if os.environ.get('PROXY_FIX', 'false').lower() == 'true':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Make sessions permanent by default
@app.before_request
def make_session_permanent():
    session.permanent = True

# Check if setup is needed
@app.before_request
def check_setup():
    # Allow access to setup page, setup API, static files, and the health
    # endpoint (used by the Docker healthcheck) regardless of setup state
    if request.endpoint in ['setup', 'api_setup', 'static', 'health', 'health_check']:
        return

    # Fresh install (no user accounts yet): walk the user through setup
    if not user_db.users_exist():
        return redirect(url_for('setup'))

# Initialize dark mode as default
init_app(app)

# Static asset cache-busting: bump when CSS/JS change so browsers fetch fresh
ASSET_VERSION = '20260830.2'

@app.context_processor
def inject_asset_version():
    return {'asset_version': ASSET_VERSION}

# Provide common template variables
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Load configuration
config = ConfigManager(parent_dir)
api = NukiAPI(config)
tracker = ActivityTracker(config.data_dir)
user_db = UserDatabase(config.data_dir)
temp_code_db = TemporaryCodeDatabase(config.data_dir)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('You need administrator privileges to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Agent access required decorator (admin or agent role)
def agent_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        if session.get('role') not in ['admin', 'agent']:
            flash('You need agent or administrator privileges to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    return render_template('index.html')

@app.route('/setup')
def setup():
    """First-time setup wizard page.

    Fresh installs start at stage 1. Because each stage saves immediately,
    an in-progress setup can be resumed (session-scoped) after a refresh.
    """
    if not user_db.users_exist():
        return render_template('setup.html', setup_stage=session.get('setup_stage', 1))
    # Users exist: only the session that created the admin may resume the wizard
    if session.get('setup_stage'):
        return render_template('setup.html', setup_stage=session.get('setup_stage'))
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = user_db.get_user(username)
        auth = user_db.get_auth(username) if user else None

        # Pass the secret check FIRST, so policy messages only ever appear for
        # someone who already proved the password — wrong passwords always get
        # the same generic error (no username enumeration).
        if user and auth and user_db.authenticate(username, password) and (
            not auth['password'] or (auth['passkey'] == 'required' and user.get('passkeys'))
        ):
            if auth['passkey'] == 'required' and user.get('passkeys'):
                error = 'This account requires passkey sign-in'
            elif not user.get('password_hash'):
                error = 'Password sign-in is not set up for this account — use your passkey'
            else:
                error = 'Password sign-in is disabled for this account — use your passkey'
        elif user and user_db.authenticate(username, password):
            user_data = user_db.get_user(username)
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user_data.get('role', 'user')
            session['theme'] = user_data.get('theme', 'dark')

            flash('You were successfully logged in')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('theme', None)
    flash('You were logged out')
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# Passkey (WebAuthn) support
# ---------------------------------------------------------------------------

@app.route('/api/profile/password-status', methods=['GET'])
@login_required
def profile_password_status():
    """Whether the current user still has a password, and how many passkeys."""
    user = user_db.get_user(session['username'])
    return jsonify({
        "has_password": bool(user and user.get('password_hash')),
        "passkey_count": len(pk.get_passkeys(user)) if user else 0,
    })


@app.route('/api/passkeys', methods=['GET'])
@login_required
def passkey_list():
    """List the current user's registered passkeys."""
    user = user_db.get_user(session['username'])
    keys = [
        {"id": k["id"], "name": k.get("name", "Passkey"), "created_at": k.get("created_at")}
        for k in pk.get_passkeys(user)
    ]
    return jsonify({"passkeys": keys, "secure_context": request.is_secure or request.host.startswith(('localhost', '127.0.0.1'))})


@app.route('/api/passkeys/register/begin', methods=['POST'])
@login_required
def passkey_register_begin():
    """Start passkey registration for the logged-in user."""
    user = user_db.get_user(session['username'])
    if user is None:
        return jsonify({"error": "User not found"}), 404
    try:
        options, state = pk.begin_registration(user, session['username'], pk.rp_from_request(request))
        session['passkey_reg_state'] = state
        return jsonify(options)
    except Exception as e:
        logger.error(f"Passkey registration begin failed: {e}")
        return jsonify({"error": "Could not start passkey registration"}), 500


@app.route('/api/passkeys/register/finish', methods=['POST'])
@login_required
def passkey_register_finish():
    """Verify and store a newly registered passkey."""
    state = session.pop('passkey_reg_state', None)
    if not state:
        return jsonify({"error": "No registration in progress"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    user = user_db.get_user(session['username'])
    try:
        credential_id, attested = pk.complete_registration(
            state, data, pk.rp_from_request(request)
        )
        name = (data.get('name') or 'Passkey').strip()[:40]
        pk.add_passkey(user, credential_id, attested, name=name)
        if not user_db._save_users():
            return jsonify({"error": "Could not save passkey"}), 500
        logger.info(f"Passkey registered for user {session['username']}")
        return jsonify({"success": True, "message": "Passkey registered"})
    except Exception as e:
        logger.error(f"Passkey registration failed: {e}")
        return jsonify({"error": "Passkey registration failed"}), 400


@app.route('/api/passkeys/<credential_id>', methods=['DELETE'])
@login_required
def passkey_delete(credential_id):
    """Remove one of the current user's passkeys."""
    user = user_db.get_user(session['username'])
    if pk.remove_passkey(user, credential_id):
        user_db._save_users()
        return jsonify({"success": True})
    return jsonify({"error": "Passkey not found"}), 404


@app.route('/api/passkeys/auth/begin', methods=['POST'])
def passkey_auth_begin():
    """Start a usernameless passkey login ceremony."""
    try:
        options, state = pk.begin_authentication(user_db, pk.rp_from_request(request))
        session['passkey_auth_state'] = state
        return jsonify(options)
    except Exception as e:
        logger.error(f"Passkey auth begin failed: {e}")
        return jsonify({"error": "Could not start passkey login"}), 500


@app.route('/api/passkeys/auth/finish', methods=['POST'])
def passkey_auth_finish():
    """Verify an assertion and log the user in."""
    state = session.pop('passkey_auth_state', None)
    if not state:
        return jsonify({"error": "No login in progress"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        username = pk.complete_authentication(state, data, user_db, pk.rp_from_request(request))
    except Exception as e:
        logger.warning(f"Passkey login failed: {e}")
        return jsonify({"error": "Passkey login failed"}), 401

    user = user_db.get_user(username)
    if not user or not user.get('active', True):
        return jsonify({"error": "Account is disabled"}), 401
    auth = user_db.get_auth(username)
    if auth and auth['passkey'] == 'disabled':
        return jsonify({"error": "Passkey sign-in is disabled for this account"}), 401

    session['logged_in'] = True
    session['username'] = username
    session['role'] = user.get('role', 'user')
    session['theme'] = user.get('theme', 'dark')
    user['last_login'] = datetime.now().isoformat()
    user_db._save_users()
    logger.info(f"User {username} logged in with passkey")
    return jsonify({"success": True, "redirect": url_for('index')})


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    """API endpoint to update user profile"""
    try:
        # Get data from request
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        theme = data.get('theme')
        action = data.get('action')

        # Get current user
        username = session.get('username')

        # Remove own password (only possible when a passkey exists)
        if action == 'remove_password':
            auth = user_db.get_auth(username)
            if not user_db.get_user(username).get('passkeys'):
                return jsonify({"error": "Register a passkey first — removing the password would leave no way to sign in"}), 400
            ok, err = user_db.set_password_enabled(username, False)
            if not ok:
                return jsonify({"error": err}), 400
            logger.info(f"Password removed for user: {username}")
            return jsonify({"success": True, "message": "Password removed — sign in with your passkey from now on"})

        # Verify current password
        if current_password and new_password:
            if not user_db.authenticate(username, current_password):
                return jsonify({"error": "Current password is incorrect"}), 401
            
            # Update password
            success = user_db.update_password(username, new_password)
            if not success:
                return jsonify({"error": "Failed to update password"}), 500
            
            logger.info(f"Password updated for user: {username}")
        
        # Update theme if provided
        if theme:
            user_db.update_theme(username, theme)
            session['theme'] = theme
            logger.info(f"Theme updated for user: {username} to {theme}")
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    """API endpoint to update user theme preference"""
    try:
        data = request.json
        username = session.get('username')
        theme = data.get('theme')
        
        # Update theme
        if theme and username:
            user_db.update_theme(username, theme)
            session['theme'] = theme
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Invalid theme or username"}), 400
    except Exception as e:
        logger.error(f"Error updating theme: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/users_manage')
@admin_required
def users_manage():
    """User management page"""
    return render_template('users_manage.html')

@app.route('/api/users/manage', methods=['GET'])
@admin_required
def get_users_manage():
    """API endpoint to get all users for management"""
    try:
        users = user_db.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage', methods=['POST'])
@admin_required
def add_user():
    """API endpoint to add a new user"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'agent')
        active = data.get('active', True)

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        if user_db.user_exists(username):
            return jsonify({"error": "User already exists"}), 409
        
        success = user_db.add_user(username, password, role, active)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to add user"}), 500
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage/<username>', methods=['PUT'])
@admin_required
def update_user(username):
    """API endpoint to update a user"""
    try:
        data = request.json
        password = data.get('password')
        role = data.get('role')
        active = data.get('active')
        theme = data.get('theme')

        if not user_db.user_exists(username):
            return jsonify({"error": "User not found"}), 404
        
        # Update password if provided
        if password:
            user_db.update_password(username, password)
        
        # Update role if provided
        if role:
            user_db.update_role(username, role)
        
        # Update active status if provided
        if active is not None:
            user_db.update_active(username, active)
        
        # Update theme if provided
        if theme:
            user_db.update_theme(username, theme)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/manage/<username>', methods=['DELETE'])
@admin_required
def delete_user(username):
    """API endpoint to delete a user"""
    try:
        if username == 'admin' or username == session.get('username'):
            return jsonify({"error": "Cannot delete admin user or currently logged in user"}), 400
        
        if not user_db.user_exists(username):
            return jsonify({"error": "User not found"}), 404
        
        success = user_db.delete_user(username)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete user"}), 500
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/manage/<username>/auth-policy', methods=['PUT'])
@admin_required
def set_auth_policy(username):
    """Set per-user sign-in policy: password on/off, passkey optional/required/disabled.

    Guards refuse changes that would leave a user — or every admin — without
    a working sign-in method.
    """
    try:
        data = request.json or {}
        if not user_db.user_exists(username):
            return jsonify({"error": "User not found"}), 404

        if 'password' in data:
            ok, err = user_db.set_password_enabled(username, bool(data['password']))
            if not ok:
                return jsonify({"error": err}), 400
            logger.info(f"Password sign-in {'enabled' if data['password'] else 'disabled'} for {username}")

        if 'passkey' in data:
            ok, err = user_db.set_passkey_policy(username, data['passkey'])
            if not ok:
                return jsonify({"error": err}), 400
            logger.info(f"Passkey policy for {username}: {data['passkey']}")

        return jsonify({"success": True, "auth": user_db.get_auth(username)})
    except Exception as e:
        logger.error(f"Error updating auth policy for {username}: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Backup & restore (admin): export/import of configuration, credentials,
# users and temporary codes.
# ---------------------------------------------------------------------------

@app.route('/admin/backup')
@admin_required
def backup_page():
    """Backup & restore page"""
    return render_template('backup.html')


@app.route('/api/admin/backup/export', methods=['GET'])
@admin_required
def backup_export():
    """Download a JSON bundle of configuration and (optionally) secrets.

    include_secrets=false masks credential values — safe for support/sharing.
    include_secrets=true produces a full migration backup. Both are logged.
    """
    try:
        include_secrets = request.args.get('include_secrets', 'false').lower() == 'true'

        def ini_to_dict(parser):
            return {s: dict(parser.items(s)) for s in parser.sections()}

        def mask(d):
            return {k: {kk: ('***' if vv else vv) for kk, vv in v.items()} for k, v in d.items()}

        users_export = {}
        for username, u in user_db.users.items():
            u_copy = json.loads(json.dumps(u))  # deep copy
            if not include_secrets:
                u_copy.pop('password_hash', None)
                u_copy.pop('passkeys', None)
                u_copy.pop('user_handle', None)
            users_export[username] = u_copy

        bundle = {
            "export_version": 1,
            "app": "nuki-smart-lock-notification",
            "exported_at": datetime.now().isoformat(),
            "include_secrets": include_secrets,
            "config": ini_to_dict(config.config),
            "credentials": ini_to_dict(config.credentials) if include_secrets else mask(ini_to_dict(config.credentials)),
            "users": users_export,
            "temp_codes": temp_code_db._load_codes() if hasattr(temp_code_db, '_load_codes') else {},
        }

        logger.info(f"Backup export by {session.get('username')} (include_secrets={include_secrets})")
        resp = jsonify(bundle)
        resp.headers['Content-Disposition'] = 'attachment; filename=nuki-backup.json'
        return resp
    except Exception as e:
        logger.error(f"Backup export failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/backup/import', methods=['POST'])
@admin_required
def backup_import():
    """Import a backup bundle. Applies only selected sections, backs up the
    current files first, and refuses imports that would lock every admin out.
    """
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "No valid backup data provided"}), 400
        if not data.get('confirm'):
            return jsonify({"error": "Missing confirmation — importing overwrites the selected settings"}), 400

        bundle = data.get('backup')
        if not isinstance(bundle, dict) or 'config' not in bundle and 'credentials' not in bundle and 'users' not in bundle:
            return jsonify({"error": "This does not look like a Nuki backup file"}), 400
        if bundle.get('app') != 'nuki-smart-lock-notification':
            return jsonify({"error": "Backup was not created by this application"}), 400

        sections = data.get('sections', {})
        applied = []

        # --- users section: validate BEFORE touching anything ---
        if sections.get('users') and isinstance(bundle.get('users'), dict):
            incoming = bundle['users']
            if not incoming or not any(
                u.get('role') == 'admin' and (u.get('password_hash') or u.get('passkeys'))
                for u in incoming.values()
            ):
                return jsonify({"error": "Refused: the imported users contain no admin with a sign-in method"}), 400
            if session.get('username') not in incoming:
                return jsonify({"error": "Refused: the import would remove your own account"}), 400

        # --- backup current state ---
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backups = {}
        if sections.get('users'):
            backups['users'] = (user_db.users_file, json.dumps(user_db.users, indent=2))
        if sections.get('config') or sections.get('credentials'):
            for label, path_obj in (('config', config.config_path), ('credentials', config.credentials_path)):
                if os.path.exists(path_obj):
                    with open(path_obj, 'r') as f:
                        backups[label] = (path_obj, f.read())

        def replace_parser(sections_data):
            """Build a fresh ConfigParser from imported sections (full restore,
            not a merge — the pre-import file is backed up first)."""
            import configparser
            p = configparser.ConfigParser(interpolation=None)
            p.read_dict({s: {k: str(v) for k, v in items.items()} for s, items in sections_data.items()})
            return p

        try:
            if sections.get('config') and isinstance(bundle.get('config'), dict):
                config.config = replace_parser(bundle['config'])
                applied.append('config')
            if sections.get('credentials') and isinstance(bundle.get('credentials'), dict):
                creds = bundle['credentials']
                if any(v == '***' for items in creds.values() for v in items.values()):
                    return jsonify({"error": "This backup has masked credentials — re-export with 'include secrets' to restore credentials"}), 400
                config.credentials = replace_parser(creds)
                applied.append('credentials')
            if sections.get('users'):
                user_db.users = incoming
                user_db._save_users()
                applied.append('users')
            if sections.get('temp_codes') and isinstance(bundle.get('temp_codes'), dict):
                temp_code_db.codes = bundle['temp_codes']
                temp_code_db._save_codes()
                applied.append('temp_codes')
        except Exception as e:
            # roll back what we touched using the backups
            for label, (path, content) in backups.items():
                try:
                    with open(path, 'w') as f:
                        f.write(content)
                    if label == 'credentials':
                        os.chmod(path, 0o600)
                except OSError:
                    pass
            logger.error(f"Backup import failed and was rolled back: {e}")
            return jsonify({"error": f"Import failed, previous settings restored: {e}"}), 500

        # persist side-cars (config.ini / credentials.ini) — users already saved
        if 'config' in applied or 'credentials' in applied:
            _persist_config_files()
            config.reload()
        if 'temp_codes' in applied:
            try:
                os.chmod(temp_code_db.codes_file, 0o600)
            except OSError:
                pass

        # drop any session-stale backup artifacts safely
        for label, (path, content) in backups.items():
            bpath = f"{path}.backup-{stamp}"
            try:
                with open(bpath, 'w') as f:
                    f.write(content)
                if label == 'credentials':
                    os.chmod(bpath, 0o600)
            except OSError:
                pass

        logger.info(f"Backup import by {session.get('username')}: sections={applied}")
        return jsonify({"success": True, "applied": applied,
                        "message": f"Restored: {', '.join(applied)}. Previous files saved with a .backup-{stamp} suffix."})
    except Exception as e:
        logger.error(f"Backup import error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/activity')
@login_required
def activity():
    """Activity log page"""
    return render_template('activity.html')

@app.route('/api/activity', methods=['GET'])
@login_required
def get_activity():
    """API endpoint to get activity logs"""
    try:
        # Get parameters
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 50))
        
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            # No locks visible (e.g. token not yet configured) — return a
            # clean empty state instead of an error
            return jsonify([])

        all_activity = []

        # Get activity for each lock
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')

            # Get activity logs
            activity = api.get_smartlock_logs(lock_id, limit=limit)
            
            # Filter by date if needed
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_activity = []
                
                for event in activity:
                    event_date = api.parse_date(event.get('date'))
                    if event_date and event_date >= cutoff_date:
                        # Add lock name to event
                        event['lockName'] = lock_name
                        filtered_activity.append(event)
                
                all_activity.extend(filtered_activity)
            else:
                # Add lock name to events
                for event in activity:
                    event['lockName'] = lock_name
                all_activity.extend(activity)
        
        # Sort by date (newest first)
        all_activity.sort(key=lambda x: api.parse_date(x.get('date')), reverse=True)
        
        # Limit results if needed
        if limit > 0 and len(all_activity) > limit:
            all_activity = all_activity[:limit]
        
        # Process activity for display
        processed_activity = []
        for event in all_activity:
            # Extract event details
            event_id = event.get('id')
            lock_name = event.get('lockName', 'Unknown Lock')
            action = event.get('action')
            trigger = event.get('trigger')
            auth_id = event.get('authId')
            date = api.parse_date(event.get('date'))
            
            if not date:
                continue
            
            # Get action description
            action_description = api.get_action_description(event)
            
            # Get trigger description
            trigger_description = api.get_trigger_description(trigger)
            
            # Get user name
            user_name = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            
            # Create processed event
            processed_event = {
                'id': event_id,
                'lock_name': lock_name,
                'action': action_description,
                'trigger': trigger_description,
                'user': user_name,
                'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                'raw_date': date.isoformat()
            }
            
            processed_activity.append(processed_event)
        
        return jsonify(processed_activity)
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
@login_required
def status():
    """Lock status page"""
    return render_template('status.html')

@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    """API endpoint to get lock status"""
    try:
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            # No locks visible (e.g. token not yet configured) — return a
            # clean empty state instead of an error
            return jsonify([])

        # Process lock information
        lock_status = []
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')
            
            # Get current state
            state = lock.get('state', {})
            state_name = state.get('stateName')
            if not state_name:
                state_code = state.get('state')
                state_name = api.get_status_description(state_code)
            
            # Get battery info
            battery_critical = state.get('batteryCritical', False)
            battery_charging = state.get('batteryCharging', False)
            battery_charge = state.get('batteryCharge', 0)
            
            # Create status object
            status = {
                'id': lock_id,
                'name': lock_name,
                'state': state_name,
                'battery_critical': battery_critical,
                'battery_charging': battery_charging,
                'battery_charge': battery_charge,
                'last_activity': None,
                'last_user': None
            }
            
            # Get recent activity for this lock
            activity = api.get_smartlock_logs(lock_id, limit=1)
            if activity:
                last_event = activity[0]
                date = api.parse_date(last_event.get('date'))
                auth_id = last_event.get('authId')
                trigger = last_event.get('trigger')
                
                if date:
                    status['last_activity'] = date.strftime('%Y-%m-%d %H:%M:%S')
                    status['last_action'] = api.get_action_description(last_event)
                    status['last_user'] = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            
            lock_status.append(status)
        
        return jsonify(lock_status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/notifications')
@admin_required
def notifications():
    """Notification settings page - Admin only"""
    return render_template('notifications.html')

@app.route('/api/notifications/settings', methods=['GET'])
@admin_required
def get_notification_settings():
    """API endpoint to get notification settings"""
    try:
        # Get notification settings
        settings = {
            'type': config.notification_type,
            'digest_mode': config.digest_mode,
            'notify_auto_lock': config.notify_auto_lock,
            'notify_system_events': config.notify_system_events,
            'excluded_users': config.excluded_users,
            'excluded_actions': config.excluded_actions,
            'excluded_triggers': config.excluded_triggers
        }
        
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/settings', methods=['POST'])
@admin_required
def update_notification_settings():
    """API endpoint to update notification settings"""
    try:
        # Get data from request
        data = request.json
        
        # Get current config file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.ini")
        
        # Import the configuration utility functions
        sys.path.insert(0, os.path.join(parent_dir, "scripts"))
        from configure import update_config as update_config_func
        
        # Update notification type
        if 'type' in data:
            update_config_func(config_path, 'General', 'notification_type', data['type'])
        
        # Update digest mode
        if 'digest_mode' in data:
            update_config_func(config_path, 'Notification', 'digest_mode', str(data['digest_mode']).lower())
        
        # Update auto lock notifications
        if 'notify_auto_lock' in data:
            update_config_func(config_path, 'Notification', 'notify_auto_lock', str(data['notify_auto_lock']).lower())
        
        # Update system events notifications
        if 'notify_system_events' in data:
            update_config_func(config_path, 'Notification', 'notify_system_events', str(data['notify_system_events']).lower())
        
        # Update excluded users
        if 'excluded_users' in data:
            excluded_users = ','.join(data['excluded_users'])
            update_config_func(config_path, 'Filter', 'excluded_users', excluded_users)
        
        # Update excluded actions
        if 'excluded_actions' in data:
            excluded_actions = ','.join(data['excluded_actions'])
            update_config_func(config_path, 'Filter', 'excluded_actions', excluded_actions)
        
        # Update excluded triggers
        if 'excluded_triggers' in data:
            excluded_triggers = ','.join(data['excluded_triggers'])
            update_config_func(config_path, 'Filter', 'excluded_triggers', excluded_triggers)
        
        # Reload configuration
        global config, api
        config = ConfigManager(parent_dir)
        api = NukiAPI(config)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/config')
@admin_required
def config_page():
    """Configuration page - Admin only"""
    return render_template('config.html')

@app.route('/api/config', methods=['GET'])
@admin_required
def get_config():
    """API endpoint to get configuration"""
    try:
        # Mask API token for security but allow identifying it
        token = config.api_token
        masked_token = ""
        if token:
            if len(token) > 10:
                masked_token = f"{token[:5]}...{token[-5:]}"
            else:
                masked_token = "********"

        # Mask sensitive fields
        email_pass = "********" if config.email_password else ""
        telegram_token = ""
        if config.telegram_bot_token:
            token = config.telegram_bot_token
            telegram_token = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "********"

        # Get configuration
        config_data = {
            'nuki': {
                'api_token': masked_token
            },
            'general': {
                'notification_type': config.notification_type,
                'polling_interval': config.polling_interval
            },
            'notification': {
                'digest_mode': config.digest_mode,
                'digest_interval': config.digest_interval,
                'notify_auto_lock': config.notify_auto_lock,
                'notify_system_events': config.notify_system_events
            },
            'filter': {
                'excluded_users': config.excluded_users,
                'excluded_actions': config.excluded_actions,
                'excluded_triggers': config.excluded_triggers
            },
            'email': {
                'username': config.email_username,
                'password': email_pass,
                'smtp_server': config.smtp_server,
                'smtp_port': config.smtp_port,
                'sender': config.email_sender,
                'recipient': config.email_recipient,
                'use_html': config.use_html_email,
                'subject_prefix': config.email_subject_prefix
            },
            'telegram': {
                'bot_token': telegram_token,
                'chat_id': config.telegram_chat_id,
                'use_emoji': config.telegram_use_emoji,
                'format': config.telegram_format
            },
            'advanced': {
                'max_events_per_check': config.max_events_per_check,
                'max_historical_events': config.max_historical_events,
                'debug_mode': config.debug_mode,
                'user_cache_timeout': config.user_cache_timeout,
                'retry_on_failure': config.retry_on_failure,
                'max_retries': config.max_retries,
                'retry_delay': config.retry_delay
            }
        }
        
        return jsonify(config_data)
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
@admin_required
def update_config():
    """API endpoint to update configuration"""
    global config, api
    try:
        # Get current config file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.ini")
        config_dir = os.path.dirname(config_path)
        backup_path = os.path.join(config_dir, "config.ini.bak")
        
        # Create a backup before making changes
        import shutil
        try:
            if os.path.exists(config_path):
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup at {backup_path}")
        except Exception as backup_error:
            logger.warning(f"Failed to create backup: {backup_error}")
        
        # Import the configuration utility functions
        sys.path.insert(0, os.path.join(parent_dir, "scripts"))
        from configure import update_config as update_config_func
        
        # Get data from request
        data = request.json
        
        success_count = 0
        error_count = 0
        
        # Handle Nuki API Token separately (credentials.ini)
        if 'nuki' in data and 'api_token' in data['nuki'] and data['nuki']['api_token'] and not data['nuki']['api_token'].startswith('***'):
            try:
                if not config.credentials.has_section('Nuki'):
                    config.credentials.add_section('Nuki')
                config.credentials.set('Nuki', 'api_token', data['nuki']['api_token'])
                logger.info("Queued Nuki API token update")
                success_count += 1
            except Exception as nuki_error:
                logger.error(f"Error updating Nuki API token: {nuki_error}")
                error_count += 1

        # Handle Email Credentials
        if 'email' in data:
            try:
                if not config.credentials.has_section('Email'):
                    config.credentials.add_section('Email')
                if 'username' in data['email'] and data['email']['username']:
                    config.credentials.set('Email', 'username', data['email']['username'])
                if 'password' in data['email'] and data['email']['password'] and not data['email']['password'].startswith('***'):
                    config.credentials.set('Email', 'password', data['email']['password'])
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating email credentials: {e}")
                error_count += 1

        # Handle Telegram Credentials
        if 'telegram' in data:
            try:
                if not config.credentials.has_section('Telegram'):
                    config.credentials.add_section('Telegram')
                if 'bot_token' in data['telegram'] and data['telegram']['bot_token'] and not data['telegram']['bot_token'].startswith('***'):
                    config.credentials.set('Telegram', 'bot_token', data['telegram']['bot_token'])
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating telegram credentials: {e}")
                error_count += 1

        # Save credentials.ini if any credential changes were made
        try:
            config._save_config(config.credentials, config.credentials_path)
            logger.info("Successfully updated credentials.ini")
        except Exception as e:
            logger.error(f"Failed to save credentials.ini: {e}")
            error_count += 1

        # Remove sensitive sections from data so they aren't processed by the standard loop
        if 'nuki' in data: del data['nuki']
        # Special case: keep non-sensitive parts of email/telegram for standard loop
        standard_data = data.copy()
        if 'email' in standard_data:
            if 'username' in standard_data['email']: del standard_data['email']['username']
            if 'password' in standard_data['email']: del standard_data['email']['password']
        if 'telegram' in standard_data:
            if 'bot_token' in standard_data['telegram']: del standard_data['telegram']['bot_token']
        
        # ... validation ...

        # Validate notification type to ensure it's not empty
        if 'general' in data and 'notification_type' in data['general']:
            if not data['general']['notification_type']:
                data['general']['notification_type'] = 'both'
        
        # Update standard configuration
        for section, options in standard_data.items():
            for option, value in options.items():
                # Convert boolean values to strings
                if isinstance(value, bool):
                    value = str(value).lower()
                
                try:
                    # Update config
                    update_config_func(config_path, section, option, str(value))
                    success_count += 1
                except Exception as option_error:
                    logger.error(f"Error updating option {section}.{option}: {option_error}")
                    error_count += 1
        
        if error_count > 0:
            logger.warning(f"Configuration update completed with {error_count} errors and {success_count} successes")
        else:
            logger.info(f"Configuration update completed successfully with {success_count} changes")
        
        # Reload configuration
        config = ConfigManager(parent_dir)
        api = NukiAPI(config)
        
        # Ensure file has proper permissions
        try:
            os.chmod(config_path, 0o640)
        except Exception as perm_error:
            logger.warning(f"Failed to set config file permissions: {perm_error}")
        
        return jsonify({"success": True, "changes": success_count, "errors": error_count})
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        # Try to restore backup if it exists
        try:
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, config_path)
                logger.info(f"Restored configuration from backup after error")
        except Exception as restore_error:
            logger.error(f"Failed to restore backup: {restore_error}")
            
        return jsonify({"error": str(e)}), 500

def _validate_nuki_token(token):
    """Read-only validation of a Nuki Web API token (GET /smartlocks)."""
    try:
        import requests as _requests
        resp = _requests.get(
            "https://api.nuki.io/smartlock",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"valid": True, "detail": "Token accepted by Nuki Web API"}
        if resp.status_code == 401:
            return {"valid": False, "detail": "Nuki rejected this token (401 Unauthorized)"}
        return {"valid": False, "detail": f"Nuki API returned HTTP {resp.status_code}"}
    except Exception as e:
        return {"valid": None, "detail": f"Could not reach Nuki API: {e}"}


def _validate_telegram_token(token):
    """Read-only validation of a Telegram bot token (getMe)."""
    if not token:
        return None
    try:
        import requests as _requests
        resp = _requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        payload = resp.json() if resp.status_code == 200 else {}
        if payload.get("ok"):
            bot_name = payload.get("result", {}).get("username", "bot")
            return {"valid": True, "detail": f"Bot verified: @{bot_name}"}
        return {"valid": False, "detail": "Telegram rejected this bot token"}
    except Exception as e:
        return {"valid": None, "detail": f"Could not reach Telegram: {e}"}


def _persist_config_files():
    """Write config.ini and credentials.ini to disk, credentials locked to 0600."""
    config._save_config(config.config, config.config_path)
    config._save_config(config.credentials, config.credentials_path)
    try:
        os.chmod(config.credentials_path, 0o600)
    except OSError:
        pass


@app.route('/api/setup', methods=['POST'])
def api_setup():
    """Staged setup API — each stage validates and saves IMMEDIATELY so a
    mistake never loses previously entered details.

    Stages:
      admin    -> create the first admin account and log in (required)
      nuki     -> save + live-validate the Nuki API token (recommended)
      telegram -> save Telegram credentials (optional)
      email    -> save email/SMTP settings (optional)

    Telegram and email are explicitly optional: posting an empty payload to
    those stages just advances the wizard.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    stage = data.get('stage', '')
    validation = {}

    try:
        # ---------------------------------------------------------------
        # Stage 1: admin account (the only required stage)
        # ---------------------------------------------------------------
        if stage == 'admin':
            if user_db.users_exist():
                if session.get('setup_stage'):
                    # Resume: this session already created the admin
                    return jsonify({"success": True, "stage": session['setup_stage'],
                                    "message": "Admin account already created"})
                return jsonify({"error": "Setup already completed"}), 403

            admin_username = (data.get('admin_username') or '').strip()
            admin_password = data.get('admin_password') or ''
            admin_confirm = data.get('admin_password_confirm') or ''

            if not admin_username or len(admin_username) < 3:
                return jsonify({"error": "Admin username is required (min. 3 characters)"}), 400
            if len(admin_password) < 8:
                return jsonify({"error": "Admin password must be at least 8 characters"}), 400
            if admin_password != admin_confirm:
                return jsonify({"error": "Passwords do not match"}), 400

            if not user_db.add_user(admin_username, admin_password, role='admin', active=True):
                return jsonify({"error": "Could not create the admin account"}), 500

            # Log the user in immediately and remember wizard progress
            session['logged_in'] = True
            session['username'] = admin_username
            session['role'] = 'admin'
            session['theme'] = 'dark'
            session['setup_stage'] = 2
            logger.info(f"Setup: admin account '{admin_username}' created")

            return jsonify({"success": True, "stage": 2,
                            "message": "Admin account created — details are saved. You can safely continue."})

        # ---------------------------------------------------------------
        # Stages 2-4: require the session that started setup
        # ---------------------------------------------------------------
        if not session.get('logged_in') or not session.get('setup_stage'):
            return jsonify({"error": "Setup session not active"}), 401

        if stage == 'nuki':
            token = (data.get('nuki_token') or '').strip()
            if token:
                if not config.credentials.has_section('Nuki'):
                    config.credentials.add_section('Nuki')
                config.credentials.set('Nuki', 'api_token', token)
                _persist_config_files()
                config.reload()
                validation['nuki'] = _validate_nuki_token(token)
            else:
                # Optional: allow continuing without a token (can add later)
                validation['nuki'] = {"valid": None, "detail": "Skipped — no token entered yet"}
            session['setup_stage'] = 3
            return jsonify({"success": True, "stage": 3, "validation": validation,
                            "message": "Nuki token saved. You can fix it any time in Configuration."})

        if stage == 'telegram':
            bot_token = (data.get('telegram_bot_token') or '').strip()
            chat_id = (data.get('telegram_chat_id') or '').strip()
            if bot_token:
                if not config.credentials.has_section('Telegram'):
                    config.credentials.add_section('Telegram')
                config.credentials.set('Telegram', 'bot_token', bot_token)
            if chat_id:
                if not config.config.has_section('Telegram'):
                    config.config.add_section('Telegram')
                config.config.set('Telegram', 'chat_id', chat_id)
            if bot_token or chat_id:
                _persist_config_files()
                config.reload()
                if bot_token:
                    validation['telegram'] = _validate_telegram_token(bot_token)
            else:
                validation['telegram'] = {"valid": None, "detail": "Skipped — you can add Telegram later in Notifications"}
            session['setup_stage'] = 4
            return jsonify({"success": True, "stage": 4, "validation": validation,
                            "message": "Telegram settings saved."})

        if stage == 'email':
            fields = {
                'email_username': ('credentials', 'Email', 'username'),
                'email_password': ('credentials', 'Email', 'password'),
                'email_smtp_server': ('config', 'Email', 'smtp_server'),
                'email_smtp_port': ('config', 'Email', 'smtp_port'),
                'email_sender': ('config', 'Email', 'sender'),
                'email_recipient': ('config', 'Email', 'recipient'),
            }
            provided = False
            for key, (target, section, name) in fields.items():
                value = (data.get(key) or '').strip()
                if not value:
                    continue
                provided = True
                store = config.credentials if target == 'credentials' else config.config
                if not store.has_section(section):
                    store.add_section(section)
                store.set(section, name, value)
            if provided:
                _persist_config_files()
                config.reload()
            else:
                validation['email'] = {"valid": None, "detail": "Skipped — you can add email later in Notifications"}
            session['setup_stage'] = 5
            return jsonify({"success": True, "stage": 5, "validation": validation,
                            "message": "Email settings saved."})

        if stage == 'done':
            session.pop('setup_stage', None)
            return jsonify({"success": True, "message": "Setup complete"})

        return jsonify({"error": f"Unknown setup stage: {stage}"}), 400
    except Exception as e:
        logger.error(f"Error during setup stage '{stage}': {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
@login_required
def stats():
    """Statistics page"""
    return render_template('stats.html')

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """API endpoint to get usage statistics"""
    try:
        # Get parameters
        days = int(request.args.get('days', 30))
        
        # Get locks
        locks = api.get_smartlocks()
        if not locks:
            # No locks visible (e.g. token not yet configured) — return a
            # clean empty statistics payload instead of an error
            return jsonify({
                "by_user": [], "by_action": [], "by_hour": {}, "by_day": {},
                "total_events": 0
            })

        all_activity = []

        # Get activity for each lock
        for lock in locks:
            lock_id = lock.get('smartlockId')
            lock_name = lock.get('name', 'Unknown Lock')

            # Get activity logs (get more data for stats)
            activity = api.get_smartlock_logs(lock_id, limit=100)
            
            # Filter by date if needed
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_activity = []
            
            for event in activity:
                event_date = api.parse_date(event.get('date'))
                if event_date and event_date >= cutoff_date:
                    # Add lock name to event
                    event['lockName'] = lock_name
                    filtered_activity.append(event)
            
            all_activity.extend(filtered_activity)
        
        # No activity found
        if not all_activity:
            return jsonify({
                "by_user": [],
                "by_action": [],
                "by_hour": [0] * 24,
                "by_day": [0] * 7,
                "total_events": 0
            })
        
        # Calculate statistics
        user_stats = {}
        action_stats = {}
        hour_stats = [0] * 24
        day_stats = [0] * 7
        
        for event in all_activity:
            # Get event details
            trigger = event.get('trigger')
            auth_id = event.get('authId')
            action = event.get('action')
            date = api.parse_date(event.get('date'))
            
            if not date:
                continue
            
            # Update user stats
            user_name = "Auto Lock" if trigger == 6 else api.get_user_name(auth_id) if auth_id else "Unknown User"
            user_stats[user_name] = user_stats.get(user_name, 0) + 1
            
            # Update action stats
            action_name = api.get_action_description(event)
            action_stats[action_name] = action_stats.get(action_name, 0) + 1
            
            # Update hour stats
            hour = date.hour
            hour_stats[hour] += 1
            
            # Update day stats
            day = date.weekday()
            day_stats[day] += 1
        
        # Format for chart.js
        user_data = [{"name": name, "count": count} for name, count in user_stats.items()]
        user_data.sort(key=lambda x: x["count"], reverse=True)
        
        action_data = [{"name": name, "count": count} for name, count in action_stats.items()]
        action_data.sort(key=lambda x: x["count"], reverse=True)
        
        return jsonify({
            "by_user": user_data,
            "by_action": action_data,
            "by_hour": hour_stats,
            "by_day": day_stats,
            "total_events": len(all_activity)
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/users')
@login_required
def users():
    """User management page"""
    return render_template('users.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """API endpoint to get users"""
    try:
        # Get users from API
        users = api.get_users()
        
        # Format user data
        user_data = []
        for user in users:
            user_id = user.get('id')
            user_name = user.get('name', 'Unknown User')
            user_type = user.get('type', 'Unknown')
            enabled = user.get('enabled', True)
            
            # Create user object
            user_obj = {
                'id': user_id,
                'name': user_name,
                'type': user_type,
                'enabled': enabled
            }
            
            user_data.append(user_obj)
        
        return jsonify(user_data)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/temp-codes')
@agent_access_required
def temp_codes_page():
    """Temporary codes management page"""
    return render_template('temp_codes.html')

@app.route('/api/temp-codes', methods=['GET'])
@agent_access_required
def get_temp_codes():
    """API endpoint to get temporary codes"""
    try:
        # Clean expired codes
        temp_code_db.clean_expired_codes()
        
        # For agent users, only show codes they created
        if session.get('role') == 'agent':
            codes = temp_code_db.get_codes_by_creator(session.get('username'))
        else:
            # Admins see all codes
            codes = temp_code_db.get_all_codes()
        
        # Add creator names
        for code in codes:
            creator = user_db.get_user(code.get('created_by'))
            if creator:
                code['creator_name'] = code.get('created_by')
            else:
                code['creator_name'] = 'Unknown'
        
        return jsonify(codes)
    except Exception as e:
        logger.error(f"Error getting temporary codes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/temp-codes', methods=['POST'])
@agent_access_required
def create_temp_code():
    """API endpoint to create a temporary code"""
    try:
        # Get data from request
        data = request.json
        code = data.get('code')
        name = data.get('name')
        expiry = data.get('expiry')
        
        if not code or not name or not expiry:
            return jsonify({"error": "Code, name, and expiry are required"}), 400
        
        # Validate code format (4-8 digits)
        if not code.isdigit() or len(code) < 4 or len(code) > 8:
            return jsonify({"error": "Code must be 4-8 digits"}), 400
        
        # Get first smartlock ID (we'll use the first one for simplicity)
        locks = api.get_smartlocks()
        if not locks:
            return jsonify({"error": "No smartlocks found"}), 404
        
        # Use the first smartlock
        smartlock_id = locks[0].get('smartlockId')
        
        # Convert expiry to datetime
        expiry_datetime = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        
        # Add code to Nuki API
        result = api.add_temporary_code(smartlock_id, code, name, expiry_datetime)
        
        if not result.get('success'):
            return jsonify({"error": result.get('message', 'Failed to add code to lock')}), 500
        
        # Generate a unique ID for the code
        code_id = str(int(time.time()))
        
        # Add code to database
        success = temp_code_db.add_code(
            code_id=code_id, 
            code=code, 
            name=name, 
            created_by=session.get('username'), 
            expiry=expiry_datetime
        )
        
        if not success:
            # Try to clean up the API authorization if database fails
            auth_id = result.get('auth_id')
            if auth_id:
                api.remove_code(smartlock_id, auth_id)
            return jsonify({"error": "Failed to save code to database"}), 500
        
        # Record the auth_id in our database for easier cleanup later
        temp_code_db.update_code(code_id, {"auth_id": result.get('auth_id')})
        
        return jsonify({
            "id": code_id,
            "code": code,
            "name": name,
            "created_by": session.get('username'),
            "created_at": datetime.now().isoformat(),
            "expiry": expiry_datetime.isoformat(),
            "auth_id": result.get('auth_id')
        })
    except Exception as e:
        logger.error(f"Error creating temporary code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/temp-codes/<code_id>', methods=['DELETE'])
@agent_access_required
def delete_temp_code(code_id):
    """API endpoint to delete a temporary code"""
    try:
        # Get code from database
        code = temp_code_db.get_code(code_id)
        if not code:
            return jsonify({"error": "Code not found"}), 404
        
        # Check permissions for agent users
        if session.get('role') == 'agent' and code.get('created_by') != session.get('username'):
            return jsonify({"error": "You can only delete codes you created"}), 403
        
        # Get the auth_id
        auth_id = code.get('auth_id')
        
        # If no auth_id stored, try to find it
        if not auth_id:
            # Get first smartlock ID
            locks = api.get_smartlocks()
            if not locks:
                return jsonify({"error": "No smartlocks found"}), 404
            
            # Use the first smartlock
            smartlock_id = locks[0].get('smartlockId')
            
            # Find auth_id by code value
            auth_id = api.find_auth_id_by_code(smartlock_id, code.get('code'))
        
        # If we have an auth_id, delete from API
        if auth_id:
            # Get first smartlock ID
            locks = api.get_smartlocks()
            if locks:
                smartlock_id = locks[0].get('smartlockId')
                api.remove_code(smartlock_id, auth_id)
        
        # Delete from database
        success = temp_code_db.delete_code(code_id)
        if not success:
            return jsonify({"error": "Failed to delete code from database"}), 500
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting temporary code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/create-agency', methods=['GET', 'POST'])
@admin_required
def create_agency_user():
    """Admin page to create agent users"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            active = 'active' in request.form
            
            if not all([username, password, email]):
                flash('Username, password, and email are required', 'danger')
                return redirect(url_for('create_agency_user'))
            
            if user_db.user_exists(username):
                flash('Username already exists', 'danger')
                return redirect(url_for('create_agency_user'))
            
            # Create the agent user
            success = user_db.add_user(username, password, 'agent', active)
            
            if success:
                flash('Agent user created successfully', 'success')
                return redirect(url_for('users_manage'))
            else:
                flash('Failed to create agent user', 'danger')
                return redirect(url_for('create_agency_user'))
                
        except Exception as e:
            logger.error(f"Error creating agent user: {e}")
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('create_agency_user'))
    
    return render_template('create_agency.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Docker healthchecks"""
    try:
        # Check if config files exist
        config_dir = os.environ.get('CONFIG_DIR', os.path.join(parent_dir, 'config'))
        config_file = os.path.join(config_dir, 'config.ini')
        creds_file = os.path.join(config_dir, 'credentials.ini')
        
        config_exists = os.path.exists(config_file)
        creds_exists = os.path.exists(creds_file)
        
        # Check logs directory is writable
        logs_dir = os.path.join(parent_dir, 'logs')
        logs_writable = os.access(logs_dir, os.W_OK)
        
        # Calculate uptime (simple version since we don't store start time)
        uptime = "healthy"
        
        # Create status response
        status = {
            "status": "healthy" if (config_exists and creds_exists and logs_writable) else "warning",
            "uptime": uptime,
            "config_files": {
                "config.ini": config_exists,
                "credentials.ini": creds_exists
            },
            "permissions": {
                "logs_writable": logs_writable
            },
            "timestamp": int(time.time())
        }
        
        if not logs_writable:
            logger.warning("Logs directory is not writable - this may cause issues")
            status["message"] = "Directory permission issues detected. See TROUBLESHOOTING.md"
        
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }), 500

# Helper function to filter sensitive data for non-admin users
def filter_api_response_for_role(response):
    """Filter API responses to remove sensitive data for non-admin users"""
    if not response.is_json:
        return response
    
    # Only filter for non-admin users
    if 'logged_in' not in session or session.get('role') == 'admin':
        return response
    
    # Check if this is a sensitive API endpoint
    sensitive_endpoints = [
        '/api/config',
        '/api/status'
    ]
    
    is_sensitive = False
    for endpoint in sensitive_endpoints:
        if request.path.startswith(endpoint):
            is_sensitive = True
            break
    
    if not is_sensitive:
        return response
    
    try:
        # Get JSON data
        data = response.get_json()
        
        # Filter status endpoint to remove sensitive information
        if request.path.startswith('/api/status'):
            # Remove personal email and telegram details
            if isinstance(data, list):
                for lock in data:
                    if 'email_details' in lock:
                        lock.pop('email_details')
                    if 'telegram_details' in lock:
                        lock.pop('telegram_details')
        
        # Filter config endpoint (should be blocked by decorator, but just in case)
        if request.path.startswith('/api/config'):
            # Prepare limited config data for non-admin users
            limited_data = {}
            
            # Only include public configuration options
            if 'general' in data:
                limited_data['general'] = {
                    'polling_interval': data['general'].get('polling_interval')
                }
            
            data = limited_data
        
        # Set the modified data
        response.set_data(json.dumps(data))
    except Exception as e:
        logger.error(f"Error filtering API response: {e}")
    
    return response

# Apply theme to all responses and filter sensitive data
@app.after_request
def apply_theme_and_filter(response):
    # Apply dark theme to HTML responses
    if 'logged_in' in session and session.get('theme') == 'dark':
        # Only apply to HTML responses
        if response.content_type and 'text/html' in response.content_type:
            response_data = response.get_data(as_text=True)
            # Add dark-theme class to body
            if '<body>' in response_data and 'dark-theme' not in response_data:
                response_data = response_data.replace('<body>', '<body class="dark-theme">')
                response.set_data(response_data)
            # Add dark mode CSS link if not present
            if '<head>' in response_data and 'dark-mode.css' not in response_data:
                css_link = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/dark-mode.css\') }}">' 
                response_data = response_data.replace('</head>', f'{css_link}\n</head>')
                response.set_data(response_data)
    
    # Filter sensitive data for non-admin users
    response = filter_api_response_for_role(response)
    
    return response

# Development entry point (the container runs gunicorn instead).
# NOTE: no default user is created here — the first admin account comes from
# the Setup Wizard at /setup on first run.
if __name__ == '__main__':
    app.run(
        debug=os.environ.get('DEBUG', 'false').lower() == 'true',
        host=os.environ.get('WEB_HOST', '127.0.0.1'),
        port=int(os.environ.get('WEB_PORT', '5000')),
    )
