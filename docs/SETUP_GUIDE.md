# Quick Setup Guide

## Step-by-Step Setup Instructions

### 1. Install Python Dependencies

```bash
# Navigate to project directory
cd E:\Projects\Email-Automation

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
copy .env.example .env

# Edit .env file and update these key settings:
# - SECRET_KEY: Generate a new secret key
# - DATABASE_URL: Configure your database
# - DEBUG: Set to True for development
```

To generate a secure SECRET_KEY, run:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Set Up Database

#### Option A: SQLite (Quick Start - Development Only)
```bash
# No additional setup needed, Django will create db.sqlite3
# Make sure .env has:
# DATABASE_URL=sqlite:///db.sqlite3
```

#### Option B: PostgreSQL (Recommended)
```bash
# Install PostgreSQL first, then:
# 1. Create database
createdb email_automation

# 2. Update .env with:
# DATABASE_URL=postgresql://username:password@localhost:5432/email_automation
```

### 4. Run Database Migrations

```bash
# Create all database tables
python manage.py migrate
```

### 5. Create Admin User

```bash
# Create superuser account
python manage.py createsuperuser
# Enter email, password when prompted
```

### 6. Create Test Data (Optional)

```bash
# Create test organizations and users
python manage.py create_test_data
```

This creates:
- Test organizations with different plans
- Test users with different roles
- Credentials: owner@test-startup-inc.com / testpass123

### 7. Run Development Server

```bash
# Start Django development server
python manage.py runserver
```

Server will start at: `http://127.0.0.1:8000`

### 8. Access the Application

- **API Root**: http://127.0.0.1:8000/api/v1/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Documentation (Swagger)**: http://127.0.0.1:8000/api/docs/
- **API Documentation (ReDoc)**: http://127.0.0.1:8000/api/redoc/
- **Health Check**: http://127.0.0.1:8000/api/v1/health/health/

## Testing the API

### 1. Register a New User

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123!\",\"password_confirm\":\"TestPass123!\",\"first_name\":\"Test\",\"last_name\":\"User\",\"organization_name\":\"Test Company\"}"
```

### 2. Login

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123!\"}"
```

Save the access token from the response.

### 3. Get Profile (Replace YOUR_TOKEN)

```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/profile/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=apps --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

## Docker Setup (Alternative)

If you prefer using Docker:

```bash
# Build and start containers
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Create test data
docker-compose exec web python manage.py create_test_data

# View logs
docker-compose logs -f web

# Stop containers
docker-compose down
```

## Troubleshooting

### Port Already in Use
```bash
# Windows: Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Database Connection Error
```bash
# Check PostgreSQL is running
# Windows: Check Services
# Linux/Mac: systemctl status postgresql

# Test connection
psql -U postgres -h localhost
```

### Redis Connection Error (Optional)
```bash
# Redis is optional for basic setup
# Set in .env for in-memory cache:
# REDIS_URL=locmem://
```

### Migration Issues
```bash
# Reset database (development only!)
python manage.py flush

# Run migrations again
python manage.py migrate
```

## Next Steps

1. **Explore API Documentation**: Visit http://127.0.0.1:8000/api/docs/
2. **Test Endpoints**: Use the Swagger UI or tools like Postman
3. **Read API Documentation**: Check README.md for detailed endpoint information
4. **Run Tests**: Execute `pytest` to ensure everything works
5. **Customize Settings**: Modify config/settings/development.py as needed

## Common Commands Reference

```bash
# Run development server
python manage.py runserver

# Run tests
pytest

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Show all URLs
python manage.py show_urls  # requires django-extensions

# Collect static files
python manage.py collectstatic

# Clear test data
python manage.py create_test_data --clear
```

## Environment Variables Reference

Key environment variables in `.env`:

```env
# Django Core
DEBUG=True
SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=config.settings.development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
# Or PostgreSQL: postgresql://user:pass@localhost:5432/dbname

# Redis (Optional)
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@example.com

# Security
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1

# Logging
LOG_LEVEL=INFO
```

## Support

If you encounter issues:

1. Check logs in `logs/django.log`
2. Enable DEBUG mode in `.env`
3. Check the Troubleshooting section above
4. Review Django and DRF documentation

---

Happy coding!
