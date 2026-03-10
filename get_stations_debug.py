import os
import django
import json
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

service = DeyeService()
stations = service.get_station_list_with_device()
print(json.dumps(stations, indent=2))
