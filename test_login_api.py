#!/usr/bin/env python
"""
Test the login API directly
"""
import requests
import json

def test_login_api():
    """Test login API with various scenarios"""

    base_url = "http://127.0.0.1:8000/api/v1"

    print("=" * 60)
    print("Testing Login API")
    print("=" * 60)

    # Test 1: Check if API is reachable
    print("\n1️⃣ Testing API health...")
    try:
        response = requests.get(f"{base_url}/health/health/", timeout=5)
        if response.status_code == 200:
            print("   ✅ API is reachable")
        else:
            print(f"   ❌ API returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot reach API: {e}")
        print("   Make sure backend is running: python manage.py runserver")
        return

    # Test 2: Test with valid format
    print("\n2️⃣ Testing login with correct format...")
    login_data = {
        "email": "test@example.com",
        "password": "Test123!@#"
    }

    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

        if response.status_code == 200:
            print("   ✅ Login successful!")
            data = response.json()
            print(f"   User: {data.get('user', {}).get('email')}")
        elif response.status_code == 400:
            print("   ❌ Bad Request (Validation Error)")
            try:
                error_data = response.json()
                print(f"   Error Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Raw Response: {response.text}")
        elif response.status_code == 401:
            print("   ❌ Unauthorized (Invalid credentials)")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Request failed: {e}")

    # Test 3: Test with missing fields
    print("\n3️⃣ Testing with missing password...")
    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: Test with extra fields
    print("\n4️⃣ Testing with extra fields...")
    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            json={
                "email": "test@example.com",
                "password": "Test123!@#",
                "remember_me": False
            },
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 5: Test with wrong content type
    print("\n5️⃣ Testing with form-urlencoded...")
    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            data=login_data,  # form-encoded instead of JSON
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60 + "\n")

    print("\n💡 Next Steps:")
    print("   1. Make sure a user exists: python check_user.py")
    print("   2. Check frontend is sending correct data")
    print("   3. Share the browser Network tab response")

if __name__ == '__main__':
    try:
        test_login_api()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
