import yaml
import os


def _load_compose():
    compose_path = "compose.yaml"
    assert os.path.exists(compose_path), "compose.yaml does not exist"
    with open(compose_path, "r") as f:
        return yaml.safe_load(f)


def test_single_service_design():
    """The deployment is a single container running monitor + web together."""
    config = _load_compose()
    services = config.get("services", {})
    assert list(services.keys()) == ["nuki"], "compose.yaml should define exactly one service: nuki"


def test_no_deprecated_version_key():
    config = _load_compose()
    assert "version" not in config, "compose.yaml must not use the deprecated top-level version key"


def test_service_configuration():
    config = _load_compose()
    service = config["services"]["nuki"]

    assert service.get("restart") == "unless-stopped"
    assert service.get("user") != "root", "nuki should not be explicitly set to run as root"
    assert "healthcheck" in service, "nuki should have a healthcheck"
    assert "init" in service, "nuki should run with init to reap zombie processes"

    # Log rotation configured
    logging = service.get("logging", {})
    assert logging.get("options", {}).get("max-size"), "nuki should configure log rotation"

    # Persistent state volumes
    volumes = service.get("volumes", [])
    assert any("/app/logs" in v for v in volumes), "nuki should have a log volume"
    assert any("/app/config" in v for v in volumes), "nuki should have a config volume"
    assert any("/app/data" in v for v in volumes), "nuki should have a data volume"
    assert any("/app/flask_session" in v for v in volumes), "nuki should have a session volume"

    # No insecure default secret
    secret = service.get("environment", {}).get("SECRET_KEY", "")
    assert "nuki-smart-lock-dashboard-fixed-key" not in str(secret), "SECRET_KEY must not have a fixed default"
