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

def pull_latest_metrics():
    service = DeyeService()
    api = DeyeAPI()
    
    token = service.get_token()
    if not token:
        logger.error("Failed to obtain token")
        return

    # Targeting Five Star Meadows
    device_sn = "2510171733"
    
    logger.info(f"Pulling metrics for device: {device_sn}")
    
    # Request latest data
    response = api.get_device_latest(token, [device_sn])
    
    print("Full API Response:")
    print(json.dumps(response, indent=2))
    
    if response.get('code') not in [0, "0", "1000000"]:
        logger.error(f"API Error: {response.get('msg')}")
        return

    device_data_list = response.get('deviceDataList', [])
    if not device_data_list:
        logger.warning("No data returned from latest endpoint.")
        return

    # Extract all keys into a flat dictionary for easy mapping
    raw_data = {item['key']: item['value'] for item in device_data_list[0].get('dataList', [])}

    # Map the data points as requested
    # Note: Mapping raw API keys (DCPowerPV1, etc.) to your specified labels
    metrics = {
        "Solar Data": {
            "PV1 Power": raw_data.get("DCPowerPV1", "0"),
            "PV2 Power": raw_data.get("DCPowerPV2", "0"),
            "Total PV Power": raw_data.get("TotalDCInputPower", "0"),
            "Today's Yield": raw_data.get("DailyActiveProduction", "0")
        },
        "Utilization/Load": {
            "Load Power": raw_data.get("TotalConsumptionPower", "0"),
            "UPS Power": raw_data.get("UPSLoadPower", "0"),
            "Today's Load": raw_data.get("DailyConsumption", "0")
        },
        "Battery Data": {
            "State of Charge": raw_data.get("SOC", "0"),
            "Battery Power": raw_data.get("BatteryPower", "0")
        }
    }

    print("\n" + "="*50)
    print(f"LATEST METRICS: FIVE STAR MEADOWS")
    print("="*50)
    print(json.dumps(metrics, indent=2))
    print("="*50 + "\n")

if __name__ == "__main__":
    pull_latest_metrics()
