from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RecordedClass(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='recorded_classes/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='recorded_classes',
        null=True,
        blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recorded_classes'
    )
    uploaded_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        if not self.video_file and not self.video_url:
            raise ValidationError('Please provide a video file or a video URL.')

    def __str__(self):
        return self.title
