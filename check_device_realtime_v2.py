
import os
import django
import logging
import json
import requests

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService

def check_device_realtime():
    service = DeyeService()
    try:
        token = service.get_token()
        from vegrid_app.models import DeyeDevice
        device = DeyeDevice.objects.first()
        if device:
            logger.info(f"Checking realtime for device {device.device_sn}")
            
            url = f"{service.base_url}/v1.0/device/realtime"
            params = {"appId": service.app_id}
            payload = {"deviceSn": device.device_sn}
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.post(url, params=params, json=payload, headers=headers)
            result = response.json()
            logger.info(f"Device Realtime Response: {json.dumps(result, indent=2)}")
        else:
            logger.error("No devices found")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    check_device_realtime()
