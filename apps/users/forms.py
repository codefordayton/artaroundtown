from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=True, label='Last name')
    email = forms.EmailField(required=True)
    organization = forms.CharField(
        max_length=200,
        required=False,
        label='Organization / affiliation',
        help_text='Gallery, arts org, school, or other affiliation (optional)',
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'organization', 'password1', 'password2',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.organization = self.cleaned_data.get('organization', '')
        user.is_approved_submitter = False
        if commit:
            user.save()
        return user
