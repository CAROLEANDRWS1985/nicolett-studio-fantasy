from ventas.permisos import solo_equipo
from django import forms
from django.apps import apps
from django.contrib import messages
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404



def _buscar_modelo(palabra):
    for m in apps.get_app_config("ventas").get_models():
        if palabra in m.__name__.lower():
            return m


def _modelo(clave):
    palabras = {"servicios": "servicio", "citas": "cita",
                "clientes": "cliente", "productos": "producto",
                "inventario": "inventario"}
    M = _buscar_modelo(palabras[clave]) if clave in palabras else None
    if M is None:
        raise Http404("Modelo no encontrado")
    return M


def _form(M):
    Form = modelform_factory(M, fields="__all__")
    for f in Form.base_fields.values():
        if isinstance(f, forms.DateTimeField):
            f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
        elif isinstance(f, forms.DateField):
            f.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        elif isinstance(f, forms.TimeField):
            f.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    return Form


@solo_equipo
def crud_lista(request, clave):
    M = _modelo(clave)
    campos = [f for f in M._meta.fields if f.name != "id"]
    filas = [{"obj": o, "valores": [getattr(o, f.name) for f in campos]}
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
        get_object_or_404(M, pk=pk).delete()
        messages.success(request, "Eliminado.")
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