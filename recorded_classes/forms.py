from django import forms
from .models import RecordedClass


class RecordedClassForm(forms.ModelForm):
    class Meta:
        model = RecordedClass
        fields = ['title', 'course', 'subject', 'description', 'video_file', 'video_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter class name'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter topic name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add a short summary'}),
            'video_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from courses.models import Course
            if user.is_teacher():
                self.fields['course'].queryset = Course.objects.filter(teacher=user)
            self.fields['course'].required = True

    def clean(self):
        cleaned_data = super().clean()
        video_file = cleaned_data.get('video_file')
        video_url = cleaned_data.get('video_url')
        if not video_file and not video_url:
            raise forms.ValidationError('Please upload a video file or provide a video URL.')
        return cleaned_data
