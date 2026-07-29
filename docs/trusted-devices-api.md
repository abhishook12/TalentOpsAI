# Trusted Devices API Contract

This document outlines the API endpoints required for the Trusted Devices panel. Currently, these endpoints are mocked on the frontend, but this contract specifies what the FastAPI backend should implement.

## 1. Get Devices
`GET /admin/devices/`
Returns a list of all devices across all users.

**Response (200 OK):**
```json
[
  {
    "id": "dev_123",
    "user_email": "alice@example.com",
    "user_name": "Alice Smith",
    "device_name": "Alice's MacBook Pro",
    "device_type": "laptop",
    "status": "Pending",
    "ip_address": "192.168.1.50",
    "location": "New York, US",
    "last_seen": "2023-10-27T14:32:00Z",
    "first_seen": "2023-10-27T10:00:00Z",
    "active_sessions": 1,
    "tags": ["remote", "vpn"],
    "trust_expires_at": null,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
  }
]
```

## 2. Get Device Stats
`GET /admin/devices/stats`
Returns aggregated statistics for the metric cards.

**Response (200 OK):**
```json
{
  "total": 150,
  "pending": 5,
  "high_risk": 2,
  "active_sessions": 45,
  "blocked_revoked": 12
}
```

## 3. Mutate Device (Action)
`PATCH /admin/devices/{device_id}`
Updates the status, name, or trust expiry of a device.

**Payload:**
```json
{
  "status": "Trusted", // or "Blocked", "Revoked", "Pending"
  "reason": "Routine review", // Required for Block/Revoke/Pending
  "trust_expires_at": "2024-10-27T00:00:00Z", // Optional ISO string
  "device_name": "New Name" // Optional string for renaming
}
```

## 4. Force Re-Verification
`POST /admin/devices/{device_id}/reverify`
Flags a device to require MFA on its next sign-in, without killing active sessions.

**Payload:**
```json
{
  "reason": "Suspicious login attempt" // Optional
}
```

## 5. Terminate Device Sessions
`DELETE /admin/devices/{device_id}/sessions`
Kills all active sessions for the specific device immediately.

## 6. Access Policy Settings
`GET /admin/devices/policy`
`PUT /admin/devices/policy`
Manages the global access policy for trusted devices.

**Payload / Response:**
```json
{
  "auto_approve_networks": true,
  "trusted_cidr": "192.168.1.0/24",
  "require_admin_approval": true,
  "allowed_countries": ["US", "CA", "GB"],
  "block_outside_geography": true,
  "max_devices_per_user": 5,
  "default_trust_duration": 90, // Days
  "auto_revoke_idle_days": 30,
  "notify_on_pending": true
}
```
