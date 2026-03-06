from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=255)
    # Rich description (HTML stored as text; edited with toolbar in the UI)
    description = models.TextField()
    # Optional hero image or graphic for the course (uploaded then mirrored to Supabase)
    hero_image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    # Public URL of the image stored in Supabase
    hero_image_url = models.URLField(blank=True, default='')
    # When the course or first session starts/ends
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    # Meta information shown in the course footer
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total duration in minutes (e.g. 45, 90, 120).',
    )
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Course fee (leave empty if free).',
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text='Physical or virtual location (e.g. Zoom link, classroom).',
    )
    organiser = models.CharField(
        max_length=255,
        blank=True,
        help_text='Organisation or person responsible for this course.',
    )
    LIMITED = 'LIMITED'
    UNLIMITED = 'UNLIMITED'
    CAPACITY_CHOICES = [
        (LIMITED, 'Limited'),
        (UNLIMITED, 'Unlimited'),
    ]
    capacity_type = models.CharField(
        max_length=10,
        choices=CAPACITY_CHOICES,
        default=UNLIMITED,
        help_text='Whether places are limited or unlimited.',
    )
    ONLINE = 'ONLINE'
    ONSITE = 'ONSITE'
    DELIVERY_CHOICES = [
        (ONLINE, 'Online'),
        (ONSITE, 'On-site'),
    ]
    delivery_mode = models.CharField(
        max_length=10,
        choices=DELIVERY_CHOICES,
        default=ONLINE,
        help_text='How the course is delivered.',
    )
    LANGUAGE_EN = 'EN'
    LANGUAGE_DE = 'DE'
    LANGUAGE_AR = 'AR'
    LANGUAGE_ZH = 'ZH'
    LANGUAGE_FR = 'FR'
    LANGUAGE_RU = 'RU'
    LANGUAGE_ES = 'ES'
    LANGUAGE_OTHER = 'OTHER'
    LANGUAGE_CHOICES = [
        (LANGUAGE_EN, 'English'),
        (LANGUAGE_DE, 'German'),
        (LANGUAGE_AR, 'Arabic'),
        (LANGUAGE_ZH, 'Chinese'),
        (LANGUAGE_FR, 'French'),
        (LANGUAGE_RU, 'Russian'),
        (LANGUAGE_ES, 'Spanish'),
        (LANGUAGE_OTHER, 'Other'),
    ]
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_EN,
        help_text='Main language used in this course.',
    )
    CATEGORY_LANGUAGES = 'LANGUAGES'
    CATEGORY_AI = 'AI'
    CATEGORY_CYBER = 'CYBER'
    CATEGORY_DATA = 'DATA'
    CATEGORY_WEB = 'WEB'
    CATEGORY_OTHER = 'OTHER'
    CATEGORY_CHOICES = [
        (CATEGORY_LANGUAGES, 'Languages'),
        (CATEGORY_AI, 'AI'),
        (CATEGORY_CYBER, 'Cyber Security'),
        (CATEGORY_DATA, 'Data Analysis'),
        (CATEGORY_WEB, 'Web Development'),
        (CATEGORY_OTHER, 'Other'),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
        blank=True,
        help_text='Course category for browsing.',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='taught_courses',
    )
    is_general = models.BooleanField(
        default=False,
        help_text='If True, this is the General announcement room; all authenticated users can join.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def duration_hours(self):
        if self.duration_minutes:
            return round(self.duration_minutes / 60, 1)
        return None


class Enrolment(models.Model):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrolments',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrolments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,  # Every first enrolment appears as Pending until teacher approves
    )
    blocked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.username} → {self.course.title}"


class Certificate(models.Model):
    """Certificate issued by teacher for an approved enrolment. Student can view/download."""
    STATUS_ISSUED = 'ISSUED'
    STATUS_REVOKED = 'REVOKED'
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_CHOICES = [
        (STATUS_ISSUED, 'Issued'),
        (STATUS_REVOKED, 'Revoked'),
        (STATUS_EXPIRED, 'Expired'),
    ]
    enrolment = models.OneToOneField(
        Enrolment,
        on_delete=models.CASCADE,
        related_name='certificate',
    )
    file = models.FileField(upload_to='certificates/%Y/%m/', blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_ISSUED,
        help_text='Lifecycle status of this certificate.',
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_certificates',
    )
    # Public URL if the certificate file is stored in Supabase
    certificate_url = models.URLField(blank=True, default='')

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate for {self.enrolment}"


class CourseMaterial(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='materials',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materials_authored',
        help_text='Teacher who uploaded this material.',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='course_materials/', blank=True)
    # Public URL if the material file is stored in Supabase
    material_url = models.URLField(blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.course.title})"


class StudentSubmission(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_submissions',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='course_submissions/', blank=True)
    # Public URL if the submission file is stored in Supabase
    file_url = models.URLField(blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} — {self.student.username} ({self.course.title})"


class VideoResource(models.Model):
    """YouTube or other video link for course materials; listed on the Videos page."""
    title = models.CharField(max_length=255)
    url = models.URLField(help_text='YouTube or video URL.')
    description = models.TextField(blank=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='video_resources',
        help_text='Leave empty for global/platform-wide videos.',
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_videos',
    )
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower first).')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


class Feedback(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_given',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='feedback',
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.rating}/5)"
