import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer, DeyeDevice, Wallet

# Credentials from .env
deye_username = os.getenv('DEYE_USERNAME', 'Info@hpower.co.ke')
deye_password = os.getenv('DEYE_PASSWORD', 'mR.deNiS!2026solAR')

u, _ = User.objects.get_or_create(username='deye_customer', defaults={'email':'deye@vegrid.co.ke', 'first_name': 'Deye', 'last_name': 'Customer'})
u.set_password('password123')
u.save()

c, _ = Customer.objects.get_or_create(user=u, defaults={'phone_number':'+254123456789', 'is_verified':True})
Wallet.objects.get_or_create(customer=c, defaults={'current_balance':1000, 'available_balance':1000})

# Link existing devices found in check_db.py for demo
DeyeDevice.objects.filter(device_sn='pollmuni88').update(
    customer=c,
    deye_username=deye_username,
    deye_password=deye_password
)
print(f"Device 'pollmuni88' updated with credentials and linked to {u.username}")

print(f"User 'deye_customer' created with password 'password123'")
print(f"Device 'Deye Site' linked to {deye_username}")
