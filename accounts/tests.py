from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import User


class UserModelTest(TestCase):

    def test_create_student(self):
        user = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.assertTrue(user.is_student())
        self.assertFalse(user.is_teacher())

    def test_create_teacher(self):
        user = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.assertTrue(user.is_teacher())
        self.assertFalse(user.is_student())

    def test_user_str(self):
        user = User.objects.create_user(
            username='testuser', password='TestPass123!', role='STUDENT',
        )
        self.assertEqual(str(user), 'testuser (Student)')


class UserRegistrationTest(TestCase):

    def test_register_page_loads(self):
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)

    def test_register_student(self):
        data = {
            'username': 'newstudent',
            'email': 'student@example.com',
            'first_name': 'New',
            'last_name': 'Student',
            'role': 'STUDENT',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        }
        response = self.client.post('/accounts/register/', data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newstudent').exists())
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.role, 'STUDENT')

    def test_register_teacher(self):
        data = {
            'username': 'newteacher',
            'email': 'teacher@example.com',
            'first_name': 'New',
            'last_name': 'Teacher',
            'role': 'TEACHER',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        }
        response = self.client.post('/accounts/register/', data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newteacher')
        self.assertEqual(user.role, 'TEACHER')

    def test_register_password_mismatch(self):
        data = {
            'username': 'baduser',
            'email': 'bad@example.com',
            'first_name': 'Bad',
            'last_name': 'User',
            'role': 'STUDENT',
            'password1': 'SecurePass99!',
            'password2': 'DifferentPass99!',
        }
        response = self.client.post('/accounts/register/', data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())


class UserAuthTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='authuser', password='TestPass123!', role='STUDENT',
        )

    def test_login_valid(self):
        response = self.client.post('/accounts/login/', {
            'username': 'authuser',
            'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid(self):
        response = self.client.post('/accounts/login/', {
            'username': 'authuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_logout(self):
        self.client.login(username='authuser', password='TestPass123!')
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')


class UserProfileTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser', password='TestPass123!', role='STUDENT',
        )

    def test_profile_page_loads(self):
        response = self.client.get(f'/accounts/profile/{self.user.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)

    def test_edit_profile(self):
        self.client.login(username='profileuser', password='TestPass123!')
        response = self.client.post('/accounts/edit-profile/', {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'presence': User.AVAILABLE,
            'status_text': 'A brand new bio',
            'bio': 'A brand new bio',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'A brand new bio')


class UserSearchTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='searchuser', password='TestPass123!', role='STUDENT',
        )
        User.objects.create_user(
            username='testmatch', password='TestPass123!', role='TEACHER',
        )

    def test_search_users(self):
        self.client.login(username='searchuser', password='TestPass123!')
        response = self.client.get('/accounts/search/?q=testmatch')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testmatch')

    def test_search_no_results(self):
        self.client.login(username='searchuser', password='TestPass123!')
        response = self.client.get('/accounts/search/?q=nonexistentuser')
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['user_results'], [])


class UserAPITest(APITestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username='apistudent', password='TestPass123!', role='STUDENT',
        )
        self.teacher = User.objects.create_user(
            username='apiteacher', password='TestPass123!', role='TEACHER',
        )
        self.client = APIClient()

    def test_user_list_authenticated(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_user_list_unauthenticated(self):
        response = self.client.get('/api/users/')
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_api_register(self):
        data = {
            'username': 'apireguser',
            'email': 'apireguser@example.com',
            'password': 'V3ryS3cure!Pass',
            'first_name': 'Api',
            'last_name': 'User',
            'role': 'STUDENT',
        }
        response = self.client.post('/api/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='apireguser').exists())

    def test_user_search(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/users/?search=apiteacher')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        usernames = [u['username'] for u in results]
        self.assertIn('apiteacher', usernames)
