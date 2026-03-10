import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import DeyeDevice
DeyeDevice.objects.filter(device_sn='SN-PLACEHOLDER').delete()
print('Deleted SN-PLACEHOLDER')
