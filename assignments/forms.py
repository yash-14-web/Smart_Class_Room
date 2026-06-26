from django import forms
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    class Meta:
        model  = Assignment
        fields = ['title', 'description', 'label', 'due_date', 'total_marks', 'attachment', 'assigned_to']
        widgets = {
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'label':       forms.Select(attrs={'class': 'form-select'}),
            'due_date':    forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'attachment':  forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_to': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        if course:
            from courses.models import Enrollment
            from users.models import CustomUser
            student_ids = Enrollment.objects.filter(course=course, status='approved').values_list('student_id', flat=True)
            self.fields['assigned_to'].queryset = CustomUser.objects.filter(id__in=student_ids)
            self.fields['assigned_to'].widget.attrs.update({'class': 'form-check-input'})
            self.fields['assigned_to'].required = False
            self.fields['assigned_to'].label = "Assign to specific students"
            self.fields['assigned_to'].help_text = "Select specific students. Leave empty to assign to ALL enrolled students."


class SubmissionForm(forms.ModelForm):
    class Meta:
        model   = Submission
        fields  = ['file', 'github_link']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'github_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/username/repo'
            })
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model   = Submission
        fields  = ['grade', 'feedback']
        widgets = {
            'grade':    forms.NumberInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
