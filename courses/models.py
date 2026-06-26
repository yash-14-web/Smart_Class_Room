from django.db import models
from django.utils import timezone
from users.models import CustomUser

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Unique short code, e.g. CS, MATH")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    cover_image = models.ImageField(upload_to='department_covers/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Unique course code, e.g. CS-101")
    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='courses_taught')
    batch = models.CharField(max_length=100, blank=True, help_text="e.g. Batch 2024, CSE-A")
    max_students = models.PositiveIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cover_image = models.ImageField(upload_to='course_covers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    project_start_date = models.DateTimeField(null=True, blank=True, help_text='Start date for project submissions')
    project_end_date = models.DateTimeField(null=True, blank=True, help_text='End date/deadline for project submissions')
    results_released = models.BooleanField(default=False, help_text='Allow students to view pass/fail results for this course')
    approval_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )

    def __str__(self):
        return f"[{self.course_code}] {self.title}"

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

    def save(self, *args, **kwargs):
        current_year = timezone.now().year
        
        # 1. Generate short form of course title
        import re
        cleaned_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', self.title)
        words = cleaned_title.split()
        # Filter out common stop words
        stop_words = {'to', 'and', 'the', 'of', 'a', 'an', 'in', 'on', 'for', 'with', 'by', 'at'}
        important_words = [w for w in words if w.lower() not in stop_words]
        if not important_words:
            important_words = words
        
        short_form = "".join(w[0].upper() for w in important_words if w)
        if not short_form:
            short_form = "CRSE"

        # 2. Auto-generate course_code if not set
        if not self.course_code:
            year_prefix = str(current_year)
            # Find all course codes containing this year
            existing_codes = Course.objects.filter(
                course_code__contains=f"-{year_prefix}"
            ).values_list('course_code', flat=True)
            
            numeric_suffixes = []
            for code in existing_codes:
                if code and '-' in code:
                    parts = code.split('-')
                    suffix = parts[-1]
                    if len(suffix) == 6 and suffix.startswith(year_prefix) and suffix.isdigit():
                        try:
                            counter = int(suffix[4:])
                            numeric_suffixes.append(counter)
                        except ValueError:
                            pass
            
            if numeric_suffixes:
                next_num = max(numeric_suffixes) + 1
            else:
                next_num = 1
                
            self.course_code = f"{short_form}-{year_prefix}{next_num:02d}"

        # 3. Auto-generate batch if not set
        if not self.batch:
            # Determine section letter A, B, C...
            # Query count of existing courses with the same title (case-insensitive) in the same year
            same_courses_count = Course.objects.filter(
                title__iexact=self.title,
                course_code__contains=f"-{current_year}"
            ).exclude(pk=self.pk).count()
            
            section_char = chr(65 + (same_courses_count % 26))
            self.batch = f"Batch {current_year}, {short_form}-{section_char}"
            
        super().save(*args, **kwargs)

class Enrollment(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} in {self.course.title}"


class VirtualSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='virtual_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    meeting_link = models.URLField(help_text="Link to Google Meet, Zoom, MS Teams, etc.")
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        from datetime import timedelta
        return timezone.now() > (self.scheduled_at + timedelta(minutes=self.duration_minutes))

    def __str__(self):
        return f"{self.title} - {self.course.title}"


class AITutorMessage(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ai_tutor_messages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ai_tutor_messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
    action = models.CharField(max_length=20, default='general')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.sender} - {self.timestamp}"
