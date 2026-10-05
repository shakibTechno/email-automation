#!/usr/bin/env python
"""
Quick Setup Verification Script
Checks if backend and frontend are properly configured
"""
import os
import sys
import requests
from pathlib import Path

def color_print(text, color):
    """Print colored text"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        color_print(f"✅ {description} exists", 'green')
        return True
    else:
        color_print(f"❌ {description} NOT found at {filepath}", 'red')
        return False

def check_backend_env():
    """Check backend environment configuration"""
    color_print("\n📋 Checking Backend Configuration...", 'blue')

    env_path = Path('.env')
    if not check_file_exists(env_path, "Backend .env file"):
        color_print("   Creating .env from .env.example...", 'yellow')
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            color_print("   ✅ Created .env file", 'green')
        else:
            color_print("   ❌ .env.example not found", 'red')
            return False

    # Check required variables
    required_vars = ['DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS']
    with open(env_path) as f:
        content = f.read()
        missing = []
        for var in required_vars:
            if var not in content:
                missing.append(var)

        if missing:
            color_print(f"   ⚠️  Missing variables: {', '.join(missing)}", 'yellow')
        else:
            color_print("   ✅ All required environment variables present", 'green')

    return True

def check_frontend_env():
    """Check frontend environment configuration"""
    color_print("\n📋 Checking Frontend Configuration...", 'blue')

    env_path = Path('frontend/.env.local')
    if not check_file_exists(env_path, "Frontend .env.local"):
        color_print("   Creating .env.local...", 'yellow')
        with open(env_path, 'w') as f:
            f.write("VITE_API_URL=http://127.0.0.1:8000/api/v1\n")
            f.write("VITE_APP_NAME=Email Marketing Platform\n")
        color_print("   ✅ Created .env.local", 'green')

    # Check API URL
    with open(env_path) as f:
        content = f.read()
        if 'VITE_API_URL=http://127.0.0.1:8000/api/v1' in content:
            color_print("   ✅ API URL correctly configured", 'green')
        else:
            color_print("   ⚠️  API URL may be incorrect", 'yellow')
            if 'VITE_API_URL' in content:
                import re
                url = re.search(r'VITE_API_URL=(.+)', content)
                if url:
                    color_print(f"   Current: {url.group(1)}", 'yellow')
                    color_print("   Expected: http://127.0.0.1:8000/api/v1", 'yellow')

    return True

def check_backend_running():
    """Check if backend server is running"""
    color_print("\n🔍 Checking Backend Server...", 'blue')

    try:
        response = requests.get('http://127.0.0.1:8000/api/v1/health/health/', timeout=2)
        if response.status_code == 200:
            color_print("   ✅ Backend server is running", 'green')
            return True
        else:
            color_print(f"   ⚠️  Backend responded with status {response.status_code}", 'yellow')
            return False
    except requests.exceptions.ConnectionError:
        color_print("   ❌ Backend server is NOT running", 'red')
        color_print("   Run: python manage.py runserver", 'yellow')
        return False
    except Exception as e:
        color_print(f"   ❌ Error checking backend: {e}", 'red')
        return False

def check_frontend_running():
    """Check if frontend server is running"""
    color_print("\n🔍 Checking Frontend Server...", 'blue')

    try:
        response = requests.get('http://localhost:3000/', timeout=2)
        if response.status_code == 200:
            color_print("   ✅ Frontend server is running", 'green')
            return True
        else:
            color_print(f"   ⚠️  Frontend responded with status {response.status_code}", 'yellow')
            return False
    except requests.exceptions.ConnectionError:
        color_print("   ❌ Frontend server is NOT running", 'red')
        color_print("   Run: cd frontend && npm run dev", 'yellow')
        return False
    except Exception as e:
        color_print(f"   ❌ Error checking frontend: {e}", 'red')
        return False

def check_database():
    """Check if database migrations are applied"""
    color_print("\n🗄️  Checking Database...", 'blue')

    if os.path.exists('db.sqlite3'):
        color_print("   ✅ Database file exists", 'green')
    else:
        color_print("   ❌ Database not found", 'red')
        color_print("   Run: python manage.py migrate", 'yellow')
        return False

    return True

def test_api_endpoints():
    """Test key API endpoints"""
    color_print("\n🧪 Testing API Endpoints...", 'blue')

    endpoints = [
        ('Health Check', 'http://127.0.0.1:8000/api/v1/health/health/'),
        ('API Root', 'http://127.0.0.1:8000/api/v1/'),
    ]

    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                color_print(f"   ✅ {name}: OK", 'green')
            else:
                color_print(f"   ⚠️  {name}: Status {response.status_code}", 'yellow')
        except Exception as e:
            color_print(f"   ❌ {name}: Failed - {e}", 'red')

def main():
    """Main verification function"""
    color_print("=" * 60, 'blue')
    color_print("   Email Marketing Platform - Setup Verification", 'blue')
    color_print("=" * 60, 'blue')

    # Check configurations
    backend_env_ok = check_backend_env()
    frontend_env_ok = check_frontend_env()

    # Check database
    db_ok = check_database()

    # Check servers
    backend_ok = check_backend_running()
    if backend_ok:
        test_api_endpoints()

    frontend_ok = check_frontend_running()

    # Summary
    color_print("\n" + "=" * 60, 'blue')
    color_print("   Summary", 'blue')
    color_print("=" * 60, 'blue')

    all_ok = all([backend_env_ok, frontend_env_ok, db_ok, backend_ok, frontend_ok])

    if all_ok:
        color_print("\n✅ Everything is configured correctly!", 'green')
        color_print("\nYou can now:", 'blue')
        color_print("   1. Visit http://localhost:3000 to access the frontend", 'green')
        color_print("   2. Create an account and start using the platform", 'green')
    else:
        color_print("\n⚠️  Some issues found. Please fix them and run again.", 'yellow')

        if not backend_ok:
            color_print("\n📝 To start backend:", 'blue')
            color_print("   python manage.py runserver", 'yellow')

        if not frontend_ok:
            color_print("\n📝 To start frontend:", 'blue')
            color_print("   cd frontend", 'yellow')
            color_print("   npm run dev", 'yellow')

        if not db_ok:
            color_print("\n📝 To setup database:", 'blue')
            color_print("   python manage.py migrate", 'yellow')

    color_print("\n" + "=" * 60 + "\n", 'blue')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        color_print("\n\nVerification cancelled.", 'yellow')
        sys.exit(0)
