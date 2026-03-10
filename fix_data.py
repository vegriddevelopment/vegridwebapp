import os
import django

def fix_customer_ids(Customer, models):
    print("Fixing Customer IDs...")
    customers_without_id = Customer.objects.filter(models.Q(customer_id__isnull=True) | models.Q(customer_id=''))
    print(f"Found {customers_without_id.count()} customers without ID.")
    for customer in customers_without_id:
        # Triggering the save() method to generate customer_id
        customer.save()
        print(f"Generated ID {customer.customer_id} for {customer.user.email or customer.user.username}")

def fix_deye_device_locations(DeyeDevice):
    print("\nFixing DeyeDevice locations from Customer data...")
    devices = DeyeDevice.objects.all()
    updated_count = 0
    for device in devices:
        customer = device.customer
        changed = False
        if customer:
            if not device.county or device.county == "Nairobi":
                if customer.county:
                    device.county = customer.county
                    changed = True
            if not device.town or device.town == "Nairobi":
                if customer.town:
                    device.town = customer.town
                    changed = True
            if not device.area or device.area == "Runda":
                if customer.area:
                    device.area = customer.area
                    changed = True
            if not device.country or device.country == "Kenya":
                if customer.country:
                    device.country = customer.country
                    changed = True
            
            if changed:
                device.save()
                updated_count += 1
                print(f"Updated location for device {device.name} (SN: {device.device_sn}) from customer {customer.user.email or customer.user.username}")
    print(f"Updated {updated_count} devices.")

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
    django.setup()
    
    from vegrid_app.models import Customer, DeyeDevice
    from django.db import models
    
    fix_customer_ids(Customer, models)
    fix_deye_device_locations(DeyeDevice)
    print("\nData fix complete.")
