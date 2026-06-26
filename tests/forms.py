from django import forms

from .models import CodingTestCase, Question, Test


class BootstrapFormMixin:
    def add_bootstrap_classes(self):
        for field_name, field in self.fields.items():
            current_class = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            elif isinstance(field.widget, forms.CheckboxInput):
                if 'form-check-input' not in current_class:
                    field.widget.attrs['class'] = f'{current_class} form-check-input'.strip()
            elif isinstance(field.widget, forms.Select):
                if 'form-select' not in current_class:
                    field.widget.attrs['class'] = f'{current_class} form-select'.strip()
            else:
                if 'form-control' not in current_class:
                    field.widget.attrs['class'] = f'{current_class} form-control'.strip()

class TestCreateForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        if user:
            from courses.models import Course
            self.fields['course'].queryset = Course.objects.filter(teacher=user)
        self.fields['course'].required = True

        selected_course = course
        if not selected_course and self.data and self.data.get('course'):
            from courses.models import Course
            try:
                selected_course = Course.objects.get(pk=self.data.get('course'))
            except (Course.DoesNotExist, ValueError):
                pass
        if not selected_course and self.instance and self.instance.pk:
            selected_course = self.instance.course

        if selected_course:
            from courses.models import Enrollment
            from users.models import CustomUser
            student_ids = Enrollment.objects.filter(course=selected_course, status='approved').values_list('student_id', flat=True)
            self.fields['assigned_to'].queryset = CustomUser.objects.filter(id__in=student_ids)
            self.fields['assigned_to'].widget.attrs.update({'class': 'form-check-input'})
        else:
            from users.models import CustomUser
            self.fields['assigned_to'].queryset = CustomUser.objects.none()

        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].label = "Assign to specific students"
        self.fields['assigned_to'].help_text = "Select specific students. Leave empty to assign to ALL enrolled students."
        self.add_bootstrap_classes()

    available_from = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Test
        fields = ['course', 'title', 'description', 'time_limit', 'available_from', 'end_date', 'is_active', 'notebook_file', 'assigned_to']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assigned_to': forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            'notebook_file': 'Optional starter notebook, dataset instructions, or reference material.',
        }


class QuestionCreateForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_bootstrap_classes()

    class Meta:
        model = Question
        fields = [
            'question_type',
            'question_text',
            'code_cell',
            'starter_code',
            'reference_solution',
            'expected_function_name',
            'option1',
            'option2',
            'option3',
            'option4',
            'correct_answer',
            'marks',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
            'code_cell': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add extra instructions, dataset notes, or problem explanation'}),
            'starter_code': forms.Textarea(attrs={'rows': 10, 'class': 'font-monospace code-editor', 'placeholder': 'def solve(...):\n    pass'}),
            'reference_solution': forms.Textarea(attrs={'rows': 10, 'class': 'font-monospace code-editor', 'placeholder': 'def solve(...):\n    # Complete correct solution implementation\n    return ...'}),
        }
        help_texts = {
            'expected_function_name': 'For coding questions, enter the function students must implement. Example: solve or train_model.',
        }

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')

        if question_type == Question.QUESTION_TYPE_MCQ:
            required_fields = ['option1', 'option2', 'option3', 'option4', 'correct_answer']
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, 'This field is required for quiz questions.')
        elif question_type == Question.QUESTION_TYPE_CODING:
            if not cleaned_data.get('expected_function_name'):
                self.add_error('expected_function_name', 'Function name is required for coding questions.')

        return cleaned_data


class CodingTestCaseForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_bootstrap_classes()

    class Meta:
        model = CodingTestCase
        fields = ['order', 'input_data', 'expected_output', 'is_sample', 'weight', 'explanation']
        widgets = {
            'input_data': forms.Textarea(attrs={'rows': 3, 'class': 'font-monospace'}),
            'expected_output': forms.Textarea(attrs={'rows': 3, 'class': 'font-monospace'}),
            'is_sample': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'explanation': forms.TextInput(attrs={'placeholder': 'Optional note shown in teacher review'}),
        }


class TestTakeForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        if questions is None:
            questions = []
        for question in questions:
            if question.question_type == Question.QUESTION_TYPE_MCQ:
                choices = [
                    ('option1', question.option1),
                    ('option2', question.option2),
                    ('option3', question.option3),
                    ('option4', question.option4),
                ]
                self.fields[f'question_{question.pk}'] = forms.ChoiceField(
                    label=question.question_text,
                    choices=choices,
                    widget=forms.RadioSelect,
                    required=True,
                )
            else:
                self.fields[f'code_{question.pk}'] = forms.CharField(
                    label=question.question_text,
                    widget=forms.Textarea(
                        attrs={
                            'rows': 12,
                            'class': 'form-control font-monospace code-editor',
                            'spellcheck': 'false',
                        }
                    ),
                    required=True,
                    initial=question.starter_code or '',
                    help_text='Write Python code that defines the required function. Hidden backend tests will grade the final answer.',
                )

