import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import DeyeDevice
try:
    d = DeyeDevice.objects.get(device_sn='pollmuni88')
    print(f"SN: {d.device_sn}")
    print(f"User in DB: {d.deye_username}")
    print(f"Pass in DB: {d.deye_password}")
except DeyeDevice.DoesNotExist:
    print("pollmuni88 not found")
