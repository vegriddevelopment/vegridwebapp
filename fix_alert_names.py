import os
import django
import logging

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from vegrid_app.services.deye_service import DeyeService

def run_cleanup():
    """Run the alert name cleanup"""
    print("="*60)
    print(" BULK FIXING ALERT SITE NAMES ")
    print("="*60)
    
    service = DeyeService()
    count = service.cleanup_alert_names()
    
    print("\n" + "="*60)
    print(f" SUCCESS: Fixed {count} alerts in the database.")
    print("="*60)

if __name__ == "__main__":
    run_cleanup()
