# Track Specification: Complete Full Docker Containerization and Environment Stabilization

## Overview
This track focuses on transforming the current mixed deployment state into a fully optimized and stabilized Docker-only environment. This includes optimizing Dockerfiles, refining volume management, securing sensitive data via environment variables, and ensuring seamless communication between the monitoring and web services.

## User Stories
- As a **Tech Enthusiast**, I want to deploy the entire system with a single 'docker compose up' command.
- As an **Admin**, I want my configuration and logs to persist even if the containers are updated or removed.
- As a **Developer**, I want a consistent development environment that mirrors the production environment on my Raspberry Pi.

## Functional Requirements
- Refine 'Dockerfile.monitor' and 'Dockerfile.web' for size and security (non-root users).
- Optimize 'docker-compose.yml' for production use, including health checks.
- Implement a robust strategy for handling 'config.ini' and 'credentials.ini' using environment variables or Docker Secrets.
- Ensure automated startup and recovery of all containers.

## Non-Functional Requirements
- **Portability**: The containers must run consistently on both x86 (for development) and ARM64 (Raspberry Pi 4).
- **Maintainability**: Clear documentation for updating tokens and configurations within the Docker context.
- **Security**: Minimize container privileges and ensure sensitive data is not baked into images.

## Acceptance Criteria
- Both 'nuki-monitor' and 'nuki-web' services start reliably via 'docker compose'.
- Web interface is accessible at the configured port.
- Notifications are correctly triggered from within the containerized monitor.
- All persistent data (logs, database, configs) survives container restarts.
