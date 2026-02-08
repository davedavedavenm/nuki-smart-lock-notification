import pytest
import os

def test_dockerfile_monitor_content():
    dockerfile_path = "Dockerfile.monitor"
    assert os.path.exists(dockerfile_path), "Dockerfile.monitor does not exist"
    
    with open(dockerfile_path, "r") as f:
        content = f.read()
        
    # Check for slim base image
    assert "slim" in content or "alpine" in content, "Dockerfile.monitor should use a slim or alpine base image"
    
    # Check for non-root user usage
    # We expect the user creation and switching to be uncommented
    assert "useradd" in content, "Dockerfile.monitor should create a non-root user"
    assert "USER nuki" in content, "Dockerfile.monitor should switch to non-root user 'nuki'"
    
    # Check that we are NOT running as root (the comment saying we are should be gone or changed)
    assert "Running as root to handle filesystem permissions" not in content, "Dockerfile.monitor should not explicitly state it runs as root"
