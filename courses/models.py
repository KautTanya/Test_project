from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='lesson_images/', blank=True, null=True)  # додамо можливість вставляти фото
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.module.title} - {self.title}"

class UserCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    order_reference = models.CharField(max_length=255, unique=True, null=True, blank=True)

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

class Payment(models.Model):
    order_reference = models.CharField(max_length=255, unique=True)
    amount          = models.DecimalField(max_digits=8, decimal_places=2)
    currency        = models.CharField(max_length=3)
    status          = models.CharField(max_length=32)        # напр. "Approved" або "Declined"
    response_data   = models.JSONField()                     # зберігаємо увесь payload
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_reference} – {self.status}"