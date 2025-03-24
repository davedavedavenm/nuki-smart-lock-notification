# Nuki App Project Changes

This document describes the changes made to fix three specific issues in the Nuki Smart Lock Notification System.

## 1. Configuration Saving Error Fix

The error when trying to save configurations, particularly when setting to "Telegram Only", has been fixed with the following improvements:

1. **Added Backup Mechanism**: The system now automatically creates a backup of the configuration file before making changes
2. **Improved Error Handling**: Each configuration update is now handled individually so a single error won't cause the entire update to fail
3. **File Permission Setting**: Explicitly sets secure permissions (0o640) on the configuration file after updates
4. **Validation for Notification Type**: Ensures notification_type cannot be saved as empty
5. **Automatic Restoration**: If an error occurs during the update, the backup is automatically restored

Location of changes: `web/app.py` in the `update_config` route

## 2. User Profile Password Change Functionality

Implemented full functionality for the user profile page to allow users to change their passwords:

1. **New API Endpoint**: Added the `/api/profile` endpoint that handles:
   - Password changing (with current password verification)
   - Theme preference updates
2. **Security**: Ensures current password is verified before allowing changes
3. **Logging**: Added proper logging for user profile changes

Location of changes: `web/app.py` - new `update_profile` route

## 3. Dark Mode Style Improvements

Enhanced the dark mode styling to fix contrast issues and improve consistency:

1. **Better Contrast**: Improved color contrast between text and backgrounds
2. **Fixed Navbar**: Enhanced navbar styling with proper hover and active states
3. **Card Text Colors**: Fixed text colors within cards that were previously too dark
4. **Form Elements**: Improved styling for disabled form elements and helper text
5. **Navigation Tabs**: Fixed styling for the navigation tabs in the configuration page
6. **Added Styling for Additional Elements**: Added missing dark mode styling for:
   - Toast notifications
   - Dashboard cards
   - Text elements (headings, leads, etc.)
   - Containers and fluid containers

Location of changes: `web/static/css/dark-mode.css`

## How to Deploy These Changes

1. **Local Testing**:
   - Make sure the Flask app is running in debug mode
   - Test the configuration saving with various options
   - Test user password changing functionality
   - Check dark mode styling across different pages

2. **Pushing to GitHub**:
   ```bash
   cd C:\Users\Dave\OneDrive\Claude\NukiAppProject\consolidated_code
   git add web/app.py
   git add web/static/css/dark-mode.css
   git add CHANGES.md
   git commit -m "Fix configuration saving, add password change and improve dark mode"
   git push origin main
   ```

3. **Deploying to Raspberry Pi**:
   - Using SSH:
     ```bash
     ssh root@your-pi-ip
     cd /root/nukiweb
     git pull
     systemctl restart nuki-web.service
     ```
   
   - Or using Docker:
     ```bash
     ssh root@your-pi-ip
     cd /root/nukiweb
     git pull
     docker-compose down
     docker-compose up -d
     ```

## Additional Notes

- These changes maintain backward compatibility with existing configurations
- No database schema changes were required
- The dark mode improvements should work with both traditional and Docker deployments
