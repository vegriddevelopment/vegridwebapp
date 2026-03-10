import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer, DeyeDevice

print("=== Checking Users ===")
users = User.objects.all()
print(f"Total users: {users.count()}")
for user in users:
    print(f"  - Username: {user.username}")
    print(f"    Email: {user.email}")
    
    # Check customer profile
    try:
        customer = Customer.objects.get(user=user)
        print(f"    Customer: exists")
        
        # Check devices
        devices = DeyeDevice.objects.filter(customer=customer)
        print(f"    Devices: {devices.count()}")
        for device in devices:
            print(f"      - {device.name} ({device.device_sn})")
            
    except Customer.DoesNotExist:
        print(f"    Customer: NOT FOUND")
        
    print()

print("\n=== Checking Deye Devices ===")
devices = DeyeDevice.objects.all()
print(f"Total devices: {devices.count()}")
for device in devices:
    print(f"  - SN: {device.device_sn}")
    print(f"    Name: {device.name}")
    print(f"    Customer: {device.customer.user.username if device.customer else 'None'}")
    print()
