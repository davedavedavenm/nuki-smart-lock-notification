import os
import sys
import pytest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from scripts.nuki.config import ConfigManager

def test_is_configured_logic():
    # Mock base_dir
    base_dir = "."
    
    # Allow missing token for testing
    os.environ["ALLOW_MISSING_TOKEN"] = "true"
    
    # Initialize with no token
    os.environ["NUKI_API_TOKEN"] = ""
    cm = ConfigManager(base_dir)
    # Force api_token to empty if env var didn't clear it
    cm.api_token = ""
    assert cm.is_configured is False
    
    # Initialize with token
    cm.api_token = "valid_token"
    assert cm.is_configured is True
    
    # Clean up
    if "NUKI_API_TOKEN" in os.environ:
        del os.environ["NUKI_API_TOKEN"]
    if "ALLOW_MISSING_TOKEN" in os.environ:
        del os.environ["ALLOW_MISSING_TOKEN"]

def test_setup_redirect_logic():
    pass