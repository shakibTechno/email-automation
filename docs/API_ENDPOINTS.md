# API Endpoints Reference

Complete reference for all API endpoints in the Email Marketing Automation Platform.

## Base URL

- **Development**: `http://127.0.0.1:8000`
- **Production**: `https://your-domain.com`

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Authentication Endpoints

### 1. Register User

Create a new user account and organization.

**Endpoint**: `POST /api/v1/auth/register/`

**Authentication**: Not required

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "organization_name": "My Company",
  "phone": "+1234567890",
  "timezone": "UTC",
  "language": "en"
}
```

**Required Fields**: email, password, password_confirm, first_name, last_name, organization_name

**Response** (201 Created):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "organization": {
      "id": "uuid",
      "name": "My Company",
      "slug": "my-company",
      "plan": "free"
    },
    "role": "owner",
    "is_active": true,
    "is_email_verified": false
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "Registration successful"
}
```

### 2. Login

Authenticate user and receive JWT tokens.

**Endpoint**: `POST /api/v1/auth/login/`

**Authentication**: Not required

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "organization": {...},
    "role": "owner"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "Login successful"
}
```

### 3. Logout

Logout user and blacklist refresh token.

**Endpoint**: `POST /api/v1/auth/logout/`

**Authentication**: Required

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response** (205 Reset Content):
```json
{
  "message": "Logout successful"
}
```

### 4. Refresh Token

Get a new access token using refresh token.

**Endpoint**: `POST /api/v1/auth/token/refresh/`

**Authentication**: Not required

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## User Profile Endpoints

### 5. Get User Profile

Retrieve current user's profile information.

**Endpoint**: `GET /api/v1/auth/profile/`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "organization": {
    "id": "uuid",
    "name": "My Company",
    "slug": "my-company",
    "plan": "starter",
    "email": "contact@mycompany.com"
  },
  "role": "owner",
  "is_active": true,
  "is_email_verified": true,
  "phone": "+1234567890",
  "avatar": "https://example.com/avatar.jpg",
  "timezone": "UTC",
  "language": "en",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T00:00:00Z",
  "last_login": "2024-01-20T10:30:00Z"
}
```

### 6. Update User Profile

Update current user's profile information.

**Endpoint**: `PUT /api/v1/auth/profile/` or `PATCH /api/v1/auth/profile/`

**Authentication**: Required

**Request Body**:
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+9876543210",
  "avatar": "https://example.com/new-avatar.jpg",
  "timezone": "America/New_York",
  "language": "es"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  ...
}
```

---

## Password Management Endpoints

### 7. Change Password

Change password for authenticated user.

**Endpoint**: `POST /api/v1/auth/change-password/`

**Authentication**: Required

**Request Body**:
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass123!@#",
  "new_password_confirm": "NewPass123!@#"
}
```

**Response** (200 OK):
```json
{
  "message": "Password changed successfully"
}
```

### 8. Password Reset Request

Request a password reset token (sent via email).

**Endpoint**: `POST /api/v1/auth/password-reset/`

**Authentication**: Not required

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "If a user with that email exists, a password reset link has been sent."
}
```

### 9. Password Reset Confirm

Reset password using token from email.

**Endpoint**: `POST /api/v1/auth/password-reset/confirm/`

**Authentication**: Not required

**Request Body**:
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123!",
  "new_password_confirm": "NewSecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "message": "Password reset successful"
}
```

---

## Health Check Endpoints

### 10. Health Check

Check application health status.

**Endpoint**: `GET /api/v1/health/health/`

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "healthy",
  "database": "healthy",
  "cache": "healthy"
}
```

### 11. Readiness Check

Kubernetes readiness probe endpoint.

**Endpoint**: `GET /api/v1/health/ready/`

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "ready"
}
```

### 12. Liveness Check

Kubernetes liveness probe endpoint.

**Endpoint**: `GET /api/v1/health/live/`

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "alive"
}
```

---

## Error Responses

All endpoints return consistent error responses:

**Format**:
```json
{
  "error": true,
  "message": "Error description",
  "details": {
    "field_name": ["Error message for this field"]
  },
  "status_code": 400
}
```

**Common Status Codes**:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Request successful, no content to return
- `205 Reset Content`: Request successful, reset content (logout)
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Rate Limiting

API endpoints are protected by rate limiting:

- Failed login attempts: 5 attempts per hour (configurable)
- After limit reached: 1 hour cooldown period

---

## Token Lifetimes

- **Access Token**: 60 minutes (configurable)
- **Refresh Token**: 7 days (configurable)
- **Password Reset Token**: 1 hour
- **Email Verification Token**: 24 hours

---

## Pagination

List endpoints support pagination (default: 20 items per page):

**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

**Response Format**:
```json
{
  "count": 100,
  "next": "http://api.example.com/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## Filtering and Searching

List endpoints support filtering and searching:

**Query Parameters**:
- `search`: Search term
- `ordering`: Sort field (prefix with `-` for descending)

Example: `?search=john&ordering=-created_at`

---

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **ReDoc**: `http://127.0.0.1:8000/api/redoc/`
- **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`

---

## CURL Examples

### Register
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","password_confirm":"Test123!","first_name":"Test","last_name":"User","organization_name":"Test Co"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

### Get Profile
```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Profile
```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Updated"}'
```

---

## Postman Collection

Import the following into Postman for easy testing:

1. Create a new Collection: "Email Marketing API"
2. Add Base URL variable: `{{base_url}}` = `http://127.0.0.1:8000`
3. Add Token variable: `{{access_token}}`
4. Add requests from the examples above

---

For more information, see:
- README.md - Complete project documentation
- SETUP_GUIDE.md - Setup and installation guide
- TECHNICAL_ARCHITECTURE.md - Technical specifications
