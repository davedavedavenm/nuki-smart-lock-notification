import os
import pytest
import sys
from unittest.mock import MagicMock

# Add scripts to path so we can import nuki
sys.path.append(os.path.join(os.getcwd(), "scripts"))

from nuki.config import ConfigManager

def test_config_env_prioritization(tmp_path):
    # Setup temp config files
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.ini"
    creds_file = config_dir / "credentials.ini"
    
    with open(config_file, "w") as f:
        f.write("[General]\nnotification_type = both\n")
    
    with open(creds_file, "w") as f:
        f.write("[Nuki]\napi_token = file_token\n")
    
    # Set env vars
    os.environ["NUKI_NOTIFICATION_TYPE"] = "telegram"
    os.environ["NUKI_API_TOKEN"] = "env_token"
    os.environ["CONFIG_DIR"] = str(config_dir)
    
    # Initialize ConfigManager
    cm = ConfigManager(base_dir=str(tmp_path))
    
    # Check prioritization
    assert cm.notification_type == "telegram", f"Expected 'telegram' from env, got {cm.notification_type}"
    assert cm.api_token == "env_token", f"Expected 'env_token' from env, got {cm.api_token}"
    
    # Clean up
    del os.environ["NUKI_NOTIFICATION_TYPE"]
    del os.environ["NUKI_API_TOKEN"]
    del os.environ["CONFIG_DIR"]