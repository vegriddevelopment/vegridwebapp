import sys
sys.path.append('.')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from django.contrib.auth.models import User
from vegrid_app.models import Customer

# Check if test user exists
if not User.objects.filter(username='testuser').exists():
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )
    user.first_name = 'Test'
    user.last_name = 'User'
    user.save()
    
    # Create customer profile
    customer = Customer.objects.create(
        user=user,
        phone_number='+254700000000',
        address='Test Address',
        county='Nairobi',
        area='Test Area',
        town='Nairobi'
    )
    print("Test user created successfully!")
else:
    print("Test user already exists")
