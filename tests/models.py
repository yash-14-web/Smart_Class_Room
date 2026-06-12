from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from courses.models import Course


class Test(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='tests',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    total_marks = models.PositiveIntegerField(default=0)
    time_limit = models.PositiveIntegerField(help_text='Time limit in minutes')
    available_from = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    notebook_file = models.FileField(upload_to='test_notebooks/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tests'
    )
    created_at = models.DateTimeField(default=timezone.now)
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_tests',
        help_text='Select specific students to assign this to. Leave blank to assign to all enrolled students.'
    )

    def __str__(self):
        return f"{self.title} - {self.course.title if self.course else 'No Course'}"

    def is_open(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.available_from and now < self.available_from:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def status_label(self):
        if not self.is_active:
            return 'Inactive'
        if self.end_date and self.end_date < timezone.now():
            return 'Closed'
        if self.available_from and self.available_from > timezone.now():
            return 'Upcoming'
        return 'Open'

    def refresh_total_marks(self):
        total = self.questions.aggregate(total=Sum('marks'))['total'] or 0
        if self.total_marks != total:
            self.total_marks = total
            self.save(update_fields=['total_marks'])
        return total

    @property
    def coding_questions_count(self):
        return self.questions.filter(question_type=Question.QUESTION_TYPE_CODING).count()

    @property
    def mcq_questions_count(self):
        return self.questions.filter(question_type=Question.QUESTION_TYPE_MCQ).count()


class Question(models.Model):
    ANSWER_CHOICES = [
        ('option1', 'Option 1'),
        ('option2', 'Option 2'),
        ('option3', 'Option 3'),
        ('option4', 'Option 4'),
    ]
    QUESTION_TYPE_MCQ = 'mcq'
    QUESTION_TYPE_CODING = 'coding'
    QUESTION_TYPE_CHOICES = [
        (QUESTION_TYPE_MCQ, 'Quiz / Multiple Choice'),
        (QUESTION_TYPE_CODING, 'Coding Question'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default=QUESTION_TYPE_MCQ,
    )
    question_text = models.TextField()
    code_cell = models.TextField(blank=True, null=True)
    starter_code = models.TextField(blank=True, null=True)
    expected_function_name = models.CharField(max_length=120, blank=True)
    option1 = models.CharField(max_length=255, blank=True, null=True)
    option2 = models.CharField(max_length=255, blank=True, null=True)
    option3 = models.CharField(max_length=255, blank=True, null=True)
    option4 = models.CharField(max_length=255, blank=True, null=True)
    correct_answer = models.CharField(max_length=10, choices=ANSWER_CHOICES, blank=True)
    marks = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.test.title} - {self.question_text[:50]}"

    def is_coding(self):
        return self.question_type == self.QUESTION_TYPE_CODING

    def is_mcq(self):
        return self.question_type == self.QUESTION_TYPE_MCQ

    @property
    def sample_case_count(self):
        return self.test_cases.filter(is_sample=True).count()

    @property
    def hidden_case_count(self):
        return self.test_cases.filter(is_sample=False).count()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.test.refresh_total_marks()

    def delete(self, *args, **kwargs):
        test = self.test
        super().delete(*args, **kwargs)
        test.refresh_total_marks()


class CodingTestCase(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='test_cases',
    )
    order = models.PositiveIntegerField(default=1)
    input_data = models.TextField(
        help_text='Use JSON array format for function arguments. Example: [[1, 2, 3]]'
    )
    expected_output = models.TextField(
        help_text='Expected return value in JSON format. Example: 6 or [1, 4, 9]'
    )
    is_sample = models.BooleanField(
        default=False,
        help_text='Sample tests are visible to students during practice runs.',
    )
    weight = models.PositiveIntegerField(default=1)
    explanation = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        kind = 'Sample' if self.is_sample else 'Hidden'
        return f"{kind} case for {self.question.test.title}"


class StudentResponse(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='test_responses'
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='responses')
    score = models.FloatField(default=0)
    quiz_score = models.FloatField(default=0)
    coding_score = models.FloatField(default=0)
    answers_payload = models.JSONField(default=dict, blank=True)
    coding_submissions = models.JSONField(default=dict, blank=True)
    evaluation_summary = models.JSONField(default=list, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'test'],
                name='unique_student_test_response',
            )
        ]

    def __str__(self):
        return f"{self.student.username} - {self.test.title} ({self.score})"

