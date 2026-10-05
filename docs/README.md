# Email Marketing Automation Platform - Backend

A complete Django REST API backend for an email marketing automation platform with JWT authentication, multi-tenant organization support, and comprehensive security features.

## Features

- **JWT Authentication** with token refresh and blacklisting
- **Multi-tenant Organization** support with role-based access control
- **Custom User Model** with email as username
- **Password Management** (reset, change)
- **Email Verification** token system
- **Security Features**:
  - Brute force protection (Django Axes)
  - CORS configuration
  - Password validation
  - Token blacklisting on logout
- **RESTful API** with comprehensive documentation (Swagger/ReDoc)
- **Comprehensive Test Suite** with pytest
- **Health Check Endpoints** for monitoring
- **Docker Support** for easy deployment

## Tech Stack

- **Django 5.0+** - Web framework
- **Django REST Framework 3.14+** - REST API
- **PostgreSQL** - Primary database
- **Redis** - Caching and sessions
- **JWT (Simple JWT)** - Authentication
- **pytest** - Testing
- **Docker & Docker Compose** - Containerization

## Project Structure

```
Email-Automation/
├── apps/
│   ├── accounts/              # User authentication & management
│   │   ├── management/
│   │   │   └── commands/      # Custom management commands
│   │   ├── tests/             # Test suite
│   │   ├── models.py          # User, Organization, Token models
│   │   ├── serializers.py     # API serializers
│   │   ├── views.py           # API views
│   │   ├── urls.py            # URL routing
│   │   ├── admin.py           # Admin configuration
│   │   └── signals.py         # Signal handlers
│   └── core/                  # Core functionality
│       ├── models.py          # Base models
│       ├── permissions.py     # Custom permissions
│       ├── exceptions.py      # Exception handlers
│       ├── views.py           # Health check endpoints
│       └── urls.py            # Core URLs
├── config/
│   ├── settings/
│   │   ├── base.py           # Base settings
│   │   ├── development.py    # Development settings
│   │   ├── production.py     # Production settings
│   │   └── test.py           # Test settings
│   ├── urls.py               # Root URL configuration
│   ├── wsgi.py               # WSGI configuration
│   └── asgi.py               # ASGI configuration
├── manage.py
├── requirements.txt
├── .env.example
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- Redis 7+ (optional, for caching)
- Docker & Docker Compose (optional)

### Option 1: Local Development Setup

1. **Clone the repository**
   ```bash
   cd E:\Projects\Email-Automation
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   copy .env.example .env  # On Windows
   # cp .env.example .env  # On Linux/Mac
   ```

   Edit `.env` and update the values:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///db.sqlite3
   # Or for PostgreSQL:
   # DATABASE_URL=postgresql://user:password@localhost:5432/email_automation
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Create test data (optional)**
   ```bash
   python manage.py create_test_data
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at: `http://localhost:8000`

### Option 2: Docker Setup

1. **Set up environment variables**
   ```bash
   copy .env.example .env
   ```

2. **Build and run containers**
   ```bash
   docker-compose up -d --build
   ```

3. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Create test data (optional)**
   ```bash
   docker-compose exec web python manage.py create_test_data
   ```

The API will be available at: `http://localhost:8000`

## API Endpoints

### Authentication

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/auth/register/` | POST | Register new user and organization | No |
| `/api/v1/auth/login/` | POST | Login and get JWT tokens | No |
| `/api/v1/auth/logout/` | POST | Logout and blacklist refresh token | Yes |
| `/api/v1/auth/token/refresh/` | POST | Refresh access token | No |
| `/api/v1/auth/profile/` | GET | Get user profile | Yes |
| `/api/v1/auth/profile/` | PUT/PATCH | Update user profile | Yes |
| `/api/v1/auth/change-password/` | POST | Change password | Yes |
| `/api/v1/auth/password-reset/` | POST | Request password reset | No |
| `/api/v1/auth/password-reset/confirm/` | POST | Confirm password reset | No |

### Health Check

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/health/health/` | GET | Health check | No |
| `/api/v1/health/ready/` | GET | Readiness probe | No |
| `/api/v1/health/live/` | GET | Liveness probe | No |

