import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()
from django.contrib.auth.models import User
from vegrid_app.models import Customer
print("All Customers/Users:")
for c in Customer.objects.all():
    print(f" - ID: {c.id}, Username: {c.user.username}, Phone: {c.phone_number}")
