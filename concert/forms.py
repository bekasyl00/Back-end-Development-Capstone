from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.models import User
from django import forms


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        max_length=50,
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control",
                "data-toggle": "password",
                "id": "password",
                "name": "password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "password"]


class SignUpForm(forms.Form):
    username = forms.CharField(
        max_length=100,
        required=True,
        validators=[UnicodeUsernameValidator()],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        max_length=50,
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control",
                "data-toggle": "password",
                "id": "password",
                "name": "password",
                "minlength": "3"
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "password"]

    def clean_password(self):
        password = self.cleaned_data["password"]
        user = User(username=self.cleaned_data.get("username", ""))
        validate_password(password, user=user)
        return password
