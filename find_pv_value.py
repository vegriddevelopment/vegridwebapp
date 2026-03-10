import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.deye_api import DeyeAPI
from vegrid_app.services.deye_service import DeyeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_value():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    device_sn = "2510171733"
    station_id = "61776373"

    print(f"\nSearching for a value near 2.89 (kW) for station {station_id}...")

    # 1. Check station/listWithDevice
    print("\n--- Checking station/listWithDevice ---")
    resp = service.get_station_list_with_device()
    for station in resp.get('stationList', []):
        if str(station.get('id')) == station_id:
            # Check common power fields
            power_fields = ['totalPower', 'generationPower', 'dayPower', 'installedCapacity']
            for f in power_fields:
                val = station.get(f)
                print(f"Station Field '{f}': {val}")

    # 2. Check device/latest
    print("\n--- Checking device/latest ---")
    resp = api.get_device_latest(token, [device_sn])
    device_data = resp.get('deviceDataList', [{}])[0].get('dataList', [])
    for item in device_data:
        key = item.get('key')
        val = item.get('value')
        # Check if value is close to 2.89 (allowing for kW/W conversion)
        try:
            num_val = float(val)
            if 2.0 <= num_val <= 4.0 or 2000 <= num_val <= 4000:
                 print(f"Device Field '{key}': {val} {item.get('unit')}")
        except:
            pass

    # 3. Check station/latest
    print("\n--- Checking station/latest ---")
    resp = api.get_station_latest(token, station_id)
    st_data = resp.get('data', {})
    for k, v in st_data.items():
        print(f"Station Latest '{k}': {v}")

if __name__ == "__main__":
    find_value()
