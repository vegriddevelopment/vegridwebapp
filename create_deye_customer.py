import os
import django
import json
from django.utils import timezone
from datetime import timedelta

from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
load_dotenv(override=True)
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer, DeyeDevice, Wallet
from vegrid_app.deye_api import DeyeAPI

def setup_deye_customer():
    # Credentials from environment
    deye_username = os.getenv('DEYE_USERNAME')
    deye_password = os.getenv('DEYE_PASSWORD')
    
    print(f"Using Deye credentials: {deye_username}")
    
    # Initialize API
    api = DeyeAPI()
    print(f"Base URL: {api.base_url}")
    print(f"App ID: {api.app_id}")
    
    # 1. Get Token
    print(f"Attempting to get token for {deye_username}...")
    token_result = api.get_token(username=deye_username, password=deye_password)
    print(f"Token Result: {json.dumps(token_result, indent=2)}")
    
    if token_result.get('code') != 0:
        # If it failed, try MD5
        print("SHA256 failed, attempting MD5...")
        token_result = api.get_token(username=deye_username, password=deye_password, hash_type='md5')
        print(f"MD5 Token Result: {json.dumps(token_result, indent=2)}")
        
        if token_result.get('code') != 0:
            print("Both SHA256 and MD5 failed. Please check credentials in .env")
            return
    
    # We have a token if we reached here
    if not token_result.get('data') or not token_result['data'].get('accessToken'):
        print("Token response missing accessToken")
        return

    token = token_result['data']['accessToken']
    print("Successfully obtained Deye token.")
    
    # 2. Get Device List
    device_list_result = api.get_device_list(token)
    if device_list_result.get('code') != 0:
        print(f"Failed to get device list: {device_list_result.get('msg')}")
        return
    
    devices = device_list_result.get('data', {}).get('list', [])
    if not devices:
        print("No devices found in this Deye account.")
        # We'll create a dummy one if no real one is found, but warn the user
        device_sn = "SN-REAL-PLACEHOLDER"
        print(f"Proceeding with placeholder SN: {device_sn}")
    else:
        device_sn = devices[0].get('deviceSn')
        print(f"Found device SN: {device_sn}")

    # 3. Create Web User
    username = 'deye_customer'
    password = 'password123'
    email = 'deye@vegrid.co.ke'
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': 'Deye',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password(password)
        user.save()
        print(f"Created web user: {username}")
    else:
        print(f"Web user {username} already exists")

    # 4. Create Customer Profile
    customer, created = Customer.objects.get_or_create(
        user=user,
        defaults={
            'phone_number': '+254123456789',
            'registration_type': 'commercial',
            'is_verified': True
        }
    )
    if created:
        print(f"Created customer profile for {username}")

    # 5. Create Wallet
    Wallet.objects.get_or_create(
        customer=customer,
        defaults={'current_balance': 1000.00, 'available_balance': 1000.00}
    )

    # 6. Link Deye Device
    device, created = DeyeDevice.objects.get_or_create(
        device_sn=device_sn,
        defaults={
            'customer': customer,
            'name': 'Deye Site',
            'deye_username': deye_username,
            'deye_password': deye_password,
            'status': 'Online'
        }
    )
    if not created:
        device.customer = customer
        device.deye_username = deye_username
        device.deye_password = deye_password
        device.save()
        print(f"Updated existing Deye device: {device_sn}")
    else:
        print(f"Linked Deye device: {device_sn}")

    print("\nSetup complete!")
    print(f"You can now log in at http://localhost:8000/ with:")
    print(f"Username: {username}")
    print(f"Password: {password}")

if __name__ == "__main__":
    setup_deye_customer()
