# Management Agency Access Documentation

This document outlines the implementation of the Management Agency functionality in the Nuki Smart Lock Notification System.

## Overview

The Management Agency feature allows designated users to create temporary access codes for the Nuki Smart Lock without having full administrator privileges. This feature is useful for property management agencies who need to provide temporary access to maintenance workers, cleaners, etc.

## Features

- **Role-Based Access Control**: New 'agency' role added to the user system
- **Temporary Code Management**: Create, view, and delete temporary access codes
- **Isolated Permissions**: Agency users can only manage codes they created
- **Expiration Handling**: Automatic expiration and cleanup of expired codes
- **Audit Trail**: Records of who created each code and when

## User Roles

The system now supports three user roles:

1. **Admin** - Full access to all system features
2. **Agency** - Can create and manage temporary codes only
3. **User** - Standard user with view-only access (cannot create codes)

## Technical Implementation

### Database Structure

Temporary codes are stored in a JSON file (`temp_codes.json`) with the following structure:

```json
{
  "code_id": {
    "code": "1234",
    "name": "Description or purpose",
    "created_by": "username",
    "created_at": "ISO datetime",
    "expiry": "ISO datetime",
    "is_active": true,
    "last_used": null,
    "auth_id": "nuki_auth_id"
  }
}
```

### API Endpoints

#### GET /api/temp-codes
Returns all temporary codes visible to the current user.
- Admin users see all codes
- Agency users see only codes they created

#### POST /api/temp-codes
Creates a new temporary code.

Request body:
```json
{
  "code": "1234",
  "name": "Description or purpose",
  "expiry": "ISO datetime"
}
```

#### DELETE /api/temp-codes/{code_id}
Deletes a temporary code.
- Admin users can delete any code
- Agency users can only delete codes they created

### Security Considerations

1. **Data Isolation**: Agency users can only view and manage codes they created
2. **API Restrictions**: Permission checks on all API endpoints
3. **Audit Trail**: All code creation and deletion actions are logged
4. **Automatic Cleanup**: Expired codes are automatically marked as inactive

## User Interface

The temporary code management interface is available to both admin and agency users via the "Temporary Codes" link in the main navigation.

### Creating Codes
1. Navigate to the Temporary Codes page
2. Fill out the form with:
   - Code (4-8 digit numeric code)
   - Name/Purpose (description of the code)
   - Expiry date and time
3. Click "Create Temporary Code"

### Deleting Codes
1. Navigate to the Temporary Codes page
2. Find the code in the list
3. Click the "Delete" button
4. Confirm the deletion

## For Administrators

### Creating Agency Users
As an administrator, you can create new agency users:

1. Go to Admin → Create Agency User
2. Fill out the form with the agency user's details:
   - Username
   - Email
   - Password
3. Click "Create Agency User"

## Docker Deployment

The implementation uses Docker volumes to ensure data persistence:

- `config-volume`: Configuration files
- `logs-volume`: Log files
- `data-volume`: Data files including temporary codes

## Maintenance

Regular maintenance tasks:

1. **Code Cleanup**: The system automatically marks expired codes as inactive
2. **Security Audit**: Regularly review the active codes and agency users
3. **Backup**: The code database is included in the standard backup routine
