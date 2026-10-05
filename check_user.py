#!/usr/bin/env python
"""
Quick script to check if user exists and create test user if needed
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import User, Organization

def main():
    print("=" * 60)
    print("User Database Check")
    print("=" * 60)

    # Check all users
    users = User.objects.all()
    print(f"\nTotal users in database: {users.count()}")

    if users.exists():
        print("\n📋 Existing Users:")
        for user in users:
            print(f"\n  Email: {user.email}")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  Active: {user.is_active}")
            print(f"  Organization: {user.organization.name}")
            print(f"  Role: {user.role}")
    else:
        print("\n⚠️  No users found in database!")

    print("\n" + "=" * 60)

    # Ask if user wants to create test user
    response = input("\nWould you like to create a test user? (yes/no): ").lower()

    if response in ['yes', 'y']:
        email = input("Enter email (default: test@example.com): ").strip() or "test@example.com"
        password = input("Enter password (default: Test123!@#): ").strip() or "Test123!@#"
        first_name = input("Enter first name (default: Test): ").strip() or "Test"
        last_name = input("Enter last name (default: User): ").strip() or "User"
        org_name = input("Enter organization name (default: Test Company): ").strip() or "Test Company"

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            print(f"\n❌ User with email {email} already exists!")
            existing_user = User.objects.get(email=email)

            # Ask if they want to reset password
            reset = input(f"\nWould you like to reset password for {email}? (yes/no): ").lower()
            if reset in ['yes', 'y']:
                existing_user.set_password(password)
                existing_user.save()
                print(f"✅ Password reset for {email}")
                print(f"\n🔑 Login Credentials:")
                print(f"   Email: {email}")
                print(f"   Password: {password}")
        else:
            # Create organization
            org, created = Organization.objects.get_or_create(
                name=org_name,
                defaults={'email': email}
            )

            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                organization=org,
                role='owner'
            )

            print(f"\n✅ User created successfully!")
            print(f"\n🔑 Login Credentials:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"   Organization: {org_name}")

            # Test authentication
            from django.contrib.auth import authenticate
            auth_user = authenticate(username=email, password=password)
            if auth_user:
                print(f"\n✅ Authentication test: SUCCESS")
            else:
                print(f"\n❌ Authentication test: FAILED")
                print("   Something is wrong with the authentication setup!")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
