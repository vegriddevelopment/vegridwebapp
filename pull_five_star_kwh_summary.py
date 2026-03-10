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

def pull_kwh_summary():
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

    # Extract raw keys
    raw_data = {item['key']: item['value'] for item in device_list[0].get('dataList', [])}
    
    # Arrange metrics in the requested order with labels
    summary = [
        ("total consumption", raw_data.get("DailyConsumption", "0.00")),
        ("solar production", raw_data.get("DailyActiveProduction", "0.00")),
        ("battery discharge", raw_data.get("DailyDischargingEnergy", "0.00")),
        ("grid import", raw_data.get("DailyEnergyPurchased", "0.00"))
    ]

    print("\n" + "="*45)
    print(f"KWH SUMMARY: FIVE STAR MEADOWS")
    print("-" * 45)
    for label, val in summary:
        print(f"{label:<25}: {float(val):>10.2f} kWh")
    print("="*45 + "\n")

if __name__ == "__main__":
    pull_kwh_summary()
