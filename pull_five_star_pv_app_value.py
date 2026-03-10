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

def pull_pv_app_value():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    device_sn = "2510171733"
    
    # Request latest data from /v1.0/device/latest
    response = api.get_device_latest(token, [device_sn])
    
    if response.get('code') not in [0, "0", "1000000"]:
        logger.error(f"API Error: {response.get('msg')}")
        return

    device_list = response.get('deviceDataList', [])
    if not device_list:
        logger.warning("No device data found in response.")
        return

    # Extract real-time power fields
    raw_data = {item['key']: item['value'] for item in device_list[0].get('dataList', [])}
    
    pv1 = float(raw_data.get("DCPowerPV1", 0))
    pv2 = float(raw_data.get("DCPowerPV2", 0))
    pv3 = float(raw_data.get("DCPowerPV3", 0))
    pv4 = float(raw_data.get("DCPowerPV4", 0))
    total_pv = float(raw_data.get("TotalDCInputPower", 0))

    print("\n" + "="*50)
    print(f"REAL-TIME POWER (DC INPUT): FIVE STAR MEADOWS")
    print("-" * 50)
    print(f"PV1 Power: {pv1:.2f} W")
    print(f"PV2 Power: {pv2:.2f} W")
    print(f"PV3 Power: {pv3:.2f} W")
    print(f"PV4 Power: {pv4:.2f} W")
    print(f"Total PV Power: {total_pv/1000:.2f} kW ({total_pv:.2f} W)")
    print("="*50 + "\n")

if __name__ == "__main__":
    pull_pv_app_value()
