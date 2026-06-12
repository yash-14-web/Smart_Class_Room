from django import forms
from courses.models import Course
from .models import ProjectSubmission


class ProjectSubmissionForm(forms.ModelForm):
    class Meta:
        model = ProjectSubmission
        fields = ['course', 'title', 'description', 'technologies_used', 'github_link', 'zip_file']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the project and use case'}),
            'technologies_used': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, Machine Learning'}),
            'github_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/your-repo'}),
            'zip_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            if not user.is_teacher():
                self.fields['course'].queryset = Course.objects.filter(enrollments__student=user).distinct()
            else:
                self.fields['course'].queryset = Course.objects.all()

    def clean_github_link(self):
        link = self.cleaned_data.get('github_link')
        if not link:
            raise forms.ValidationError('GitHub link must not be empty.')
        return link


class ProjectGradeForm(forms.ModelForm):
    class Meta:
        model = ProjectSubmission
        fields = ['score', 'total_marks', 'feedback']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
