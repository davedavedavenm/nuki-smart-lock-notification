# Security Policy

## Supported Versions

We currently support the following versions of the Nuki Smart Lock Notification System with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to [YOUR_EMAIL]. All security vulnerabilities will be promptly addressed.

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

If using Docker:
- Containers are configured to run as non-root users
- Sensitive information is stored in Docker secrets or environment variables
- Container images are kept updated for security patches

### User Management

- Passwords are hashed and not stored in plaintext
- Proper access controls are implemented for the web interface
- Session management includes timeouts and secure cookie settings

## Security Best Practices for Installation

1. Use a dedicated Raspberry Pi user account with appropriate permissions
2. Restrict access to configuration directories
3. Keep your Raspberry Pi updated with the latest security patches
4. Use strong passwords for all components
5. If exposing the web interface, ensure it's behind a secure reverse proxy
6. Enable firewall rules to restrict access to necessary ports only
7. Use secure communication channels for accessing your Raspberry Pi (SSH keys, not passwords)
