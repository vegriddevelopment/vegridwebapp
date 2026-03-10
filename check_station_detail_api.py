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

def check_station_detail_api():
    """Check Deye station detail API"""
    logger.info("Checking Deye station detail API...")
    
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
        
        base_url = service.base_url
        app_id = service.app_id
        
        # Try to get station detail
        station_url = f"{base_url}/v1.0/station/detail"
        station_params = {"appId": app_id, "id": device.device_sn}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Requesting station detail from: {station_url}")
        logger.info(f"Params: {station_params}")
        logger.info(f"Headers: {headers}")
        
        response = requests.get(station_url, params=station_params, headers=headers, timeout=10)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_station_detail_api()
