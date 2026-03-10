import os
import django
import logging
import sys

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.services.deye_service import DeyeService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Deye TotalDCInputPower check...")
    
    try:
        # Initialize DeyeService
        deye_service = DeyeService()
        
        logger.info("Checking device measure points...")
        
        # Get devices
        devices = deye_service.get_station_list_with_device()
        if not devices:
            logger.error("No devices found")
            return
        
        # Find the target device
        target_device_sn = None
        for station in devices.get('stationList', []):
            if station.get('name') == "VOLEMI Hybrid Solar System":
                logger.info(f"Found target station: {station.get('name')}")
                for device in station.get('deviceListItems', []):
                    target_device_sn = device.get('deviceSn')
                    logger.info(f"Target device SN: {target_device_sn}")
        
        if not target_device_sn:
            logger.error("Target device not found")
            return
        
        logger.info("Requesting history for TotalDCInputPower...")
        
        # Use a modified version of get_latest_generation_power to check TotalDCInputPower
        token = deye_service.get_token()
        base_url = deye_service.base_url
        app_id = deye_service.app_id
        
        import requests
        from datetime import datetime, timedelta
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        history_url = f"{base_url}/v1.0/device/history"
        history_params = {"appId": app_id}
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)
        
        history_payload = {
            "deviceSn": target_device_sn,
            "measurePoints": ["TotalDCInputPower"],
            "startAt": start_time.strftime("%Y-%m-%d"),
            "endAt": end_time.strftime("%Y-%m-%d"),
            "granularity": 1
        }
        
        history_response = requests.post(
            history_url,
            params=history_params,
            json=history_payload,
            headers=headers,
            timeout=20
        )
        
        if history_response.status_code == 200:
            history_result = history_response.json()
            logger.info(f"History response code: {history_result.get('code')}")
            
            if history_result.get('code') in [0, "0", "1000000"]:
                data_list = history_result.get('dataList', [])
                if data_list:
                    logger.info(f"Data list count: {len(data_list)}")
                    latest_data = sorted(data_list, key=lambda x: int(x['time']))[-1]
                    item_list = latest_data.get('itemList', [])
                    for item in item_list:
                        if item.get('key') == 'TotalDCInputPower':
                            total_dc_power = float(item.get('value')) / 1000  # Convert to kW
                            logger.info(f"Latest TotalDCInputPower: {total_dc_power:.2f} kW")
                else:
                    logger.warning("No data points in device history")
            else:
                logger.error(f"History API error: {history_result.get('msg')}")
        else:
            logger.error(f"History API request failed: {history_response.status_code} - {history_response.text}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    return True

if __name__ == "__main__":
    main()