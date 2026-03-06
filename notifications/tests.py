from django.test import TestCase

from accounts.models import User
from courses.models import Course, CourseMaterial, Enrolment

from .models import Notification


class NotificationSignalTest(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='TestPass123!', role='TEACHER',
        )
        self.student = User.objects.create_user(
            username='student1', password='TestPass123!', role='STUDENT',
        )
        self.course = Course.objects.create(
            title='Signal Course',
            description='Course for signal tests',
            teacher=self.teacher,
        )

    def test_enrolment_notifies_teacher(self):
        Enrolment.objects.create(student=self.student, course=self.course)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.teacher,
                message__contains=self.student.username,
            ).exists()
        )

    def test_material_upload_notifies_students(self):
        Enrolment.objects.create(
            student=self.student, course=self.course,
            status=Enrolment.APPROVED,
        )
        initial_count = Notification.objects.filter(
            recipient=self.student,
        ).count()

        CourseMaterial.objects.create(
            course=self.course, title='Week 1 Notes',
            file='course_materials/test.pdf',
        )
        new_count = Notification.objects.filter(
            recipient=self.student,
        ).count()
        self.assertEqual(new_count, initial_count + 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                message__contains='Week 1 Notes',
            ).exists()
        )


class NotificationViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='notifuser', password='TestPass123!', role='STUDENT',
        )
        self.client.login(username='notifuser', password='TestPass123!')

    def test_notification_list(self):
        Notification.objects.create(
            recipient=self.user, message='Test notification',
        )
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test notification')

    def test_mark_read(self):
        notification = Notification.objects.create(
            recipient=self.user, message='Unread notification',
        )
        self.assertFalse(notification.read)
        response = self.client.post(
            f'/notifications/{notification.pk}/read/',
        )
        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.read)

    def test_mark_all_read(self):
        Notification.objects.create(
            recipient=self.user, message='Notif 1',
        )
        Notification.objects.create(
            recipient=self.user, message='Notif 2',
        )
        Notification.objects.create(
            recipient=self.user, message='Notif 3',
        )

        response = self.client.post('/notifications/mark-all-read/')
        self.assertEqual(response.status_code, 302)
        unread = Notification.objects.filter(
            recipient=self.user, read=False,
        ).count()
        self.assertEqual(unread, 0)
