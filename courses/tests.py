from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

from .models import Course, CourseMaterial, Enrolment, Feedback


class CourseModelTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )

    def test_course_creation(self):
        course = Course.objects.create(
            title='Django 101', description='Learn Django', teacher=self.teacher,
        )
        self.assertEqual(course.title, 'Django 101')
        self.assertEqual(course.teacher, self.teacher)

    def test_course_str(self):
        course = Course.objects.create(
            title='Flask Basics', description='Intro to Flask', teacher=self.teacher,
        )
        self.assertEqual(str(course), 'Flask Basics')


class EnrolmentModelTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='Test Course', description='Desc', teacher=self.teacher,
        )

    def test_enrolment(self):
        enrolment = Enrolment.objects.create(
            student=self.student, course=self.course,
        )
        self.assertEqual(enrolment.student, self.student)
        self.assertEqual(enrolment.course, self.course)
        self.assertFalse(enrolment.blocked)

    def test_unique_enrolment(self):
        Enrolment.objects.create(student=self.student, course=self.course)
        with self.assertRaises(IntegrityError):
            Enrolment.objects.create(student=self.student, course=self.course)


class CourseViewTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='View Test Course',
            description='A course for testing views',
            teacher=self.teacher,
        )

    def test_course_list(self):
        response = self.client.get('/courses/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Test Course')

    def test_course_detail(self):
        response = self.client.get(f'/courses/{self.course.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)

    def test_course_create_teacher(self):
        self.client.login(username='teacher1', password='TestPass123!')
        response = self.client.post('/courses/create/', {
            'title': 'New Course',
            'description': 'Brand new course',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(title='New Course').exists())

    def test_course_create_student_forbidden(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.post('/courses/create/', {
            'title': 'Should Fail',
            'description': 'Not allowed',
        })
        self.assertEqual(response.status_code, 403)

    def test_enrol_student(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.post(f'/courses/{self.course.pk}/enrol/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrolment.objects.filter(
                student=self.student, course=self.course,
            ).exists()
        )

    def test_block_student(self):
        Enrolment.objects.create(
            student=self.student, course=self.course,
            status=Enrolment.APPROVED,
        )
        self.client.login(username='teacher1', password='TestPass123!')
        response = self.client.post(
            f'/courses/{self.course.pk}/block/{self.student.pk}/'
        )
        self.assertEqual(response.status_code, 302)
        enrolment = Enrolment.objects.get(
            student=self.student, course=self.course,
        )
        self.assertTrue(enrolment.blocked)

    def test_upload_material(self):
        self.client.login(username='teacher1', password='TestPass123!')
        test_file = SimpleUploadedFile(
            'notes.pdf', b'file_content', content_type='application/pdf',
        )
        response = self.client.post(
            f'/courses/{self.course.pk}/upload-material/',
            {'title': 'Lecture Notes', 'file': test_file},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CourseMaterial.objects.filter(
                course=self.course, title='Lecture Notes',
            ).exists()
        )


class FeedbackTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='Feedback Course',
            description='Course for feedback tests',
            teacher=self.teacher,
        )
        Enrolment.objects.create(
            student=self.student, course=self.course,
            status=Enrolment.APPROVED,
        )

    def test_leave_feedback(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.post(
            f'/courses/{self.course.pk}/feedback/',
            {'rating': 4, 'comment': 'Great course!'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Feedback.objects.filter(
                student=self.student, course=self.course,
            ).exists()
        )

    def test_feedback_unique_per_course(self):
        Feedback.objects.create(
            student=self.student, course=self.course,
            rating=5, comment='First review',
        )
        with self.assertRaises(IntegrityError):
            Feedback.objects.create(
                student=self.student, course=self.course,
                rating=3, comment='Duplicate review',
            )


class CourseAPITest(APITestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='API Course',
            description='Course for API tests',
            teacher=self.teacher,
        )
        self.client = APIClient()

    def test_course_list_api(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_course_create_api_teacher(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post('/api/courses/', {
            'title': 'API Created Course',
            'description': 'Created via API',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Course.objects.filter(title='API Created Course').exists()
        )

    def test_course_create_api_student_forbidden(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/courses/', {
            'title': 'Should Fail',
            'description': 'Students cannot create',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enrol_api(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/courses/{self.course.pk}/enrol/',
            format='json',
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )
        self.assertTrue(
            Enrolment.objects.filter(
                student=self.student, course=self.course,
            ).exists()
        )

    def test_blocked_student_cannot_enrol(self):
        Enrolment.objects.create(
            student=self.student, course=self.course, blocked=True,
        )
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/courses/{self.course.pk}/enrol/',
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
