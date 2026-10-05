"""
Simple script to test the authentication API endpoints.
Run this after starting the development server.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"


def print_response(response, title):
    """Print formatted response."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_health_check():
    """Test health check endpoint."""
    response = requests.get(f"{BASE_URL}/health/health/")
    print_response(response, "Health Check")
    return response.status_code == 200


def test_registration():
    """Test user registration."""
    data = {
        "email": "testuser@example.com",
        "password": "TestPass123!@#",
        "password_confirm": "TestPass123!@#",
        "first_name": "Test",
        "last_name": "User",
        "organization_name": "Test Organization"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=data)
    print_response(response, "User Registration")

    if response.status_code == 201:
        return response.json()
    return None


def test_login(email, password):
    """Test user login."""
    data = {
        "email": email,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=data)
    print_response(response, "User Login")

    if response.status_code == 200:
        return response.json()
    return None


def test_get_profile(access_token):
    """Test getting user profile."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    print_response(response, "Get User Profile")
    return response.status_code == 200


def test_update_profile(access_token):
    """Test updating user profile."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "first_name": "Updated",
        "phone": "+1234567890"
    }
    response = requests.patch(f"{BASE_URL}/auth/profile/", json=data, headers=headers)
    print_response(response, "Update User Profile")
    return response.status_code == 200


def test_refresh_token(refresh_token):
    """Test token refresh."""
    data = {
        "refresh": refresh_token
    }
    response = requests.post(f"{BASE_URL}/auth/token/refresh/", json=data)
    print_response(response, "Refresh Access Token")

    if response.status_code == 200:
        return response.json()
    return None


def test_logout(access_token, refresh_token):
    """Test user logout."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "refresh": refresh_token
    }
    response = requests.post(f"{BASE_URL}/auth/logout/", json=data, headers=headers)
    print_response(response, "User Logout")
    return response.status_code == 205


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("EMAIL MARKETING AUTOMATION API TESTS")
    print("=" * 60)
    print("\nMake sure the development server is running:")
    print("python manage.py runserver")
    print("\nStarting tests...")

    # Test health check
    if not test_health_check():
        print("\n❌ Health check failed! Make sure the server is running.")
        return

    # Test registration
    print("\n\n--- Testing Registration ---")
    registration_data = test_registration()
    if not registration_data:
        print("\n⚠️  Registration failed (user might already exist)")
        # Try login instead
        print("\nTrying login with existing credentials...")
        login_data = test_login("testuser@example.com", "TestPass123!@#")
    else:
        print("\n✅ Registration successful!")
        login_data = registration_data

    if not login_data:
        print("\n❌ Cannot proceed without authentication")
        return

    access_token = login_data.get('tokens', {}).get('access')
    refresh_token = login_data.get('tokens', {}).get('refresh')

    # Test profile retrieval
    print("\n\n--- Testing Profile Retrieval ---")
    if test_get_profile(access_token):
        print("✅ Profile retrieval successful!")
    else:
        print("❌ Profile retrieval failed!")

    # Test profile update
    print("\n\n--- Testing Profile Update ---")
    if test_update_profile(access_token):
        print("✅ Profile update successful!")
    else:
        print("❌ Profile update failed!")

    # Test token refresh
    print("\n\n--- Testing Token Refresh ---")
    refresh_data = test_refresh_token(refresh_token)
    if refresh_data:
        print("✅ Token refresh successful!")
        # Update access token
        access_token = refresh_data.get('access', access_token)
        if 'refresh' in refresh_data:
            refresh_token = refresh_data['refresh']
    else:
        print("❌ Token refresh failed!")

    # Test logout
    print("\n\n--- Testing Logout ---")
    if test_logout(access_token, refresh_token):
        print("✅ Logout successful!")
    else:
        print("❌ Logout failed!")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("Make sure the development server is running:")
        print("python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Error: {e}")
