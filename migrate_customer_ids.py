import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import Customer

def migrate_customer_ids():
    """Migrate existing customer IDs to the new format: prefix+day+month+year+seq"""
    customers = Customer.objects.exclude(customer_id__isnull=True).exclude(customer_id='')
    
    print(f"Found {customers.count()} customers with existing IDs")
    
    count = 0
    for customer in customers:
        old_id = customer.customer_id
        # Expected old format: KE YY MM DD SEQ (14 chars)
        # prefix(2), year(2), month(2), day(2), seq(4)
        if len(old_id) == 12: # Actually KE 26 03 05 0001 is 12 chars
            prefix = old_id[:2]
            year = old_id[2:4]
            month = old_id[4:6]
            day = old_id[6:8]
            seq = old_id[8:]
            
            new_id = f"{prefix}{day}{month}{year}{seq}"
            if old_id != new_id:
                customer.customer_id = new_id
                customer.save()
                print(f"Migrated ID: {old_id} -> {new_id} for {customer.user}")
                count += 1
        else:
            print(f"Skipping ID {old_id} - doesn't match expected length of 12")

    print(f"Successfully migrated {count} customer IDs")

if __name__ == "__main__":
    migrate_customer_ids()
