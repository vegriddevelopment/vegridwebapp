import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer

def create_admin():
    username = 'adminuser'
    email = 'admin@vegrid.com'
    password = 'adminpassword123'
    
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        user.first_name = "Admin"
        user.last_name = "User"
        user.is_staff = True
        user.save()
        
        # Create corresponding customer profile
        Customer.objects.get_or_create(
            user=user,
            phone_number='0711223344',
            registration_type='individual',
            is_verified=True
        )
        
        print(f"Successfully created admin user:")
        print(f"Username: {username}")
        print(f"Password: {password}")
    else:
        print(f"User {username} already exists.")

if __name__ == "__main__":
    create_admin()
