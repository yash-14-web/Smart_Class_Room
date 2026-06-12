from django.db import models
from django.utils import timezone
from users.models import CustomUser
from courses.models import Course


class AttendanceSession(models.Model):
    """Teacher creates an attendance session for a course on a date."""
    course      = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='attendance_sessions'
    )
    date        = models.DateField(default=timezone.localdate)
    topic       = models.CharField(
        max_length=200, blank=True,
        help_text='Topic covered in this class (optional)'
    )
    is_open     = models.BooleanField(
        default=False,
        help_text='When True, students can mark their own attendance'
    )
    created_by  = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='created_sessions'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    closed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ('course', 'date')

    def __str__(self):
        return f"{self.course.title} — {self.date}"

    def present_count(self):
        return self.records.filter(status='present').count()

    def absent_count(self):
        return self.records.filter(status='absent').count()

    def total_students(self):
        return self.course.enrollments.count()


class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent',  'Absent'),
    )
    session  = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name='records'
    )
    student  = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='attendance_records'
    )
    status   = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='absent'
    )
    marked_at = models.DateTimeField(auto_now_add=True)
    marked_by = models.CharField(
        max_length=10,
        choices=(('self', 'Self'), ('teacher', 'Teacher')),
        default='teacher'
    )

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student.username} — {self.session} — {self.status}"
