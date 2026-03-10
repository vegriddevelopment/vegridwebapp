import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vegrid_project.settings')
django.setup()

from vegrid_app.models import Alert
a = Alert.objects.first()
if a:
    print(f"ID: {a.id}")
    print(f"Type: {a.alert_type}")
    print(f"Message: {a.message}")
else:
    print("No alerts found")
