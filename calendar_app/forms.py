from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    start = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
        ),
    )
    end = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
        ),
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'course', 'event_type', 'start', 'end']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].required = False
        if user:
            from courses.models import Course, Enrolment
            if user.is_teacher():
                self.fields['course'].queryset = Course.objects.filter(teacher=user)
            else:
                enrolled_ids = Enrolment.objects.filter(
                    student=user, status=Enrolment.APPROVED, blocked=False,
                ).values_list('course_id', flat=True)
                self.fields['course'].queryset = Course.objects.filter(id__in=enrolled_ids)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        if start and end and end <= start:
            raise forms.ValidationError('End time must be after start time.')
        return cleaned_data
