from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin',   'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    STATUS_CHOICES = (
        ('pending',  'Pending Approval'),
        ('active',   'Active'),
        ('rejected', 'Rejected'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    cover_pic = models.ImageField(upload_to='cover_pics/', blank=True, null=True)
    cover_preset = models.CharField(max_length=50, default='nebula')
    cover_position = models.IntegerField(default=50)
    bio = models.TextField(blank=True, null=True)
    account_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def is_admin(self):
        return self.is_superuser or self.role == 'admin'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"{self.username} ({self.role})"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.account_status = 'active'
            self.role = 'admin'       # Superusers are always Admin
        
        # Auto-generate Student ID for student accounts if not already set
        if self.role == 'student' and not self.student_id:
            import datetime
            current_year = datetime.datetime.now().year
            prefix = f"STU-{current_year}"
            
            # Find the last student ID for the current year
            last_student = CustomUser.objects.filter(
                role='student',
                student_id__startswith=prefix
            ).order_by('-student_id').first()
            
            if last_student and last_student.student_id:
                try:
                    # Extract sequence suffix (the digits after STU-YYYY)
                    suffix = last_student.student_id[len(prefix):]
                    next_num = int(suffix) + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            
            self.student_id = f"{prefix}{next_num:02d}"
            
        super().save(*args, **kwargs)


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, help_text="e.g. assignment, quiz, test, enrollment, grade")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.is_read}"


def notify_user(user, title, message, notification_type):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )


