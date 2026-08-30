# Agent Access (Temporary Codes) Documentation

This document describes the Agent functionality in the Nuki Smart Lock Notification System — letting a trusted person (a cleaner, a property manager, a family member) create temporary access codes for the Nuki Smart Lock without giving them full administrator access.

## Overview

The Agent feature allows designated users to create temporary access codes for the Nuki Smart Lock without having full administrator privileges. This is useful for property management agencies who need to provide temporary access to maintenance workers, cleaners, etc.

## Features

- **Role-Based Access Control**: The `agent` role can manage temporary codes and view basic lock information
- **Temporary Code Management**: Create, view, and delete temporary access codes
- **Isolated Permissions**: Agent users can only manage codes they created
- **Expiration Handling**: Automatic expiration and cleanup of expired codes
- **Audit Trail**: Records of who created each code and when

## User Roles

The system supports two user roles:

1. **Admin** — Full access to all system features, created during the Setup Wizard
2. **Agent** — Can view lock status and create/manage temporary codes only (admins create agent accounts via **Admin → Create Agent User**)

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
- Agent users see only codes they created

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
- Agent users can only delete codes they created

### Security Considerations

1. **Data Isolation**: Agent users can only view and manage codes they created
2. **API Restrictions**: Permission checks on all API endpoints
3. **Audit Trail**: All code creation and deletion actions are logged
4. **Automatic Cleanup**: Expired codes are automatically marked as inactive

## User Interface

The temporary code management interface is available to both admin and agent users via the "Temporary Codes" link in the main navigation.

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

### Creating Agent Users
As an administrator, you can create new agent users:

1. Go to Admin → Create Agent User
2. Fill out the form with the agent user's details:
   - Username
   - Password
3. Click "Create Agent User" and share the credentials with that person securely

## Docker Deployment

All data persists on the host through bind mounts (see [DOCKER_GUIDE.md](../DOCKER_GUIDE.md)):

- `./config` — configuration files
- `./data` — data files including temporary codes
- `./logs` — application logs

## Maintenance

Regular maintenance tasks:

1. **Code Cleanup**: The system automatically marks expired codes as inactive
2. **Security Audit**: Regularly review the active codes and agency users
3. **Backup**: The code database is included in the standard backup routine
