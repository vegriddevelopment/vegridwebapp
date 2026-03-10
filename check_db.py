import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()
from vegrid_app.models import DeyeDevice
print("All devices in DB:")
for d in DeyeDevice.objects.all():
    print(f" - {d.name} (SN: {d.device_sn}) -> Customer: {d.customer.user.username}")
