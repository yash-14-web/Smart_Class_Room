from django.db import models
from django.utils import timezone
from users.models import CustomUser
from courses.models import Course


class Assignment(models.Model):

    LABEL_CHOICES = (
        ('assignment', 'Assignment'),
        ('test',       'Test'),
        ('project',    'Project'),
    )

    course      = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='assignments'
    )
    title       = models.CharField(max_length=200)
    description = models.TextField()
    due_date    = models.DateTimeField()
    total_marks = models.IntegerField(default=100)
    created_at  = models.DateTimeField(auto_now_add=True)
    attachment  = models.FileField(
        upload_to='assignment_files/', blank=True, null=True
    )
    label       = models.CharField(
        max_length=20,
        choices=LABEL_CHOICES,
        default='assignment',
        help_text='Type: Assignment, Test, or Project'
    )
    assigned_to = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='assigned_assignments',
        help_text='Select specific students to assign this to. Leave blank to assign to all enrolled students.'
    )

    def __str__(self):
        return f"{self.title} [{self.get_label_display()}] — {self.course.title}"

    def submission_count(self):
        return self.submissions.count()

    def is_overdue(self):
        return timezone.now() > self.due_date

    def label_color(self):
        return {
            'assignment': 'primary',
            'test':       'warning',
            'project':    'success',
        }.get(self.label, 'secondary')


class Submission(models.Model):
    assignment   = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name='submissions'
    )
    student      = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='submissions'
    )
    file         = models.FileField(upload_to='submissions/', blank=True, null=True)
    github_link  = models.URLField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade        = models.IntegerField(blank=True, null=True)
    feedback     = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if not self.file and not self.github_link:
            raise ValidationError('You must provide either a file or a GitHub link.')

    def __str__(self):
        return f"{self.student.username} — {self.assignment.title}"

    def percentage(self):
        if self.grade is not None and self.assignment.total_marks:
            return round((self.grade / self.assignment.total_marks) * 100, 1)
        return 0

    def pass_fail(self):
        if self.grade is None:
            return 'Pending'
        return 'Pass' if self.percentage() >= 40 else 'Fail'
