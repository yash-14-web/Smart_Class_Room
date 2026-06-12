from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_zip(value):
    if not str(value.name).lower().endswith('.zip'):
        raise ValidationError('Only .zip files are allowed for project submissions.')


class ProjectSubmission(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_submissions'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='project_submissions',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Describe the project and use case.')
    technologies_used = models.CharField(max_length=255)
    github_link = models.URLField()
    zip_file = models.FileField(upload_to='project_submissions/', validators=[validate_zip])
    score = models.PositiveIntegerField(null=True, blank=True)
    total_marks = models.PositiveIntegerField(default=100)
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_projects'
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.student.username} - {self.title}"

    @property
    def grade_letter(self):
        if self.score is None or self.total_marks == 0:
            return None
        percentage = (self.score / self.total_marks) * 100
        if percentage >= 90:
            return 'A'
        if percentage >= 75:
            return 'B'
        return 'C'
