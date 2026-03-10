
from django.contrib.auth.models import User
from vegrid_app.models import Customer, OTP
from django.utils import timezone
from datetime import timedelta
import random
import string

def generate_otp(length=4):
    return ''.join(random.choices(string.digits, k=length))

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

test_customer, customer_created = Customer.objects.get_or_create(
    user=test_user,
    defaults={
        'phone_number': '+254700000000',
        'registration_type': 'individual',
        'is_verified': True
    }
)

otp_code = generate_otp()
expires_at = timezone.now() + timedelta(minutes=5)
OTP.objects.create(
    user=test_user,
    otp_code=otp_code,
    expires_at=expires_at,
    otp_type='phone'
)

print(f"Test user created: {test_user.email}")
print(f"Customer created: {test_customer.phone_number}")
print(f"Test OTP: {otp_code} (expires at {expires_at})")
