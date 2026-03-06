from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

from .models import StatusUpdate


class StatusUpdateTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='socialuser', password='TestPass123!', role='STUDENT',
        )

    def test_post_status(self):
        self.client.login(username='socialuser', password='TestPass123!')
        response = self.client.post(
            '/social/post/',
            {'content': 'Hello StudySphere!'},
            HTTP_REFERER='/social/',
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            StatusUpdate.objects.filter(
                user=self.user, content='Hello StudySphere!',
            ).exists()
        )

    def test_status_feed(self):
        StatusUpdate.objects.create(user=self.user, content='Feed item')
        self.client.login(username='socialuser', password='TestPass123!')
        response = self.client.get('/social/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feed item')

    def test_status_model_str(self):
        update = StatusUpdate.objects.create(
            user=self.user, content='A quick status update for testing',
        )
        self.assertIn(self.user.username, str(update))
        self.assertIn('A quick status update for testing', str(update))


class StatusAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser', password='TestPass123!', role='STUDENT',
        )
        self.client = APIClient()

    def test_create_status_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/status/',
            {'content': 'API status post'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            StatusUpdate.objects.filter(content='API status post').exists()
        )

    def test_list_status_api(self):
        StatusUpdate.objects.create(user=self.user, content='Existing post')
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
