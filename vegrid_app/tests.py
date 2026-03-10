from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from vegrid_app.models import Customer, OTP
from vegrid_app.views import generate_otp, send_sms_otp, send_email_otp
from django.utils import timezone
from datetime import timedelta
import json


class PageViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_how_it_works_page(self):
        response = self.client.get(reverse('how-it-works'))
        self.assertEqual(response.status_code, 200)

    def test_solutions_page(self):
        response = self.client.get(reverse('solutions'))
        self.assertEqual(response.status_code, 200)

    def test_impact_page(self):
        response = self.client.get(reverse('impact'))
        self.assertEqual(response.status_code, 200)

    def test_team_page(self):
        response = self.client.get(reverse('team'))
        self.assertEqual(response.status_code, 200)

    def test_careers_page(self):
        response = self.client.get(reverse('careers'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

    def test_get_quote_page(self):
        response = self.client.get(reverse('get-quote'))
        self.assertEqual(response.status_code, 200)


class OTPTests(TestCase):
    """Tests for OTP functionality"""
    
    def test_otp_generation(self):
        """Test OTP generation function"""
        otp = generate_otp()
        self.assertEqual(len(otp), 4)
        self.assertTrue(otp.isdigit())

    def test_otp_model_creation(self):
        """Test OTP model creation and properties"""
        # Create test user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Create OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='phone'
        )
        
        # Verify OTP properties
        self.assertEqual(otp.user, user)
        self.assertEqual(otp.otp_code, otp_code)
        self.assertEqual(otp.otp_type, 'phone')
        self.assertFalse(otp.is_used)
        self.assertLess(timezone.now(), otp.expires_at)

    def test_otp_expiry(self):
        """Test OTP expiry functionality"""
        user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpassword"
        )
        
        otp_code = generate_otp()
        expires_at = timezone.now() - timedelta(minutes=1)  # Expired OTP
        
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='email'
        )
        
        # Verify OTP is expired
        self.assertGreater(timezone.now(), otp.expires_at)

    def test_mark_otp_as_used(self):
        """Test marking OTP as used"""
        user = User.objects.create_user(
            username="testuser3",
            email="test3@example.com",
            password="testpassword"
        )
        
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='phone'
        )
        
        # Mark as used
        otp.is_used = True
        otp.save()
        
        # Verify change was saved
        self.assertTrue(OTP.objects.get(id=otp.id).is_used)


class OTPAPITests(TestCase):
    """Tests for OTP API endpoints"""
    
    def setUp(self):
        self.client = Client()
        
    def test_send_phone_otp_api(self):
        """Test sending phone OTP API endpoint"""
        url = reverse('send-phone-otp')
        data = {
            "phone_number": "+254700000000",
            "country": "Kenya",
            "registration_type": "individual"
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['otp_length'], 4)
        self.assertEqual(response_data['expires_in'], 300)

    def test_verify_phone_otp_api(self):
        """Test verifying phone OTP API endpoint"""
        # Create test user and customer
        user = User.objects.create_user(
            username="+254700000001",
            email="+254700000001@temp.com",
            password="testpassword"
        )
        
        customer = Customer.objects.create(
            user=user,
            phone_number="+254700000001",
            registration_type="individual"
        )
        
        # Create valid OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='phone'
        )
        
        # Test verification
        url = reverse('verify-phone-otp')
        data = {
            "phone_number": "+254700000001",
            "otp_code": otp_code
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify customer is marked as verified
        customer.refresh_from_db()
        self.assertTrue(customer.is_verified)

    def test_send_login_otp_api(self):
        """Test sending login OTP API endpoint"""
        # Create test user and customer
        user = User.objects.create_user(
            username="+254700000002",
            email="+254700000002@temp.com",
            password="testpassword"
        )
        
        Customer.objects.create(
            user=user,
            phone_number="+254700000002",
            registration_type="individual"
        )
        
        url = reverse('send-login-otp')
        data = {
            "phone_number": "+254700000002"
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

    def test_verify_email_otp_api(self):
        """Test verifying email OTP API endpoint"""
        # Create test user
        user = User.objects.create_user(
            username="testemailuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Create valid email OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at,
            otp_type='email'
        )
        
        # Test verification
        url = reverse('verify-email-otp')
        data = {
            "email": "test@example.com",
            "otp_code": otp_code
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

