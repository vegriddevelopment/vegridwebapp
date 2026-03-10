import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer, OTP

print("=== Users ===")
for user in User.objects.all():
    print(f"ID: {user.id}")
    print(f"Name: {user.first_name} {user.last_name}")
    print(f"Email: {user.email}")
    print(f"Username: {user.username}")
    
    try:
        customer = Customer.objects.get(user=user)
        print(f"Phone: {customer.phone_number}")
        print(f"Verified: {customer.is_verified}")
    except Customer.DoesNotExist:
        print("Customer profile: Not found")
    
    # Get OTPs
    otps = OTP.objects.filter(user=user)
    if otps.exists():
        print(f"OTPs: {otps.count()}")
        for otp in otps:
            print(f"  - Type: {otp.otp_type}, Code: {otp.otp_code}, Expires: {otp.expires_at}, Used: {otp.is_used}")
    
    print()
