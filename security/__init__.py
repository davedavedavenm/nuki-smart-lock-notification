"""
Nuki Smart Lock Security Module

This package provides security monitoring and alerting for the Nuki Smart Lock system.
It detects suspicious activity patterns and generates priority security alerts.
"""

from .security_monitor import SecurityMonitor
from .security_alerter import SecurityAlerter

# Module version
__version__ = '0.1.0'
