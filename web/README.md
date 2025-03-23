# Nuki Smart Lock Web Dashboard

A web-based dashboard for the Nuki Smart Lock Notification System.

## Features

- View lock status and activity in real-time
- Browse and filter activity logs
- View usage statistics and analytics
- Manage user access
- Configure system settings
- Mobile-responsive design

## Installation

### Prerequisites

- Python 3.6+
- Flask and related packages
- Working Nuki Smart Lock Notification System

### Setup

1. Install required packages:

```bash
cd /root/nukiweb
source venv/bin/activate
pip install flask flask-login werkzeug
```

2. Start the web server:

```bash
cd /root/nukiweb/web
python app.py
```

For production deployment, it's recommended to use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -b 0.0.0.0:5000 app:app
```

## Usage

Access the dashboard by navigating to `http://your-raspberry-pi-ip:5000` in your web browser.

Default login credentials:
- Username: admin
- Password: nukiadmin

**Important:** Change the default password after first login by editing the `app.py` file.

## Pages

### Dashboard
The main overview page showing lock status, recent activity, and system statistics.

### Activity Log
View, filter, and export detailed activity logs.

### Lock Status
View current lock status and perform lock operations.

### Statistics
Visualize usage patterns and trends with charts and graphs.

### Users
View and manage user access.

### Configuration
Configure system settings, notification preferences, and more.

## Security Considerations

- The web interface uses basic authentication
- For enhanced security, consider:
  - Setting up HTTPS
  - Implementing stronger authentication
  - Restricting access to local network only
  - Using a reverse proxy like Nginx

## Customization

You can customize the appearance by modifying the CSS and JavaScript files:

- `static/css/style.css` - Custom styling
- `static/js/main.js` - Common JavaScript functions

To modify page templates, edit the files in the `templates` directory:

- `templates/base.html` - Main layout template
- `templates/index.html` - Dashboard template
- And so on for other pages

## Adding Active Lock Control

To enable active control of the lock (lock/unlock/unlatch operations), you'll need to:

1. Implement the API endpoints in `app.py` for these operations
2. Add proper authentication and validation to prevent unauthorized access
3. Update the status page to use these endpoints

Example implementation for lock control endpoints:

```python
@app.route('/api/lock/<lock_id>/lock', methods=['POST'])
@login_required
def lock_action(lock_id):
    # Perform lock action via Nuki API
    # Return success/failure
    pass
```

## Troubleshooting

- If the dashboard can't connect to the Nuki API, check that:
  - The Nuki notification service is running
  - API credentials are valid
  - Network connectivity is working
  
- If charts or statistics aren't loading, verify that:
  - JavaScript is enabled in your browser
  - The browser has access to external CDN resources

## Future Enhancements

Planned enhancements for the web dashboard include:

- User account management system
- Role-based access control
- Real-time updates using WebSockets
- Email notifications for security alerts
- Customizable dashboard layout
- Dark mode theme option
- Mobile app integration

## Contributing

Contributions to improve the web dashboard are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
