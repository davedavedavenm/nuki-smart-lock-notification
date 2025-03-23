#!/usr/bin/env python3
"""
This module adds a health check endpoint to the Flask web interface.
Import it in app.py and register the blueprint.
"""

from flask import Blueprint, jsonify, current_app
import os
import time
import logging
import psutil
import sys
import platform

# Get the start time when the module is loaded
start_time = time.time()

# Create Blueprint
health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Health check endpoint for Docker healthchecks and monitoring.
    Returns system status and uptime information.
    """
    try:
        # Get application logger
        logger = current_app.logger
        
        # Check if config files exist
        config_dir = os.environ.get('CONFIG_DIR', '/app/config')
        config_file = os.path.join(config_dir, 'config.ini')
        creds_file = os.path.join(config_dir, 'credentials.ini')
        
        config_exists = os.path.exists(config_file)
        creds_exists = os.path.exists(creds_file)
        
        # Calculate uptime
        uptime_seconds = int(time.time() - start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Get system statistics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_used_percent = memory.percent
        disk = psutil.disk_usage('/')
        disk_used_percent = disk.percent
        
        # Create status response
        status = {
            "status": "healthy",
            "application": {
                "uptime": uptime,
                "uptime_seconds": uptime_seconds,
                "python_version": sys.version,
                "platform": platform.platform(),
            },
            "config_files": {
                "config_dir": config_dir,
                "config.ini": config_exists,
                "credentials.ini": creds_exists
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_used_percent,
                "disk_percent": disk_used_percent
            },
            "timestamp": int(time.time())
        }
        
        # Log health check
        logger.debug(f"Health check performed: status={status['status']}")
        
        return jsonify(status), 200
    except Exception as e:
        error_message = str(e)
        try:
            current_app.logger.error(f"Health check failed: {error_message}")
        except:
            # Fallback if logger is not available
            print(f"Health check failed: {error_message}", file=sys.stderr)
            
        return jsonify({
            "status": "unhealthy",
            "error": error_message,
            "timestamp": int(time.time())
        }), 500
