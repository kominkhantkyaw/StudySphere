from django import forms

from .models import StatusUpdate


class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StatusUpdate
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "What's on your mind?",
                'class': 'form-control',
            }),
            'attachment': forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*,video/*,.pdf'}),
        }
