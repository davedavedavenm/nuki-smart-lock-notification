import pytest
import os


def test_dockerfile_content():
    dockerfile_path = "Dockerfile"
    assert os.path.exists(dockerfile_path), "Dockerfile does not exist"

    with open(dockerfile_path, "r") as f:
        content = f.read()

    # Slim Debian base, pinned Python minor version
    assert "python:3.13-slim" in content, "Dockerfile should use python:3.13-slim base image"

    # Non-root user
    assert "useradd" in content, "Dockerfile should create a non-root user"
    assert "USER nuki" in content, "Dockerfile should switch to non-root user 'nuki'"

    # Production WSGI server, not flask dev server
    assert "gunicorn" in content, "Dockerfile should install gunicorn"

    # Healthcheck present
    assert "HEALTHCHECK" in content, "Dockerfile should define a healthcheck"

    # No secrets baked in
    assert "SECRET_KEY" not in content, "Dockerfile must not set SECRET_KEY"
