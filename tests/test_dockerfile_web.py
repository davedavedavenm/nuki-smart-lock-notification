import pytest
import os

def test_dockerfile_web_content():
    dockerfile_path = "Dockerfile.web"
    assert os.path.exists(dockerfile_path), "Dockerfile.web does not exist"
    
    with open(dockerfile_path, "r") as f:
        content = f.read()
        
    # Check for slim base image
    assert "slim" in content or "alpine" in content, "Dockerfile.web should use a slim or alpine base image"
    
    # Check for non-root user usage
    assert "useradd" in content, "Dockerfile.web should create a non-root user"
    assert "USER nuki" in content, "Dockerfile.web should switch to non-root user 'nuki'"
    
    # Check for Gunicorn
    assert "gunicorn" in content, "Dockerfile.web should use gunicorn for production serving"
    
    # Verify curl is installed for healthcheck
    assert "curl" in content, "Dockerfile.web should install curl for healthchecks"
