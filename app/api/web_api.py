"""
Web API endpoints for Nuki Smart Lock Notification System.
Provides REST API functionality for monitoring and configuration.
"""
import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from functools import wraps

# Import authentication module
from app.web.models import user_db

# Configure logging
logger = logging.getLogger('nuki_monitor')

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# API authentication decorator
def require_api_key(view_function):
    """Decorator to require API key for API endpoints."""
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        # Validate API key
        if not user_db.validate_api_key(api_key):
            logger.warning(f"Invalid API key attempt: {request.remote_addr}")
            return jsonify({'error': 'Invalid API key'}), 403
            
        return view_function(*args, **kwargs)
    return decorated_function

# Health check endpoint (no authentication required)
@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API availability."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': current_app.config.get('VERSION', '1.0.0')
    })

# Lock status endpoints
@api_bp.route('/locks', methods=['GET'])
@require_api_key
def get_locks():
    """Get status of all configured locks."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get locks data
        locks = nuki_api.get_locks()
        
        return jsonify({
            'status': 'success',
            'count': len(locks),
            'locks': locks
        })
    except Exception as e:
        logger.error(f"Error getting locks: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/locks/<lock_id>', methods=['GET'])
@require_api_key
def get_lock(lock_id):
    """Get status of a specific lock."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get lock data
        lock = nuki_api.get_lock(lock_id)
        
        if not lock:
            return jsonify({'status': 'error', 'message': 'Lock not found'}), 404
            
        return jsonify({
            'status': 'success',
            'lock': lock
        })
    except Exception as e:
        logger.error(f"Error getting lock {lock_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/locks/<lock_id>/actions', methods=['POST'])
@require_api_key
def lock_action(lock_id):
    """Perform action on a specific lock."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get action from request
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'status': 'error', 'message': 'Action is required'}), 400
            
        action = data['action'].lower()
        valid_actions = ['lock', 'unlock', 'unlatch', 'lock_n_go', 'lock_n_go_unlatch']
        
        if action not in valid_actions:
            return jsonify({
                'status': 'error', 
                'message': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
            }), 400
            
        # Execute action
        result = nuki_api.execute_action(lock_id, action)
        
        return jsonify({
            'status': 'success',
            'action': action,
            'lock_id': lock_id,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error executing {action} on lock {lock_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Activity endpoints
@api_bp.route('/activity', methods=['GET'])
@require_api_key
def get_activity():
    """Get recent activity for all locks."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get query parameters
        limit = request.args.get('limit', default=10, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # Validate parameters
        if limit < 1 or limit > 100:
            return jsonify({'status': 'error', 'message': 'Limit must be between 1 and 100'}), 400
            
        if offset < 0:
            return jsonify({'status': 'error', 'message': 'Offset must be non-negative'}), 400
            
        # Get activity data
        activity = nuki_api.get_activity(limit=limit, offset=offset)
        
        return jsonify({
            'status': 'success',
            'count': len(activity),
            'limit': limit,
            'offset': offset,
            'activity': activity
        })
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/activity/<lock_id>', methods=['GET'])
@require_api_key
def get_lock_activity(lock_id):
    """Get recent activity for a specific lock."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get query parameters
        limit = request.args.get('limit', default=10, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # Validate parameters
        if limit < 1 or limit > 100:
            return jsonify({'status': 'error', 'message': 'Limit must be between 1 and 100'}), 400
            
        if offset < 0:
            return jsonify({'status': 'error', 'message': 'Offset must be non-negative'}), 400
            
        # Get activity data for specific lock
        activity = nuki_api.get_lock_activity(lock_id, limit=limit, offset=offset)
        
        return jsonify({
            'status': 'success',
            'lock_id': lock_id,
            'count': len(activity),
            'limit': limit,
            'offset': offset,
            'activity': activity
        })
    except Exception as e:
        logger.error(f"Error getting activity for lock {lock_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# User endpoints
@api_bp.route('/users', methods=['GET'])
@require_api_key
def get_users():
    """Get all users associated with locks."""
    try:
        # Get Nuki API instance from the application context
        nuki_api = current_app.nuki_api
        
        # Get users data
        users = nuki_api.get_users()
        
        return jsonify({
            'status': 'success',
            'count': len(users),
            'users': users
        })
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Configuration endpoints
@api_bp.route('/config', methods=['GET'])
@require_api_key
def get_config():
    """Get current configuration (non-sensitive settings only)."""
    try:
        # Get configuration manager instance from the application context
        config_manager = current_app.config_manager
        
        # Get non-sensitive configuration
        config = config_manager.get_safe_config()
        
        return jsonify({
            'status': 'success',
            'config': config
        })
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/config', methods=['POST'])
@require_api_key
def update_config():
    """Update configuration settings."""
    try:
        # Get configuration manager instance from the application context
        config_manager = current_app.config_manager
        
        # Get settings from request
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No configuration data provided'}), 400
            
        # Validate settings
        if not isinstance(data, dict):
            return jsonify({'status': 'error', 'message': 'Configuration must be a JSON object'}), 400
            
        # Prevent updating sensitive settings via API
        sensitive_sections = ['Credentials', 'Security']
        for section in sensitive_sections:
            if section in data:
                return jsonify({
                    'status': 'error', 
                    'message': f'Cannot update sensitive section: {section}'
                }), 403
                
        # Update settings
        updated = config_manager.update_config(data)
        
        if updated:
            return jsonify({
                'status': 'success',
                'message': 'Configuration updated successfully'
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Failed to update configuration'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# System status endpoint
@api_bp.route('/system/status', methods=['GET'])
@require_api_key
def system_status():
    """Get system status information."""
    try:
        # Get system status information
        from app.monitoring.health_monitor import run_health_check
        
        # Run health check with web service check
        health_result = run_health_check(check_web=True)
        
        # Get additional system information
        import psutil
        import os
        from datetime import timedelta
        
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get uptime
        uptime_seconds = int(psutil.boot_time())
        uptime = str(timedelta(seconds=int(datetime.now().timestamp() - uptime_seconds)))
        
        # Get version information
        version = current_app.config.get('VERSION', '1.0.0')
        
        return jsonify({
            'status': 'success',
            'health': {
                'status': 'healthy' if health_result else 'unhealthy',
            },
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'uptime': uptime
            },
            'version': version,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def init_app(app):
    """Initialize API blueprint with the Flask app."""
    app.register_blueprint(api_bp)
    logger.info("API endpoints registered")
