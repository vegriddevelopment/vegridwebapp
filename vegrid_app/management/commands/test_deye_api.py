from django.core.management.base import BaseCommand
from vegrid_app.deye_api import DeyeAPI
import json

class Command(BaseCommand):
    help = 'Tests DeyeCloud API connectivity'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='DeyeCloud Username')
        parser.add_argument('password', type=str, help='DeyeCloud Password')
        parser.add_argument('--sn', type=str, help='Device Serial Number to fetch data for')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        sn = options.get('sn')

        api = DeyeAPI()
        self.stdout.write(self.style.NOTICE(f'Authenticating {username}...'))
        
        token_res = api.get_token(username=username, password=password)
        if token_res.get('code') != 0:
            self.stdout.write(self.style.ERROR(f"Auth Failed: {token_res.get('msg', 'Unknown Error')}"))
            return

        token = token_res['data']['accessToken']
        self.stdout.write(self.style.SUCCESS(f"Successfully authenticated. Token: {token[:10]}..."))

        if sn:
            self.stdout.write(self.style.NOTICE(f'Fetching data for {sn}...'))
            data_res = api.get_device_realtime(token, sn)
            if data_res.get('code') == 0:
                self.stdout.write(self.style.SUCCESS('Data fetched successfully:'))
                self.stdout.write(json.dumps(data_res['data'], indent=4))
            else:
                self.stdout.write(self.style.ERROR(f"Fetch Failed: {data_res.get('msg', 'Unknown Error')}"))
        else:
            self.stdout.write(self.style.NOTICE('Fetching device list...'))
            list_res = api.get_device_list(token)
            if list_res.get('code') == 0:
                self.stdout.write(self.style.SUCCESS('Devices found:'))
                self.stdout.write(json.dumps(list_res['data'], indent=4))
            else:
                self.stdout.write(self.style.ERROR(f"List Failed: {list_res.get('msg', 'Unknown Error')}"))
