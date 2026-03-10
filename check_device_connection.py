import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_device_connection():
    service = DeyeService()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    logger.info("Fetching station and device list...")
    stations_resp = service.get_station_list_with_device()
    
    if stations_resp.get('code') not in [0, "0", "1000000"]:
        logger.error(f"Failed to get station list: {stations_resp.get('msg')}")
        return

    station_list = stations_resp.get('stationList', [])
    if not station_list:
        logger.warning("No stations found.")
        return

    print("\n" + "="*60)
    print(f"{'STATION NAME':<25} | {'DEVICE SN':<15} | {'STATUS':<10}")
    print("-" * 60)

    for station in station_list:
        station_name = station.get('name', 'Unknown')
        device_list = station.get('deviceListItems', [])
        
        if not device_list:
            print(f"{station_name[:25]:<25} | {'No Devices':<15} | {'N/A':<10}")
            continue

        for device in device_list:
            sn = device.get('deviceSn', 'Unknown')
            # connectStatus: 1 usually means online, 0 offline
            status_code = device.get('connectStatus')
            status = "Online" if status_code == 1 else "Offline"
            print(f"{station_name[:25]:<25} | {sn:<15} | {status:<10}")

    print("="*60 + "\n")

if __name__ == "__main__":
    check_device_connection()
