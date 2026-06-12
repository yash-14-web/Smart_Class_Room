from django import forms
from .models import ReportCard


class ReportCardUpdateForm(forms.ModelForm):
    class Meta:
        model = ReportCard
        fields = ['student', 'course', 'assignment_score', 'quiz_score', 'test_score']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
        }
