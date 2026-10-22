from django.contrib.auth import get_user_model
User = get_user_model()
from ventas.permisos import solo_equipo
from django import forms
from django.apps import apps
from django.contrib import messages
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404


# Columnas que NO se muestran en la lista de cada modelo
OCULTAR_COLUMNAS = {
    "Cliente": {"comuna"},
    "Atencion": {"creado"},
}


def _nombre_usuario(u):
    """Nombre de la persona (no el correo). Si no tiene nombre guardado, usa su usuario."""
    return u.get_full_name() or u.username


def _buscar_modelo(palabra):
    for m in apps.get_app_config("ventas").get_models():
        if palabra in m.__name__.lower():
            return m


def _modelo(clave):
    palabras = {"servicios": "servicio", "citas": "cita",
                "clientes": "cliente", "productos": "producto",
                "inventario": "inventario", "atenciones": "atencion",
                "proveedores": "proveedor",
                "compras": "compraproveedor"}
    M = _buscar_modelo(palabras[clave]) if clave in palabras else None
    if M is None:
        raise Http404("Modelo no encontrado")
    return M


def _form(M):
    Form = modelform_factory(M, fields="__all__")
    # La cuenta de la clienta se vincula sola por correo: no se muestra en el formulario
    if "usuario" in Form.base_fields:
        del Form.base_fields["usuario"]
    # La comuna ya no se pide en la ficha de la clienta
    if M.__name__ == "Cliente" and "comuna" in Form.base_fields:
        del Form.base_fields["comuna"]
    # Colaborador: solo los profesionales del salón
    if "profesional" in Form.base_fields:
        campo = Form.base_fields["profesional"]
        campo.queryset = User.objects.filter(is_staff=True, is_superuser=False).order_by("first_name")
        campo.label = "Colaborador"
        campo.label_from_instance = lambda u: _nombre_usuario(u)
    for f in Form.base_fields.values():
        if isinstance(f, forms.DateTimeField):
            f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
        elif isinstance(f, forms.DateField):
            f.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        elif isinstance(f, forms.TimeField):
            f.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    return Form


def _valor(o, f):
    """Lo que se muestra en cada celda de la lista."""
    v = getattr(o, f.name)
    if v is None:
        return None
    if f.name == "profesional":
        return _nombre_usuario(v)
    if f.choices:
        return getattr(o, f"get_{f.name}_display")()
    if f.name in ("monto_cobrado", "monto"):
        return "$" + f"{int(v):,}".replace(",", ".")
    if isinstance(v, bool):
        return "Sí" if v else "No"
    return v


@solo_equipo
def crud_lista(request, clave):
    M = _modelo(clave)
    ocultas = OCULTAR_COLUMNAS.get(M.__name__, set())
    campos = [f for f in M._meta.fields if f.name != "id" and f.name not in ocultas]
    filas = [{"obj": o, "valores": [_valor(o, f) for f in campos]}
             for o in M.objects.all()]
    return render(request, "ventas/crud_lista.html", {
        "clave": clave,
        "titulo": clave.capitalize(),
        "encabezados": [str(f.verbose_name).capitalize() for f in campos],
        "filas": filas,
    })


@solo_equipo
def crud_editar(request, clave, pk=None):
    M = _modelo(clave)
    obj = get_object_or_404(M, pk=pk) if pk else None
    form = _form(M)(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Guardado correctamente.")
        return redirect("crud_lista", clave=clave)
    return render(request, "ventas/crud_form.html", {
        "form": form, "clave": clave, "obj": obj, "titulo": clave.capitalize(),
    })


@solo_equipo
def crud_borrar(request, clave, pk):
    M = _modelo(clave)
    if request.method == "POST":
        try:
            get_object_or_404(M, pk=pk).delete()
            messages.success(request, "Eliminado.")
        except Exception:
            messages.error(request, "No se puede eliminar: tiene registros asociados. "
                                    "Puedes marcarlo como no activo.")
    return redirect("crud_lista", clave=clave)
from .models import ServicioBelleza


@solo_equipo
def precios(request):
    if request.method == "POST":
        s = get_object_or_404(ServicioBelleza, pk=request.POST["servicio_id"])
        s.precio = int(request.POST.get("precio") or 0)
        s.save()
        messages.success(request, f"Precio de {s.nombre} actualizado.")
        return redirect(request.path)
    return render(request, "ventas/precios_promos.html",
                  {"servicios": ServicioBelleza.objects.order_by("nombre")})