from django.db import models
from users.models import CustomUser
from courses.models import Course


class Quiz(models.Model):
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration    = models.IntegerField(default=30, help_text='Duration in minutes')
    total_marks = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    start_date  = models.DateTimeField(null=True, blank=True)
    due_date    = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='assigned_quizzes',
        help_text='Select specific students to assign this to. Leave blank to assign to all enrolled students.'
    )

    def __str__(self):
        return f"{self.title} — {self.course.title}"

    def is_open(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.due_date and now > self.due_date:
            return False
        return True

    def question_count(self):
        return self.questions.count()

    def calculate_total(self):
        total = sum(q.marks for q in self.questions.all())
        self.total_marks = total
        self.save()


class Question(models.Model):
    quiz    = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text    = models.TextField()
    marks   = models.IntegerField(default=1)
    order   = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}"


class Choice(models.Model):
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text       = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'Wrong'})"


class QuizAttempt(models.Model):
    quiz       = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student    = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='quiz_attempts')
    score      = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at= models.DateTimeField(null=True, blank=True)
    is_complete= models.BooleanField(default=False)

    class Meta:
        unique_together = ('quiz', 'student')

    def __str__(self):
        return f"{self.student.username} — {self.quiz.title} — {self.score}"

    def percentage(self):
        if self.quiz.total_marks:
            return round((self.score / self.quiz.total_marks) * 100, 1)
        return 0


class StudentAnswer(models.Model):
    attempt  = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice   = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def is_correct(self):
        return self.choice and self.choice.is_correct
