from django.test import TestCase

from accounts.models import User
from courses.models import Course, Enrolment

from .models import Message


class ChatViewTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.other_student = User.objects.create_user(
            username='student2', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='Chat Course',
            description='Course for chat tests',
            teacher=self.teacher,
        )
        Enrolment.objects.create(
            student=self.student, course=self.course, status=Enrolment.APPROVED,
        )

    def test_chat_lobby(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.get('/chat/')
        self.assertEqual(response.status_code, 200)

    def test_chat_room_enrolled(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.get(f'/chat/{self.course.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_chat_room_not_enrolled(self):
        self.client.login(username='student2', password='TestPass123!')
        response = self.client.get(f'/chat/{self.course.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_chat_room_teacher(self):
        self.client.login(username='teacher1', password='TestPass123!')
        response = self.client.get(f'/chat/{self.course.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_chat_teachers_room_teacher(self):
        self.client.login(username='teacher1', password='TestPass123!')
        response = self.client.get('/chat/teachers/')
        self.assertEqual(response.status_code, 200)

    def test_chat_teachers_room_student_forbidden(self):
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.get('/chat/teachers/')
        self.assertEqual(response.status_code, 403)


class MessageModelTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.course = Course.objects.create(
            title='Message Course',
            description='Course for message tests',
            teacher=self.teacher,
        )

    def test_message_creation(self):
        message = Message.objects.create(
            course=self.course,
            sender=self.teacher,
            content='Hello class!',
        )
        self.assertEqual(message.content, 'Hello class!')
        self.assertEqual(message.sender, self.teacher)
        self.assertEqual(message.course, self.course)

    def test_message_str(self):
        message = Message.objects.create(
            course=self.course,
            sender=self.teacher,
            content='Welcome everyone to the course',
        )
        self.assertIn(self.teacher.username, str(message))
        self.assertIn(self.course.title, str(message))
