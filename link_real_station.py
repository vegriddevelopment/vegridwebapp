import os
import django
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer, DeyeDevice

def link_real_station():
    # Target station from our findings
    station_id = "61776373" # VOLEMI Hybrid Solar System
    username = 'deye_customer'
    
    try:
        user = User.objects.get(username=username)
        customer = user.customer
        
        # Create or update device with station ID as SN for now
        device, created = DeyeDevice.objects.update_or_create(
            device_sn=station_id,
            defaults={
                'customer': customer,
                'name': 'VOLEMI Hybrid Solar System',
                'county': 'Nairobi',
                'town': 'Kugeria',
                'area': 'Kugeria',
                'status': 'Online',
                'deye_username': os.getenv('DEYE_USERNAME'),
                'deye_password': os.getenv('DEYE_PASSWORD')
            }
        )
        
        # Remove the old SN-PLACEHOLDER or pollmuni88 if they exist for this customer
        DeyeDevice.objects.filter(customer=customer).exclude(device_sn=station_id).delete()
        
        if created:
            print(f"Linked real station {station_id} to {username}")
        else:
            print(f"Updated station {station_id} for {username}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    link_real_station()
