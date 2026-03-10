
import os
import django
import logging
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.models import DeyeDevice

def check_station_detail():
    logger.info("Checking Deye API station detail...")
    
    devices = DeyeDevice.objects.all()
    if not devices.exists():
        logger.error("No Deye devices found")
        return
    
    device = devices.first()
    logger.info(f"Testing device: {device.name} (SN: {device.device_sn})")
    
    service = DeyeService()
    
    try:
        token = service.get_token()
        logger.info(f"Token obtained: {token[:10]}...")
        
        base_url = service.base_url
        app_id = service.app_id
        
        # Try station detail endpoint
        url = f"{base_url}/v1.0/station/detail"
        params = {"appId": app_id, "id": device.device_sn}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Requesting station detail from: {url}")
        logger.info(f"Params: {params}")
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        # Try to get more detailed realtime data via station
        realtime_url = f"{base_url}/v1.0/station/realtime"
        realtime_params = {"appId": app_id, "id": device.device_sn}
        
        logger.info(f"\nRequesting station realtime data from: {realtime_url}")
        logger.info(f"Params: {realtime_params}")
        
        realtime_response = requests.get(realtime_url, params=realtime_params, headers=headers, timeout=10)
        
        logger.info(f"Response status code: {realtime_response.status_code}")
        logger.info(f"Response content: {realtime_response.text}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_station_detail()
