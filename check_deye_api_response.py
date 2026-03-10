import os
import django
import logging
import requests

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.models import DeyeDevice

def check_deye_api_response():
    """Check Deye API response for device real-time data"""
    logger.info("Checking Deye API response for device real-time data...")
    
    # Get Deye devices from database
    devices = DeyeDevice.objects.all()
    
    if not devices.exists():
        logger.error("No Deye devices found in database")
        return
    
    device = devices.first()
    logger.info(f"Testing device: {device.name} (SN: {device.device_sn})")
    
    # Initialize DeyeService
    service = DeyeService()
    
    try:
        token = service.get_token()
        logger.info(f"Token obtained: {token[:10]}...")
        
        # Try to get real-time data directly
        base_url = service.base_url
        app_id = service.app_id
        
        url = f"{base_url}/v1.0/device/realtime"
        params = {"appId": app_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"deviceSn": device.device_sn}
        
        logger.info(f"Requesting real-time data from: {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        # Try to get station list
        logger.info("\n--- Getting station list ---")
        station_url = f"{base_url}/v1.0/station/list"
        station_params = {"appId": app_id, "page": 1, "size": 20}
        station_payload = {"page": 1, "size": 20}
        
        station_response = requests.post(station_url, params=station_params, json=station_payload, headers=headers, timeout=10)
        
        logger.info(f"Station list status code: {station_response.status_code}")
        logger.info(f"Station list content: {station_response.text}")
        
        # Parse station list
        station_data = station_response.json()
        if station_data.get('code') in [0, "0", "1000000"]:
            station_list = station_data.get('stationList', [])
            logger.info(f"Found {len(station_list)} stations")
            
            for station in station_list:
                logger.info(f"\nStation ID: {station.get('id')}")
                logger.info(f"Station Name: {station.get('name')}")
                logger.info(f"Generation Power: {station.get('generationPower')}")
                logger.info(f"Battery SOC: {station.get('batterySOC')}")
                logger.info(f"Device SN: {station.get('deviceSn')}")
                
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_deye_api_response()
