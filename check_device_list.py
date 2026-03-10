import os
import django
import logging
import json

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService

def check_device_list():
    """Check if Deye API returns device list with real data"""
    logger.info("Checking Deye device list API...")
    
    # Initialize DeyeService
    service = DeyeService()
    
    try:
        # Get device list
        device_list = service.get_device_list()
        logger.info(f"Device list response: {json.dumps(device_list, indent=2)}")
        
        if device_list.get('code') in [0, "0", "1000000"]:
            logger.info(f"Successfully retrieved device list with {device_list.get('total', 0)} devices")
            
            # Check if device list has any data
            if 'list' in device_list:
                devices = device_list['list']
                for device in devices:
                    logger.info(f"\nDevice: {device.get('deviceName', 'Unknown')} (SN: {device.get('deviceSn')})")
                    logger.info(f"Data: {json.dumps(device, indent=4)}")
            elif 'deviceList' in device_list:
                devices = device_list['deviceList']
                for device in devices:
                    logger.info(f"\nDevice: {device.get('deviceName', 'Unknown')} (SN: {device.get('deviceSn')})")
                    logger.info(f"Data: {json.dumps(device, indent=4)}")
            else:
                logger.warning("No device list data in response")
                
        else:
            logger.error(f"Failed to get device list: {device_list.get('msg', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error checking device list: {str(e)}")

if __name__ == "__main__":
    check_device_list()
