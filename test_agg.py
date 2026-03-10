import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

def test_aggregation():
    service = DeyeService()
    station_id = "61776373"
    
    print(f"Testing aggregation for station {station_id}...")
    agg = service._aggregate_device_latest_for_station(station_id)
    print(json.dumps(agg, indent=2))

if __name__ == "__main__":
    test_aggregation()
