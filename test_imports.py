import sys
import os
import pytest

def test_web_imports():
    """Test that all modules in web package can be imported"""
    # Get the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add project root to path if not already
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Test importing web modules
    import web.app
    import web.models
    import web.temp_codes
    
    # Assert modules are properly initialized
    assert hasattr(web.app, 'app')
    assert hasattr(web.models, 'User')
    assert hasattr(web.models, 'UserDatabase')
    assert hasattr(web.temp_codes, 'TemporaryCodeDatabase')
