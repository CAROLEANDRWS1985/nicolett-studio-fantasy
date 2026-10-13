from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Producto, Cita, Inventario
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import ServicioBelleza
from .forms import ServicioForm
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Cliente, Cita
from .forms import ClienteForm, CitaForm
from django.apps import apps
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404


def _modelo_servicio():
    for m in apps.get_app_config("ventas").get_models():
        if any(f.name == "precio" for f in m._meta.get_fields()):
            return m


def precios_promos(request):
    Servicio = _modelo_servicio()

    if request.method == "POST":
        s = get_object_or_404(Servicio, pk=request.POST["servicio_id"])
        s.precio = int(request.POST.get("precio") or 0)
        s.save()
        messages.success(request, f"Precio de {s} actualizado.")
        return redirect(request.path)

    return render(request, "ventas/precios_promos.html",
                  {"servicios": Servicio.objects.all()})
@login_required(login_url='login')
def panel_duena(request):
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para ver esta página')
        return redirect('home')

    productos = Producto.objects.all()
    citas = Cita.objects.all().order_by('fecha', 'hora')
    inventario = Inventario.objects.select_related('producto').all()

    return render(request, 'panel_duena.html', {
        'productos': productos,
        'citas': citas,
        'inventario': inventario,
    })
class ServicioList(LoginRequiredMixin, ListView):
    model = ServicioBelleza
    template_name = "ventas/servicios.html"


class ServicioCreate(LoginRequiredMixin, CreateView):
    model = ServicioBelleza
    form_class = ServicioForm
    template_name = "ventas/servicio_form.html"
    success_url = reverse_lazy("servicios_lista")


class ServicioUpdate(LoginRequiredMixin, UpdateView):
    model = ServicioBelleza
    form_class = ServicioForm
    template_name = "ventas/servicio_form.html"
    success_url = reverse_lazy("servicios_lista")


class ServicioDelete(LoginRequiredMixin, DeleteView):
    model = ServicioBelleza
    template_name = "ventas/servicio_confirmar_borrar.html"
    success_url = reverse_lazy("servicios_lista")

    # ---------- PRECIOS (solo precios de servicios) ----------
@login_required
def precios(request):
    if request.method == "POST":
        servicio = get_object_or_404(ServicioBelleza, pk=request.POST.get("servicio_id"))
        try:
            precio = Decimal(request.POST.get("precio", ""))
            if precio < 0:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, "Precio no válido.")
        else:
            servicio.precio = precio
            servicio.save(update_fields=["precio"])
            messages.success(request, f"Precio de {servicio.nombre} actualizado.")
        return redirect("admin_precios_promos")

    servicios = ServicioBelleza.objects.order_by("nombre")
    return render(request, "ventas/precios_promos.html", {"servicios": servicios})


# ---------- USUARIOS (clientas) ----------
class ClienteList(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "ventas/usuarios.html"
    ordering = ["nombre"]


class ClienteCreate(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "ventas/form_generico.html"
    success_url = reverse_lazy("admin_usuarios")
    extra_context = {"titulo": "Nueva clienta", "volver": reverse_lazy("admin_usuarios")}


class ClienteUpdate(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "ventas/form_generico.html"
    success_url = reverse_lazy("admin_usuarios")
    extra_context = {"titulo": "Editar clienta", "volver": reverse_lazy("admin_usuarios")}


class ClienteDelete(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = "ventas/confirmar_borrar.html"
    success_url = reverse_lazy("admin_usuarios")
    extra_context = {"volver": reverse_lazy("admin_usuarios")}


# ---------- CITAS ----------
class CitaHoyList(LoginRequiredMixin, ListView):
    model = Cita
    template_name = "ventas/citas_hoy.html"

    def get_queryset(self):
        return (Cita.objects.filter(fecha=timezone.localdate())
                .select_related("cliente", "servicio").order_by("hora"))


class CitaCreate(LoginRequiredMixin, CreateView):
    model = Cita
    form_class = CitaForm
    template_name = "ventas/form_generico.html"
    success_url = reverse_lazy("admin_citas_hoy")
    extra_context = {"titulo": "Nueva cita", "volver": reverse_lazy("admin_citas_hoy")}


class CitaUpdate(LoginRequiredMixin, UpdateView):
    model = Cita
    form_class = CitaForm
    template_name = "ventas/form_generico.html"
    success_url = reverse_lazy("admin_citas_hoy")
    extra_context = {"titulo": "Editar cita", "volver": reverse_lazy("admin_citas_hoy")}


class CitaDelete(LoginRequiredMixin, DeleteView):
    model = Cita
    template_name = "ventas/confirmar_borrar.html"
    success_url = reverse_lazy("admin_citas_hoy")
    extra_context = {"volver": reverse_lazy("admin_citas_hoy")}
    from django import forms
from django.forms import modelform_factory


def _buscar_modelo(*palabras):
    for m in apps.get_app_config("ventas").get_models():
        if any(p in m.__name__.lower() for p in palabras):
            return m


def _modelo(clave):
    if clave == "servicios":
        M = _modelo_servicio()
    elif clave == "citas":
        M = _buscar_modelo("cita", "agend", "reserva")
    elif clave == "productos":
        M = _buscar_modelo("producto")
    else:
        M = None
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


def crud_lista(request, clave):
    M = _modelo(clave)
    campos = [f for f in M._meta.fields if f.name != "id"]
    filas = [{"obj": o, "valores": [getattr(o, f.name) for f in campos]}
             for o in M.objects.all()]
    return render(request, "ventas/crud_lista.html", {
        "clave": clave, "titulo": clave.capitalize(),
        "encabezados": [f.verbose_name.capitalize() for f in campos],
        "filas": filas,
    })


def crud_editar(request, clave, pk=None):
    M = _modelo(clave)
    obj = get_object_or_404(M, pk=pk) if pk else None
    form = _form(M)(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Guardado correctamente.")
        return redirect("crud_lista", clave=clave)
    return render(request, "ventas/crud_form.html",
                  {"form": form, "clave": clave, "obj": obj, "titulo": clave.capitalize()})


def crud_borrar(request, clave, pk):
    M = _modelo(clave)
    if request.method == "POST":
        get_object_or_404(M, pk=pk).delete()
        messages.success(request, "Eliminado.")
    return redirect("crud_lista", clave=clave)
def _modelo_servicio():
    candidatos = [m for m in apps.get_app_config("ventas").get_models()
                  if any(f.name == "precio" for f in m._meta.get_fields())]
    for m in candidatos:
        if "servic" in m.__name__.lower():
            return m
    return candidatos[0] if candidatos else None


def _buscar_modelo(*palabras):
    for m in apps.get_app_config("ventas").get_models():
        if any(p in m.__name__.lower() for p in palabras):
            return m


def _modelo(clave):
    if clave == "servicios":
        M = _modelo_servicio()
    elif clave == "citas":
        M = _buscar_modelo("cita", "agend", "reserva")
    else:
        M = None
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


@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
def crud_borrar(request, clave, pk):
    M = _modelo(clave)
    if request.method == "POST":
        get_object_or_404(M, pk=pk).delete()
        messages.success(request, "Eliminado.")
    return redirect("crud_lista", clave=clave)