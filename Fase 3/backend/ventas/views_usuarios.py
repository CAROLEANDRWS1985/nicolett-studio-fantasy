from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from ventas.permisos import solo_equipo

User = get_user_model()


class ColaboradorForm(forms.Form):
    nombre = forms.CharField(max_length=150)
    correo = forms.EmailField()
    clave = forms.CharField(widget=forms.PasswordInput, required=False,
                            help_text="Al editar, déjala vacía para mantener la actual.")

    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = obj
        if obj is None:
            self.fields["clave"].required = True

    def clean_correo(self):
        correo = self.cleaned_data["correo"].lower()
        otros = User.objects.filter(username=correo)
        if self.obj:
            otros = otros.exclude(pk=self.obj.pk)
        if otros.exists():
            raise forms.ValidationError("Ya existe una persona con ese correo.")
        return correo


def _colaboradores():
    return User.objects.filter(is_staff=True, is_superuser=False).order_by("first_name")


@solo_equipo
def usuarios_lista(request):
    filas = [{"obj": u, "valores": [u.first_name, u.email, "••••••"]} for u in _colaboradores()]
    return render(request, "ventas/crud_lista.html", {
        "clave": "usuarios", "titulo": "Usuarios",
        "encabezados": ["Nombre", "Correo", "Clave"], "filas": filas,
    })


@solo_equipo
def usuarios_editar(request, pk=None):
    obj = get_object_or_404(_colaboradores(), pk=pk) if pk else None
    initial = {"nombre": obj.first_name, "correo": obj.email} if obj else None
    form = ColaboradorForm(request.POST or None, initial=initial, obj=obj)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if obj is None:
            obj = User(is_staff=True)
        obj.username = d["correo"]
        obj.email = d["correo"]
        obj.first_name = d["nombre"]
        if d["clave"]:
            obj.set_password(d["clave"])
        obj.save()
        messages.success(request, "Guardado correctamente.")
        return redirect("usuarios_lista")
    return render(request, "ventas/crud_form.html", {
        "form": form, "clave": "usuarios", "obj": obj, "titulo": "Usuarios",
    })


@solo_equipo
def usuarios_borrar(request, pk):
    if request.method == "POST":
        u = get_object_or_404(_colaboradores(), pk=pk)
        if u == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
        else:
            u.delete()
            messages.success(request, "Eliminado.")
    return redirect("usuarios_lista")