from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from ventas.permisos import solo_equipo

User = get_user_model()
GRUPO = "Colaboradoras"


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
        correo = self.cleaned_data["correo"].strip().lower()
        # NUEVO: revisa el correo tanto en el usuario como en el campo correo
        otros = User.objects.filter(Q(username__iexact=correo) | Q(email__iexact=correo))
        if self.obj:
            otros = otros.exclude(pk=self.obj.pk)
        if otros.exists():
            raise forms.ValidationError("Ya existe una persona con ese correo.")
        return correo

    def clean_nombre(self):
        # NUEVO: avisa si ya hay alguien del equipo con el mismo nombre
        nombre = self.cleaned_data["nombre"].strip()
        otros = _equipo().filter(first_name__iexact=nombre)
        if self.obj:
            otros = otros.exclude(pk=self.obj.pk)
        if otros.exists():
            raise forms.ValidationError(
                "Ya existe alguien del equipo con ese nombre. Edítala en vez de crear otra.")
        return nombre


def _equipo():
    """NUEVO: todo el equipo (dueña incluida), para que nadie quede fuera de la lista."""
    return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).order_by("first_name", "username")


def _colaboradores():
    """Cuentas que se pueden editar o borrar desde aquí (la dueña no)."""
    return User.objects.filter(is_staff=True, is_superuser=False)


def _tipo(u):
    if u.is_superuser:
        return "Dueña"
    if u.groups.filter(name=GRUPO).exists():
        return "Colaboradora"
    return "Administración"


@solo_equipo
def usuarios_lista(request):
    # Buscador por nombre o por la parte del correo antes del @
    q = ""
    for nombre_param in ("q", "buscar", "busqueda", "search"):
        if request.GET.get(nombre_param):
            q = request.GET[nombre_param].strip()
            break
    gente = list(_equipo())
    if q:
        t = q.lower()
        # Si el nombre coincide exacto (ej. "Nicole"), muestra solo esa persona
        exactos = [u for u in gente if (u.first_name or "").lower() == t]
        if exactos:
            gente = exactos
        else:
            gente = [u for u in gente
                     if t in (u.first_name or "").lower()
                     or t in (u.last_name or "").lower()
                     or t in (u.email or u.username).split("@")[0].lower()]

    filas = [{"obj": u, "valores": [u.first_name or u.username, u.email or u.username, _tipo(u)]}
             for u in gente]
    return render(request, "ventas/crud_lista.html", {
        "clave": "usuarios", "titulo": "Colaboradores del salón",
        "encabezados": ["Nombre", "Correo", "Tipo"], "filas": filas,
        "q": q, "busqueda": q,
    })


@solo_equipo
def usuarios_editar(request, pk=None):
    # La dueña también se puede editar (nombre, correo, clave), pero no borrar
    obj = get_object_or_404(_equipo(), pk=pk) if pk else None
    initial = {"nombre": obj.first_name, "correo": obj.email or obj.username} if obj else None
    form = ColaboradorForm(request.POST or None, initial=initial, obj=obj)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        nueva = obj is None
        if nueva:
            obj = User(is_staff=True)
        obj.username = d["correo"]
        obj.email = d["correo"]
        obj.first_name = d["nombre"]
        if d["clave"]:
            obj.set_password(d["clave"])
        obj.save()
        if nueva:
            # NUEVO: quien se crea aquí queda como colaboradora (solo ve su agenda)
            grupo, _ = Group.objects.get_or_create(name=GRUPO)
            obj.groups.add(grupo)
        messages.success(request, "Guardado correctamente.")
        return redirect("usuarios_lista")
    return render(request, "ventas/crud_form.html", {
        "form": form, "clave": "usuarios", "obj": obj, "titulo": "Colaboradores del salón",
    })


@solo_equipo
def usuarios_borrar(request, pk):
    if request.method == "POST":
        u = get_object_or_404(_equipo(), pk=pk)
        if u == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
        elif u.is_superuser:
            messages.error(request, "La cuenta de la dueña no se puede eliminar.")
        else:
            u.delete()
            messages.success(request, "Eliminado.")
    return redirect("usuarios_lista")