from django.db import models
from django.conf import settings

# 1. Base Model for common fields (DRY Principle)
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# 2. Category: Separated to avoid data repetition (3NF)
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

# 3. Course: The main entity
class Course(TimestampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='taught_courses')
    
    # Many-to-Many: Students can have many courses, and courses have many students
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Enrollment', related_name='enrolled_courses')

    def __str__(self):
        return self.title

# 4. Lesson: One-to-Many relationship with Course
class Lesson(TimestampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField()  # Or FileField for videos
    order = models.PositiveIntegerField(help_text="Sequence of the lesson in the course")

    class Meta:
        ordering = ['order']

# 5. Enrollment: Junction table to store relationship-specific data
class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_on = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course') # Prevents double enrollment
