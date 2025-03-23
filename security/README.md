# Nuki Smart Lock Security Alerting Module

## Overview

The Security Alerting Module enhances the Nuki Smart Lock Notification System by adding advanced detection and alerting for suspicious activity patterns. This module works alongside the existing notification system to provide an additional layer of security monitoring.

## Features

- Detection of multiple failed access attempts
- Unusual access time monitoring
- Multiple access attempts from different users in short periods
- Geolocation validation (optional)
- Priority alerting for security concerns
- Customizable security thresholds
- Detailed security logs and audit trail

## Implementation

The module integrates with the existing Nuki notification system without requiring major changes to the core functionality.

### Components

1. **Pattern Detection Engine**: Analyzes activity logs to identify suspicious patterns
2. **Alert Manager**: Handles security alerts with higher priority than regular notifications
3. **Configuration Module**: Allows customization of security thresholds and settings
4. **Security Dashboard**: Web interface component for monitoring security events

## Installation

1. Install the security module files:

```bash
# Copy security module files
mkdir -p /root/nukiweb/scripts/security
cp security_monitor.py /root/nukiweb/scripts/security/
cp security_alerter.py /root/nukiweb/scripts/security/
cp __init__.py /root/nukiweb/scripts/security/
```

2. Update the configuration:

```bash
# Add security section to config
/root/nukiweb/scripts/configure.py update --section Security --option enabled --value true
```

3. Restart the notification service:

```bash
systemctl restart nuki-monitor.service
```

## Configuration

The security module has several configurable parameters:

### Thresholds

- `failed_attempts_threshold`: Number of failed attempts before alerting (default: 3)
- `failed_attempts_window`: Time window for counting failed attempts in seconds (default: 300)
- `unusual_hour_start`: Start of quiet hours (default: 23)
- `unusual_hour_end`: End of quiet hours (default: 6)
- `rapid_access_threshold`: Number of access events in short period (default: 5)
- `rapid_access_window`: Time window for rapid access in seconds (default: 60)

### Alert Settings

- `alert_priority`: Priority level for security alerts (default: high)
- `alert_sound`: Enable sound for security alerts (default: true)
- `notify_owner_only`: Send security alerts only to owner (default: true)
- `include_evidence`: Include detailed evidence in alerts (default: true)

## Usage

Once installed and configured, the security module runs automatically alongside the main notification system. Security alerts will be sent via the configured notification methods (email and/or Telegram) with distinct formatting to highlight their importance.

### Web Dashboard Integration

When used with the web dashboard, security events will appear in a dedicated security section with proper highlighting. The dashboard will also display security statistics and trends.

## Technical Operation

The security module works by:

1. **Monitoring Activity**: Continuously analyzing the activity log
2. **Pattern Recognition**: Applying pattern recognition algorithms to detect suspicious activity
3. **Context Analysis**: Evaluating context (time, user, location) for each event
4. **Alert Generation**: Creating prioritized alerts for suspicious patterns
5. **Logging**: Maintaining detailed security logs for auditing purposes

## Example Patterns Detected

### Multiple Failed Access Attempts

```
2025-03-23 14:52:53 [WARNING] Security: 3 failed access attempts within 2 minutes
2025-03-23 14:53:12 [ALERT] Security: Failed access threshold exceeded (4 attempts)
```

### Unusual Hours Access

```
2025-03-23 02:15:35 [NOTICE] Security: Access during unusual hours by User3
```

### Rapid Multiple Access

```
2025-03-23 13:30:01 [WARNING] Security: 5 access events within 45 seconds
```

## Implementation Files

### security_monitor.py

The main monitoring component that analyzes activity patterns and detects suspicious behavior.

### security_alerter.py

Handles the generation and delivery of security alerts through the notification system.

### security_config.py

Manages security-specific configuration options.

## Integration with Existing System

The security module integrates with the existing notification system by:

1. Subscribing to activity events
2. Analyzing events in parallel to normal processing
3. Using the same notification channels with higher priority for alerts
4. Sharing the same configuration system with security-specific sections

## Future Enhancements

- Machine learning for anomaly detection
- User behavior profiling
- Geographic access restrictions
- Two-factor authentication integration
- Integration with home security systems
- Mobile push notifications for critical alerts

## Troubleshooting

- If security alerts aren't being generated, check that the module is enabled in the configuration
- To reduce false positives, adjust the threshold settings
- For detailed debugging, enable debug mode in the advanced configuration

## Requirements

- Nuki Smart Lock Notification System (v1.0+)
- Python 3.6+
- Access to Nuki API
