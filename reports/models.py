from django.conf import settings
from django.db import models
from django.utils import timezone
from courses.models import Course


class ReportCard(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_cards'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='report_cards',
        null=True,
        blank=True,
    )
    assignment_score = models.PositiveIntegerField(default=0)
    quiz_score = models.PositiveIntegerField(default=0)
    test_score = models.PositiveIntegerField(default=0)
    overall_score = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'course')

    def calculate_overall_score(self):
        return self.assignment_score + self.quiz_score + self.test_score

    def save(self, *args, **kwargs):
        self.overall_score = self.calculate_overall_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} — {self.course.title} Report"
