# Security Policy

## Supported Versions

We currently support the following versions of the Nuki Smart Lock Notification System with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately via GitHub:

1. Go to the repository's **Security** tab
2. Click **"Report a vulnerability"** (private vulnerability reporting)

Alternatively, open a GitHub issue asking for a private contact channel —
without including any vulnerability details. Reports are reviewed promptly.

Please include the following information in your report:

- Type of vulnerability
- Steps to reproduce the vulnerability
- Potential impact
- Suggestions for mitigation (if any)

Please do not disclose security vulnerabilities publicly until they have been addressed by the maintainers.

## Security Considerations

### API Tokens and Credentials

- API tokens and credentials should be stored in the `credentials.ini` file, which is excluded from version control
- File permissions for `credentials.ini` should be set to `600` (read/write for owner only)
- Never hardcode sensitive information in the source code

### Network Security

- All communication with the Nuki API uses HTTPS
- The web interface should be secured with HTTPS if exposed to the internet
- Consider using a reverse proxy (e.g., Nginx, Apache) with HTTPS for the web interface

### Container Security

The Docker deployment (see [DOCKER_GUIDE.md](DOCKER_GUIDE.md)):

- Runs a **single container** as a non-root user (UID/GID 999)
- Bakes **no secrets into the image** — `.env`, `credentials.ini`, logs,
  sessions and data are excluded from the build context via `.dockerignore`
- Requires `SECRET_KEY` to be provided via `.env`; no insecure fixed default
  exists (an ephemeral key is generated if unset)
- Publishes only port 5000; front it with an HTTPS reverse proxy if exposed
- Images are built from `python:3.13-slim` and kept updated

### User Management

- Passwords are hashed and not stored in plaintext (PBKDF2 via Werkzeug)
- **No default credentials**: a fresh install has no user accounts until you
  create the first admin in the Setup Wizard; the wizard closes permanently
  once an account exists (and stays closed if the users file is corrupt —
  fail closed)
- **Passkeys (WebAuthn)**: optional phishing-resistant login via
  fingerprint/face/device PIN, registered per-user from the profile page.
  Requires a secure context (HTTPS or localhost); passwords remain available
  as a fallback
- Proper access controls are implemented for the web interface
- Session management includes timeouts, HttpOnly cookies, and a
  `WEB_HTTPS=true` opt-in for Secure cookies behind reverse proxies

## Security Best Practices for Installation

1. Set a strong, unique `SECRET_KEY` in `.env` before first start
2. Restrict access to the `config/` directory (it contains live credentials)
3. Keep the host and the Docker image updated with the latest security patches
4. Use strong passwords for all web users
5. If exposing the web interface, put it behind an HTTPS reverse proxy
6. Enable firewall rules to restrict access to necessary ports only
7. Use secure communication channels for host access (SSH keys, not passwords)
8. Run `python sanitize_check.py` before committing; CI enforces this scan
