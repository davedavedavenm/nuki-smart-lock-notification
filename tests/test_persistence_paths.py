import os
import sys
import pytest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from scripts.nuki.config import ConfigManager
from scripts.nuki.utils import ActivityTracker
from web.models import UserDatabase
from web.temp_codes import TemporaryCodeDatabase

def test_persistence_paths(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["CONFIG_DIR"] = str(tmp_path / "config")
    os.mkdir(tmp_path / "config")
    
    # Test ActivityTracker
    tracker = ActivityTracker(str(data_dir))
    assert tracker.last_activity_path == os.path.join(str(data_dir), "last_activity.json")
    
    # Test UserDatabase
    user_db = UserDatabase(str(data_dir))
    assert user_db.users_file == os.path.join(str(data_dir), "users.json")
    
    # Test TemporaryCodeDatabase
    temp_db = TemporaryCodeDatabase(str(data_dir))
    assert temp_db.codes_file == os.path.join(str(data_dir), "temp_codes.json")
    
    # Clean up
    del os.environ["DATA_DIR"]
    del os.environ["CONFIG_DIR"]
