#!/usr/bin/env python
"""Script to create a test user with OTP for login functionality testing."""

import os
import django
from django.contrib.auth.models import User
from vegrid_app.models import Customer, OTP
from django.utils import timezone
from datetime import timedelta
import random
import string


# Configure Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()


def generate_otp(length=4):
    """Generate a numeric OTP of specified length."""
    return ''.join(random.choices(string.digits, k=length))


def create_test_user():
    """Create a test user and associated customer profile with OTP."""
    
    # Create test user
    test_user, created = User.objects.get_or_create(
        username='testuser@example.com',
        defaults={
            'email': 'testuser@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': User.objects.make_random_password()
        }
    )
    
    if created:
        print(f"Created test user: {test_user.email}")
    else:
        print(f"Test user already exists: {test_user.email}")
    
    # Create customer profile
    test_customer, customer_created = Customer.objects.get_or_create(
        user=test_user,
        defaults={
            'phone_number': '+254700000000',
            'registration_type': 'individual',
            'is_verified': True
        }
    )
    
    if customer_created:
        print(f"Created customer profile: {test_customer.phone_number}")
    else:
        print(f"Customer profile already exists: {test_customer.phone_number}")
    
    # Generate test OTP
    otp_code = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    OTP.objects.create(
        user=test_user,
        otp_code=otp_code,
        expires_at=expires_at,
        otp_type='phone'
    )
    
    print(f"Generated test OTP: {otp_code} (expires at {expires_at})")
    
    return test_user, test_customer, otp_code


if __name__ == '__main__':
    try:
        test_user, test_customer, otp_code = create_test_user()
        print("\nTest data created successfully!")
        print(f"\nUser login details:")
        print(f"Email: {test_user.email}")
        print(f"Phone Number: {test_customer.phone_number}")
        print(f"OTP: {otp_code}")
        print(f"OTP Expiration: {test_customer.user.otp_set.latest('created_at').expires_at}")
    except Exception as e:
        print(f"Error creating test user: {e}")
        import traceback
        traceback.print_exc()
