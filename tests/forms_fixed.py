from django import forms

from .models import CodingTestCase, Question, Test


class TestCreateForm(forms.ModelForm):
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
        fields = ['title', 'description', 'time_limit', 'available_from', 'end_date', 'is_active', 'notebook_file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'notebook_file': 'Optional starter notebook, dataset instructions, or reference material.',
        }


class QuestionCreateForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_type',
            'question_text',
            'code_cell',
            'starter_code',
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
            'starter_code': forms.Textarea(attrs={'rows': 10, 'class': 'font-monospace', 'placeholder': 'def solve(...):\n    pass'}),
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


class CodingTestCaseForm(forms.ModelForm):
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
                            'class': 'form-control font-monospace',
                            'spellcheck': 'false',
                        }
                    ),
                    required=True,
                    initial=question.starter_code or '',
                    help_text='Write Python code that defines the required function. Hidden backend tests will grade the final answer.',
                )
