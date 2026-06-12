from django.db import models
from users.models import CustomUser
from courses.models import Course

class Material(models.Model):
    MATERIAL_TYPES = (
        ('pdf', 'PDF Document'),
        ('doc', 'Word Document'),
        ('ppt', 'Presentation'),
        ('zip', 'ZIP Archive'),
        ('py', 'Python File'),
        ('other', 'Other'),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/')
    material_type = models.CharField(max_length=10, choices=MATERIAL_TYPES, default='other')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    def filename(self):
        return self.file.name.split('/')[-1]

    def file_extension(self):
        name = self.file.name
        return name.split('.')[-1].lower() if '.' in name else ''
