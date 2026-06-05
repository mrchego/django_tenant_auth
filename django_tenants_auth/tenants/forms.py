from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import make_password
from django_tenants_auth.tenants.models import User

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_password(self):
        password = self.cleaned_data.get("password")

        try:
            password_validation.validate_password(password=password, user=self.instance)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)

        if password and not password.startswith("pbkdf2_"):
            return make_password(password)

        return password