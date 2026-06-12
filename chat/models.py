from django.db import models
from users.models import CustomUser


class Message(models.Model):
    sender    = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                  related_name='sent_messages')
    receiver  = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                  related_name='received_messages')
    message   = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.message[:40]}"


class GroupMessage(models.Model):
    """Optional: Course group chat messages."""
    from courses.models import Course
    course    = models.ForeignKey(Course, on_delete=models.CASCADE,
                                  related_name='group_messages')
    sender    = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                  related_name='group_sent_messages')
    message   = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.course.title}] {self.sender.username}: {self.message[:40]}"
