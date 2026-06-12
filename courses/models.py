from django.db import models
from django.utils import timezone
from users.models import CustomUser

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='courses_taught')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cover_image = models.ImageField(upload_to='course_covers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    project_start_date = models.DateTimeField(null=True, blank=True, help_text='Start date for project submissions')
    project_end_date = models.DateTimeField(null=True, blank=True, help_text='End date/deadline for project submissions')
    results_released = models.BooleanField(default=False, help_text='Allow students to view pass/fail results for this course')

    def __str__(self):
        return self.title

    def is_started(self):
        if self.start_date is None:
            return True
        return timezone.now() >= self.start_date

    def is_available(self):
        if not self.is_active:
            return False
        if self.start_date and timezone.now() < self.start_date:
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True

    def is_project_submission_open(self):
        # If neither project start nor end date is configured, no project is required/active.
        if self.project_start_date is None and self.project_end_date is None:
            return False
        now = timezone.now()
        if self.project_start_date and now < self.project_start_date:
            return False
        if self.project_end_date and now > self.project_end_date:
            return False
        return True

    def status_label(self):
        if not self.is_active:
            return 'Inactive'
        if self.start_date and timezone.now() < self.start_date:
            return 'Starts soon'
        if self.end_date and timezone.now() > self.end_date:
            return 'Ended'
        return 'Active'

    def results_visible(self):
        return self.results_released

    def student_count(self):
        return self.enrollments.count()

    def student_count(self):
        return self.enrollments.count()

class Enrollment(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} in {self.course.title}"
