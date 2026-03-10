import os
import django
from datetime import datetime

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import Customer

def generate_customer_ids():
    """Generate customer IDs for existing customers without one."""
    customers = Customer.objects.filter(customer_id__isnull=True)
    
    print(f"Found {customers.count()} customers without customer IDs")
    
    for customer in customers:
        try:
            # Get country prefix (default to 'KE' if not provided)
            country_prefix = customer.country[:2].upper() if customer.country else 'KE'
            
            # Use the customer's creation date if available, otherwise current date
            if hasattr(customer, 'created_at') and customer.created_at:
                now = customer.created_at
            else:
                now = datetime.now()
                
            day = str(now.day).zfill(2)
            month = str(now.month).zfill(2)
            year = str(now.year)[2:]  # 2-digit year (e.g., 2026 becomes 26)
            
            # Get next sequence number (prefix+day+month+year)
            last_customer = Customer.objects.filter(
                customer_id__startswith=f"{country_prefix}{day}{month}{year}"
            ).order_by('-customer_id').first()
            
            if last_customer:
                # Extract sequence number from last customer ID (last 4 digits)
                last_seq = int(last_customer.customer_id[-4:])
                next_seq = last_seq + 1
            else:
                next_seq = 1
                
            # Format sequence with 4 digits
            seq_number = str(next_seq).zfill(4)
            
            # Combine all parts (prefix, day, month, year, sequence)
            customer.customer_id = f"{country_prefix}{day}{month}{year}{seq_number}"
            customer.save()
            
            print(f"Generated customer ID: {customer.customer_id} for {customer.user}")
            
        except Exception as e:
            print(f"Error generating customer ID for {customer.user}: {e}")

if __name__ == "__main__":
    generate_customer_ids()
    print("Customer ID generation complete")
