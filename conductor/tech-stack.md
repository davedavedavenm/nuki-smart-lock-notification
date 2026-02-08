# Technology Stack - Nuki Smart Lock Notification System

## Core Languages & Runtimes
- **Python 3.6+**: The primary programming language for both the monitoring daemon and the web dashboard.

## Frameworks & Libraries
- **Flask**: A lightweight WSGI web application framework used for the web interface and API endpoints.
- **Requests**: Used for robust HTTP interactions with the Nuki Web API and Telegram Bot API.
- **Passlib & Cryptography**: Employed for secure password hashing and encryption of sensitive data.
- **Python-Dateutil**: Handles complex date and time manipulations for activity logging and temporary code management.

## Frontend
- **Bootstrap CSS**: The foundational framework for a responsive, modern UI with Light/Dark mode support.
- **Vanilla JavaScript**: Used for interactive dashboard elements and real-time status updates.

## Infrastructure & Deployment
- **Docker & Docker Compose**: The primary deployment method, providing a fully containerized environment for all services.
- **SQLite (Implied/Standard)**: Likely used for local storage of user data and activity logs (managed via Flask models).

## External Integrations
- **Nuki Web API**: The source of truth for lock status and activity events.
- **Telegram Bot API**: Used for delivering instant push notifications to users.
