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
from vegrid_app.models import Alert

def run_bulk_fix():
    """Run a comprehensive alert fix: names, types, and raw info in messages"""
    print("="*60)
    print(" BULK FIXING ALERTS (TYPES, NAMES, MESSAGES) ")
    print("="*60)
    
    from vegrid_app.models import Alert, DeyeDevice
    
    # 1. First, add "Original Alert Type" to ALL alerts if not present
    print("\nAdding 'Original Alert Type' to all alerts...")
    all_alerts = Alert.objects.all()
    type_count = 0
    for alert in all_alerts:
        # If it's one of our simplified types, it should have the original name in message
        if alert.alert_type == "LOW VOLT":
            raw_info = "Original Alert Type: F56DC_VoltLow_Fault"
            if not alert.message:
                alert.message = raw_info
                alert.save()
                type_count += 1
            elif raw_info not in alert.message:
                alert.message = f"{raw_info}\n{alert.message}"
                alert.save()
                type_count += 1
        else:
            # For other types, we assume alert_type IS the raw type (unless it's LOW fault/Volt which we already fixed)
            raw_info = f"Original Alert Type: {alert.alert_type}"
            if not alert.message:
                alert.message = raw_info
                alert.save()
                type_count += 1
            elif "Original Alert Type:" not in alert.message:
                alert.message = f"{raw_info}\n{alert.message}"
                alert.save()
                type_count += 1
                
    print(f"Updated original type info for {type_count} alerts.")

    # 2. Add SN info to inverter alerts
    print("\nChecking for missing SN info in inverter alerts...")
    inverter_alerts = Alert.objects.filter(source="Inverter")
    sn_count = 0
    
    for alert in inverter_alerts:
        if "Device SN:" in (alert.message or ""):
            continue
            
        target_sn = None
        if alert.site and len(alert.site) > 5 and any(c.isdigit() for c in alert.site[:5]):
             # If site name looks like an SN
             target_sn = alert.site
             
        if not target_sn:
            device = DeyeDevice.objects.filter(customer=alert.customer).first()
            if device:
                target_sn = device.device_sn
        
        if target_sn:
            sn_info = f"Device SN: {target_sn}"
            if not alert.message:
                alert.message = sn_info
            else:
                alert.message = f"{sn_info}\n{alert.message}"
            alert.save()
            sn_count += 1
            
    print(f"Added SN info to {sn_count} inverter alerts.")
    
    # 3. Finally, run standard cleanup for site names
    print("\nRunning service-level cleanup for site names...")
    service = DeyeService()
    cleanup_count = service.cleanup_alert_names()
    print(f"Service cleanup updated {cleanup_count} alerts.")
    
    print("\n" + "="*60)
    print(" FINISHED ")
    print("="*60)

if __name__ == "__main__":
    run_bulk_fix()
