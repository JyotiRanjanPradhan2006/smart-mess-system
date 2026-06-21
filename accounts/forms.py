"""accounts/forms.py"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, StudentProfile


class StudentRegistrationForm(UserCreationForm):
    first_name  = forms.CharField(max_length=50, required=True)
    last_name   = forms.CharField(max_length=50, required=True)
    email       = forms.EmailField(required=True)
    phone       = forms.CharField(max_length=15, required=False)
    roll_number = forms.CharField(max_length=20)
    department  = forms.CharField(max_length=100, required=False)
    year_of_study = forms.IntegerField(min_value=1, max_value=6, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name   = self.cleaned_data['first_name']
        user.last_name    = self.cleaned_data['last_name']
        user.email        = self.cleaned_data['email']
        user.phone        = self.cleaned_data.get('phone', '')
        user.role         = User.Role.STUDENT
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                roll_number=self.cleaned_data['roll_number'],
                department=self.cleaned_data.get('department', ''),
                year_of_study=self.cleaned_data.get('year_of_study'),
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )
