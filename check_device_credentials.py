import sys
sys.path.append('.')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from vegrid_app.models import DeyeDevice
device = DeyeDevice.objects.first()
print(f"Device SN: {device.device_sn}")
print(f"Name: {device.name}")
print(f"Deye Username: {device.deye_username}")
print(f"Deye Password: {device.deye_password}")
print(f"County: {device.county}")
print(f"Town: {device.town}")
print(f"Area: {device.area}")
print(f"Rating: {device.rating}")
print(f"Generation: {device.generation}")
print(f"Storage: {device.storage}")
print(f"Grid Imports: {device.grid_imports}")
print(f"Grid Export: {device.grid_export}")
print(f"Load: {device.load}")
print(f"Status: {device.status}")
