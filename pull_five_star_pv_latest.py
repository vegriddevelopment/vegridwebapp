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

def pull_pv_data_mapped():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    # Five Star Meadows Details
    device_sn = "2510171733"
    
    # Fetch from /v1.0/device/latest
    response = api.get_device_latest(token, [device_sn])
    
    if response.get('code') not in [0, "0", "1000000"]:
        logger.error(f"API Error: {response.get('msg')}")
        return

    # Navigate the specific deviceDataList -> dataList structure identified in RAW test
    device_list = response.get('deviceDataList', [])
    if not device_list:
        logger.warning("No device data found in response.")
        return

    # Map the raw keys to your desired labels
    raw_data = {item['key']: item['value'] for item in device_list[0].get('dataList', [])}
    
    # Dashboard Mapping Logic
    pv_dashboard_data = {
        "Device": device_sn,
        "Station": "Five Star Meadows",
        "Real-Time Power (Watts)": {
            "pv1Power": raw_data.get("DCPowerPV1", "0"),
            "pv2Power": raw_data.get("DCPowerPV2", "0"),
            "pv3Power": raw_data.get("DCPowerPV3", "0"),
            "totalPvPower": raw_data.get("TotalDCInputPower", "0")
        },
        "Electrical Details (V/A)": {
            "pv1Volt": raw_data.get("DCVoltagePV1", "0"),
            "pv1Current": raw_data.get("DCCurrentPV1", "0"),
            "pv2Volt": raw_data.get("DCVoltagePV2", "0"),
            "pv2Current": raw_data.get("DCCurrentPV2", "0")
        },
        "Energy Production (kWh)": {
            "todayPv": raw_data.get("DailyActiveProduction", "0"),
            "totalPv": raw_data.get("TotalActiveProduction", "0")
        }
    }

    print("\n" + "="*50)
    print("MAPPED PV DASHBOARD DATA")
    print("="*50)
    print(json.dumps(pv_dashboard_data, indent=2))
    print("="*50 + "\n")

if __name__ == "__main__":
    pull_pv_data_mapped()
