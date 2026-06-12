from django.db import models
from users.models import CustomUser
from courses.models import Course


class Certificate(models.Model):
    BADGE_TYPES = (
        ('completion',  'Course Completion'),
        ('excellence',  'Excellence Award'),
        ('topper',      'Course Topper'),
        ('participation','Participation'),
    )
    student     = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='certificates')
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    issued_by   = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='issued_certificates')
    badge_type  = models.CharField(max_length=20, choices=BADGE_TYPES, default='completion')
    title       = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    issued_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course', 'badge_type')

    def __str__(self):
        return f"{self.badge_type} — {self.student.username} — {self.course.title}"

    def badge_color(self):
        colors = {
            'completion':   '#1A56DB',
            'excellence':   '#D97706',
            'topper':       '#059669',
            'participation':'#7C3AED',
        }
        return colors.get(self.badge_type, '#1A56DB')

    def badge_color_dark(self):
        colors = {
            'completion':   '#0f3fae',
            'excellence':   '#b45309',
            'topper':       '#047857',
            'participation':'#5b21b6',
        }
        return colors.get(self.badge_type, '#0f3fae')

    def badge_icon(self):
        icons = {
            'completion':   'bi-award-fill',
            'excellence':   'bi-star-fill',
            'topper':       'bi-trophy-fill',
            'participation':'bi-patch-check-fill',
        }
        return icons.get(self.badge_type, 'bi-award-fill')
