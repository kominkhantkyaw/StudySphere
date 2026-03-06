from django import forms

from .models import User


class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            if user.role == 'STUDENT' and not user.student_id:
                user.get_or_set_student_id()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'address', 'presence', 'status_text', 'bio', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, Country'}),
            'presence': forms.Select(attrs={'class': 'form-select'}),
            'status_text': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. Studying now, Taking a break, Listening to Music',
                    'maxlength': 200,
                }
            ),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class GeneralSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['preferred_language', 'theme_mode', 'notify_email', 'notify_in_app', 'share_activity']
        widgets = {
            'preferred_language': forms.Select(attrs={'class': 'form-select'}),
            'theme_mode': forms.Select(attrs={'class': 'form-select'}),
            'notify_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_in_app': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'share_activity': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
