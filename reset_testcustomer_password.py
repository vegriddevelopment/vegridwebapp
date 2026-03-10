import sys
sys.path.append('.')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
import django
django.setup()

from django.contrib.auth.models import User

try:
    user = User.objects.get(username='testcustomer')
    user.set_password('testpassword123')
    user.save()
    print("Password reset successful for testcustomer")
    print("Username: testcustomer")
    print("Password: testpassword123")
except User.DoesNotExist:
    print("User testcustomer not found")
