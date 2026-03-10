import os
import django
import logging

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService
from vegrid_app.models import DeyeDevice

def run_sync():
    service = DeyeService()
    service.sync_site_names()
    
    # Check results
    for device in DeyeDevice.objects.all():
        logger.info(f"Device {device.device_sn} current name: {device.name}")

if __name__ == "__main__":
    run_sync()
