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

def test_alerts():
    """Test the improved get_alerts method"""
    logger.info("Testing alerts sync...")
    
    service = DeyeService()
    
    # Test for specific device
    device_sn = "2510171733"
    alerts = service.get_alerts(device_sn, save_to_db=False)
    
    print(f"\nAlerts for {device_sn}:")
    print(json.dumps(alerts, indent=2))
    
    # Test for all devices
    all_alerts = service.get_alerts(save_to_db=False)
    print(f"\nAll Alerts for account:")
    print(json.dumps(all_alerts, indent=2))

if __name__ == "__main__":
    test_alerts()
