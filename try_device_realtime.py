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

from vegrid_app.models import DeyeDevice
from vegrid_app.deye_api import DeyeAPI

def try_device_realtime():
    """Try to get real-time data using device credentials"""
    logger.info("Trying to get real-time data using device credentials...")
    
    try:
        # Get the device
        device = DeyeDevice.objects.get(device_sn="61776373")
        logger.info(f"Device: {device.name} (SN: {device.device_sn})")
        logger.info(f"Credentials: {device.deye_username}:{device.deye_password}")
        
        # Initialize DeyeAPI
        api = DeyeAPI()
        
        # Get token
        logger.info("Getting token...")
        token_result = api.get_token(
            username=device.deye_username,
            password=device.deye_password,
            hash_type='sha256'
        )
        
        logger.info(f"Token result: {json.dumps(token_result, indent=2)}")
        
        if token_result.get('code') != 0:
            logger.warning("SHA256 hash failed, trying MD5...")
            token_result = api.get_token(
                username=device.deye_username,
                password=device.deye_password,
                hash_type='md5'
            )
            logger.info(f"MD5 token result: {json.dumps(token_result, indent=2)}")
        
        if token_result.get('code') == 0:
            token = token_result['data']['accessToken']
            logger.info(f"Token obtained: {token[:10]}...")
            
            # Get real-time data
            logger.info("Getting real-time data...")
            realtime_result = api.get_device_realtime(token, device.device_sn)
            logger.info(f"Real-time data result: {json.dumps(realtime_result, indent=2)}")
            
            if realtime_result.get('code') == 0:
                logger.info("Successfully retrieved real-time data")
                logger.info(f"Data: {json.dumps(realtime_result['data'], indent=4)}")
            else:
                logger.error(f"Failed to get real-time data: {realtime_result.get('msg', 'Unknown error')}")
        else:
            logger.error(f"Failed to get token: {token_result.get('msg', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    try_device_realtime()
