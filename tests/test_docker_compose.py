import yaml
import os

def test_docker_compose_optimization():
    dc_path = "docker-compose.yml"
    assert os.path.exists(dc_path), "docker-compose.yml does not exist"
    
    with open(dc_path, "r") as f:
        config = yaml.safe_load(f)
        
    services = config.get("services", {})
    assert "nuki-monitor" in services
    assert "nuki-web" in services
    
    # Check that nuki-monitor does NOT run as root in compose (if we want it managed by Dockerfile)
    assert services["nuki-monitor"].get("user") != "root", "nuki-monitor should not be explicitly set to run as root in docker-compose.yml"
    
    # Check for healthchecks
    assert "healthcheck" in services["nuki-monitor"]
    assert "healthcheck" in services["nuki-web"]
    
    # Check restart policy
    assert services["nuki-monitor"].get("restart") == "unless-stopped"
    assert services["nuki-web"].get("restart") == "unless-stopped"
    
    # Check logging (optional but good to have)
    # nuki-monitor should have log volume
    volumes_monitor = services["nuki-monitor"].get("volumes", [])
    assert any("/app/logs" in v for v in volumes_monitor), "nuki-monitor should have a log volume"
