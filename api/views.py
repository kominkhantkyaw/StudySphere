from django.db.models import Q
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from analytics.models import Activity
from analytics.services import get_weekly_engagement, log_activity
from accounts.permissions import IsStudent, IsTeacher
from accounts.serializers import RegisterSerializer, UserSerializer
from calendar_app.models import Event
from calendar_app.serializers import EventSerializer
from courses.models import Course, CourseMaterial, Enrolment, Feedback
from courses.serializers import (
    CourseMaterialSerializer,
    CourseSerializer,
    EnrolmentSerializer,
    FeedbackSerializer,
)
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from social.models import StatusUpdate
from social.serializers import StatusUpdateSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'date_joined']
    http_method_names = ['get', 'head', 'options']


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = [SearchFilter]
    search_fields = ['title', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def enrol(self, request, pk=None):
        course = self.get_object()

        if Enrolment.objects.filter(
            student=request.user, course=course, blocked=True,
        ).exists():
            return Response(
                {'detail': 'You have been blocked from this course.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        enrolment, created = Enrolment.objects.get_or_create(
            student=request.user, course=course,
            defaults={'status': Enrolment.PENDING},
        )
        if not created and enrolment.status == Enrolment.REJECTED:
            enrolment.status = Enrolment.PENDING
            enrolment.save(update_fields=['status'])
        serializer = EnrolmentSerializer(enrolment)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def feedback(self, request, pk=None):
        course = self.get_object()
        serializer = FeedbackSerializer(course.feedback.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsTeacher])
    def students(self, request, pk=None):
        course = self.get_object()
        enrolments = course.enrolments.filter(
            status=Enrolment.APPROVED,
        ).select_related('student')
        students = [
            UserSerializer(enrolment.student).data
            for enrolment in enrolments
        ]
        return Response(students)

    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        course = self.get_object()
        serializer = CourseMaterialSerializer(course.materials.all(), many=True)
        return Response(serializer.data)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(student=self.request.user)
        log_activity(self.request.user, Activity.SUBMIT, course=instance.course)


class StatusUpdateViewSet(viewsets.ModelViewSet):
    queryset = StatusUpdate.objects.all()
    serializer_class = StatusUpdateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        methods=['get'],
        url_path='user/(?P<user_id>[^/.]+)',
    )
    def user_statuses(self, request, user_id=None):
        statuses = StatusUpdate.objects.filter(user_id=user_id)
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(read=True)
        return Response({'detail': 'All notifications marked as read.'})


class CourseMaterialViewSet(viewsets.ModelViewSet):
    queryset = CourseMaterial.objects.all()
    serializer_class = CourseMaterialSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher()]
        return [IsAuthenticated()]


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['start', 'created_at']

    def get_queryset(self):
        return Event.objects.filter(
            Q(creator=self.request.user) | Q(attendees=self.request.user),
        ).distinct()

    def perform_create(self, serializer):
        event = serializer.save(creator=self.request.user)
        event.attendees.add(self.request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        event = self.get_object()
        event.attendees.add(request.user)
        return Response({'detail': 'Joined event.'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        event = self.get_object()
        if event.creator == request.user:
            return Response(
                {'detail': 'Creator cannot leave their own event.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        event.attendees.remove(request.user)
        return Response({'detail': 'Left event.'})


class WeeklyEngagementView(APIView):
    """
    GET /api/analytics/weekly-engagement/
    Returns 7-day rolling window: daily active students and submissions for the teacher's courses.
    Teacher-only.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        payload = get_weekly_engagement(request.user)
        # API contract: data items with date, active_students, submissions (optional day_label)
        payload['data'] = [
            {
                'date': row['date'],
                'day': row['day_label'],
                'active_students': row['active_students'],
                'submissions': row['submissions'],
            }
            for row in payload['data']
        ]
        return Response(payload)