### API Documentation

- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

## API Usage Examples

### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "My Company"
  }'
```

Response:
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
    "role": "owner"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "Registration successful"
}
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Get User Profile

```bash
curl -X GET http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Profile

```bash
curl -X PATCH http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "phone": "+1234567890"
  }'
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

### Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

### Password Reset Request

```bash
curl -X POST http://localhost:8000/api/v1/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### Password Reset Confirm

```bash
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-from-email",
    "new_password": "NewSecurePass123!",
    "new_password_confirm": "NewSecurePass123!"
  }'
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=apps --cov-report=html
```

### Run specific test file
```bash
pytest apps/accounts/tests/test_models.py
```

### Run specific test class
```bash
pytest apps/accounts/tests/test_api.py::TestRegistrationAPI
```

### Run specific test
```bash
pytest apps/accounts/tests/test_api.py::TestRegistrationAPI::test_register_success
```

View coverage report: Open `htmlcov/index.html` in a browser

## Database Models

### Organization
- Multi-tenant organization model
- Fields: name, slug, plan, email, contact info, limits
- Supports soft deletion

### User
- Custom user model with email as username
- Fields: email, name, organization, role, profile info
- Roles: owner, admin, member, viewer
- Inherits from AbstractBaseUser and PermissionsMixin

### PasswordResetToken
- Tokens for password reset functionality
- Auto-expiration after 1 hour
- Single-use tokens

### EmailVerificationToken
- Tokens for email verification
- Auto-expiration configurable

## Security Features

### Authentication
- JWT token-based authentication
- Refresh token rotation
- Token blacklisting on logout
- Configurable token lifetime

### Password Security
- Strong password validation
- Password complexity requirements
- Secure password hashing (PBKDF2)
- Password reset with time-limited tokens

### Brute Force Protection
- Django Axes integration
- Configurable failure limit
- IP-based lockout
- Automatic cooldown period

### CORS
- Configurable allowed origins
- Credential support
- Development and production configs

### Additional Security
- CSRF protection
- XSS protection headers
- Content type sniffing protection
- Clickjacking protection
- SSL redirect in production

## Management Commands

### Create Test Data
```bash
python manage.py create_test_data
```
Creates test organizations and users for development.

Test credentials:
- Email: `owner@test-startup-inc.com`
- Password: `testpass123`

### Clear Test Data
```bash
python manage.py create_test_data --clear
```

### Setup Initial Data
```bash
python manage.py setup_initial_data
```
Sets up initial superuser for production.

## Development

### Code Formatting
```bash
black apps/
isort apps/
```

### Linting
```bash
flake8 apps/
```

### Type Checking
```bash
mypy apps/
```

## Deployment

### Environment Variables (Production)

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
EMAIL_BACKEND=anymail.backends.amazon_ses.EmailBackend
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Run Migrations
```bash
python manage.py migrate --noinput
```

### Run with Gunicorn
```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 config.wsgi:application
```

## Monitoring

### Health Check Endpoints

- **Health**: `/api/v1/health/health/` - Checks database and cache
- **Readiness**: `/api/v1/health/ready/` - Kubernetes readiness probe
- **Liveness**: `/api/v1/health/live/` - Kubernetes liveness probe

### Logging

Logs are stored in `logs/django.log` with rotation enabled.

Configure log level in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
psql -U postgres -h localhost -p 5432

# Test database connection
python manage.py dbshell
```

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Test Redis connection
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
```

### Migration Issues
```bash
# Show migrations
python manage.py showmigrations

# Reset migrations (development only!)
python manage.py migrate accounts zero
python manage.py migrate

# Create new migration
python manage.py makemigrations
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Run tests and linting
5. Submit a pull request

## License

Proprietary - All rights reserved

## Support

For issues and questions, please contact the development team.

---

Built with Django 5.0+ and Django REST Framework 3.14+
