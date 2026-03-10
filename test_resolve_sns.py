import os
import sys
import django
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_resolve_sns():
    service = DeyeService()
    station_id = "61776373"
    print(f"Resolving SNs for station {station_id}...")
    sns = service._get_device_sns_from_station_id(station_id)
    print(f"SNS: {sns}")

if __name__ == "__main__":
    test_resolve_sns()
