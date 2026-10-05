#!/usr/bin/env python
"""
Initialization script for the Email Marketing Automation Platform.
This script performs initial setup tasks for development.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}")


def print_info(text):
    """Print info message."""
    print(f"→ {text}")


def run_command(command, description):
    """Run a command and return success status."""
    print_info(f"{description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print_success(description)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed!")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is 3.11+."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python 3.11+ required. Current: {version.major}.{version.minor}.{version.micro}")
        return False


def check_virtual_env():
    """Check if running in virtual environment."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Running in virtual environment")
        return True
    else:
        print_error("Not running in virtual environment")
        print_info("Create and activate a virtual environment first:")
        print("  python -m venv venv")
        print("  venv\\Scripts\\activate  (Windows)")
        print("  source venv/bin/activate  (Linux/Mac)")
        return False


def check_env_file():
    """Check if .env file exists."""
    env_file = Path('.env')
    env_example = Path('.env.example')

    if env_file.exists():
        print_success(".env file exists")
        return True
    elif env_example.exists():
        print_info("Creating .env from .env.example...")
        shutil.copy(env_example, env_file)
        print_success("Created .env file")
        print_info("Please update .env with your settings before continuing")
        return True
    else:
        print_error(".env.example not found")
        return False


def create_logs_directory():
    """Create logs directory."""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        logs_dir.mkdir()
        print_success("Created logs directory")
    else:
        print_success("Logs directory exists")
    return True


def main():
    """Main initialization function."""
    print_header("Email Marketing Automation Platform - Initialization")

    print("This script will set up your development environment.\n")

    # Check Python version
    print_header("Step 1: Checking Python Version")
    if not check_python_version():
        sys.exit(1)

    # Check virtual environment
    print_header("Step 2: Checking Virtual Environment")
    if not check_virtual_env():
        sys.exit(1)

    # Check/create .env file
    print_header("Step 3: Setting up Environment Variables")
    if not check_env_file():
        sys.exit(1)

    # Create logs directory
    print_header("Step 4: Creating Required Directories")
    create_logs_directory()

    # Install dependencies
    print_header("Step 5: Installing Dependencies")
    if not run_command("pip install -r requirements.txt", "Installing Python packages"):
        print_info("You can install dependencies manually: pip install -r requirements.txt")

    # Run migrations
    print_header("Step 6: Setting up Database")
    if not run_command("python manage.py migrate", "Running database migrations"):
        print_error("Migration failed. Please run manually: python manage.py migrate")

    # Create superuser (optional)
    print_header("Step 7: Create Admin User (Optional)")
    print_info("You can create a superuser account now or later.")
    response = input("Create superuser now? (y/n): ").lower()
    if response == 'y':
        print_info("Running: python manage.py createsuperuser")
        subprocess.run("python manage.py createsuperuser", shell=True)

    # Create test data (optional)
    print_header("Step 8: Create Test Data (Optional)")
    print_info("Create test organizations and users for development?")
    response = input("Create test data? (y/n): ").lower()
    if response == 'y':
        if run_command("python manage.py create_test_data", "Creating test data"):
            print_info("\nTest credentials:")
            print("  Email: owner@test-startup-inc.com")
            print("  Password: testpass123")

    # Final instructions
    print_header("Setup Complete!")
    print("Your development environment is ready!\n")
    print("Next steps:")
    print("  1. Review and update .env file with your settings")
    print("  2. Start the development server:")
    print("     python manage.py runserver")
    print("\n  3. Access the application:")
    print("     - API Root: http://127.0.0.1:8000/api/v1/")
    print("     - Admin: http://127.0.0.1:8000/admin/")
    print("     - API Docs: http://127.0.0.1:8000/api/docs/")
    print("\n  4. Run tests:")
    print("     pytest")
    print("\n  5. Test the API:")
    print("     python test_api.py")
    print("\nFor detailed instructions, see SETUP_GUIDE.md")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
