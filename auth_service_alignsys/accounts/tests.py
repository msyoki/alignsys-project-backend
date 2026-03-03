"""Tests for authentication views."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import Profile, Subscription, UserType, PlanName, SubscriptionStatus, BillingInterval

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """Test cases for authentication endpoints."""

    def setUp(self):
        self.client = APIClient()
        
        # Create a test profile and subscription
        self.profile = Profile.objects.create(
            name='Test User',
            type=UserType.INDIVIDUAL
        )
        
        self.subscription = Subscription.objects.create(
            profile=self.profile,
            plan_name=PlanName.FREE_ESIGN,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY
        )
        
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            profile=self.profile
        )

    def test_register_individual_user(self):
        """Test registering an individual user."""
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'secure123',
            'first_name': 'New',
            'last_name': 'User',
            'plan_name': 'FREE_ESIGN',
            'type': 'INDIVIDUAL'
        }
        response = self.client.post('/auth/register', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')

    def test_login_with_email(self):
        """Test login with email."""
        data = {
            'username': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post('/auth/login', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_username(self):
        """Test login with username."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post('/auth/login', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post('/auth/login', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """Test refreshing access token."""
        # First login
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        login_response = self.client.post('/auth/login', login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Refresh token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post('/auth/refresh', refresh_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
