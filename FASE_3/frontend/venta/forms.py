# -----------------------------------------------------------
# ARCHIVO NUEVO: guárdalo como venta/forms.py
# (si ya creaste este archivo antes, reemplázalo por este)
# -----------------------------------------------------------

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]