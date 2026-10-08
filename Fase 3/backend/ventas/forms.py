from django import forms
from .models import ServicioBelleza, Cliente, Cita


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "rut", "email", "telefono", "comuna", "activo"]


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ["cliente", "servicio", "fecha", "hora", "estado", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

class ServicioForm(forms.ModelForm):
    class Meta:
        model = ServicioBelleza
        fields = ["nombre", "descripcion", "duracion_minutos", "precio", "activo"]