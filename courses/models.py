from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField
from uuid import uuid4


class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            if not base_slug:
                base_slug = f"course-{uuid4().hex[:8]}"
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    # content = models.TextField()
    content = RichTextUploadingField()
    youtube_url = models.URLField(blank=True, null=True, help_text="Вставте посилання на відео з YouTube")
    image = models.ImageField(upload_to='lesson_images/', blank=True, null=True)  # додамо можливість вставляти фото
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
class ContentBlock(models.Model):
    TEXT = 'text'
    IMAGE = 'image'
    VIDEO = 'video'
    FILE = 'file'
    LINK = 'link'

    CONTENT_TYPES = [
        (TEXT, 'Текст'),
        (IMAGE, 'Зображення (URL)'),
        (VIDEO, 'Відео (YouTube URL)'),
        (FILE, 'Файл (PDF, DOCX, тощо)'),
        (LINK, 'Посилання'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='blocks')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


    
class LessonImage(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='lesson_images/')

class LessonAttachment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='lesson_attachments/')
    name = models.CharField(max_length=255)

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