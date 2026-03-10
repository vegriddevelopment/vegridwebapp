import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()
from vegrid_app.models import DeyeDevice
print(f"Total devices in DB: {DeyeDevice.objects.count()}")
for d in DeyeDevice.objects.all():
    print(f"- {d.name} (SN: {d.device_sn}) | Status: {d.status} | Rating: {d.rating}kVA | Gen: {d.generation}kW | Storage: {d.storage}kW | Load: {d.load}kW")
