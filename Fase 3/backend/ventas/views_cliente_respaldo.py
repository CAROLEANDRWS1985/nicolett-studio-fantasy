from datetime import date, datetime, time
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import ServicioBelleza, Cliente
from .servicios_nicolett import SERVICIOS

CATEGORIAS = {nombre: cat for nombre, cat, _p, _n in SERVICIOS}

# ---- HORARIO DEL SALÓN (cámbialo aquí) ----
HORA_INICIO = 10   # primera cita a las 10:00
HORA_FIN = 19      # última cita termina a las 19:00
PASO = 60          # minutos entre una hora y la siguiente
# Domingo cerrado


def _modelo_cita():
    for m in apps.get_app_config("ventas").get_models():
        if "cita" in m.__name__.lower():
            return m


def _campos_cita(Cita):
    fs = [f for f in Cita._meta.fields if f.editable]
    rel = lambda M: next((f for f in fs if f.is_relation and f.related_model is M), None)
    return {
        "cli": rel(Cliente),
        "srv": rel(ServicioBelleza),
        "dt": next((f for f in fs if isinstance(f, models.DateTimeField)), None),
        "d": next((f for f in fs if type(f) is models.DateField), None),
        "t": next((f for f in fs if isinstance(f, models.TimeField)), None),
    }


def _cliente(u):
    if not u.email:
        return None
    c = Cliente.objects.filter(email__iexact=u.email).first()
    if c:
        return c
    try:
        return Cliente.objects.create(nombre=u.first_name or u.username, email=u.email)
    except Exception:
        return None


def _es_equipo(u):
    return u.is_staff or u.is_superuser


def _precio(p):
    return "$" + f"{int(p):,}".replace(",", ".")


def _slots():
    out, m = [], HORA_INICIO * 60
    while m < HORA_FIN * 60:
        out.append(f"{m // 60:02d}:{m % 60:02d}")
        m += PASO
    return out


def _ocupadas(Cita, c, fecha):
    ocupadas = set()
    if c["dt"]:
        for o in Cita.objects.filter(**{c["dt"].name + "__date": fecha}):
            v = getattr(o, c["dt"].name)
            if v and timezone.is_aware(v):
                v = timezone.localtime(v)
            if v:
                ocupadas.add(v.strftime("%H:%M"))
    elif c["d"] and c["t"]:
        for o in Cita.objects.filter(**{c["d"].name: fecha}):
            v = getattr(o, c["t"].name)
            if v:
                ocupadas.add(v.strftime("%H:%M"))
    return ocupadas


def _estado_horas(Cita, c, fecha):
    if fecha < date.today() or fecha.weekday() == 6:
        return []
    ocupadas = _ocupadas(Cita, c, fecha)
    ahora = datetime.now().strftime("%H:%M")
    res = []
    for h in _slots():
        pasada = fecha == date.today() and h <= ahora
        res.append({"hora": h, "libre": h not in ocupadas and not pasada})
    return res


@login_required(login_url="/")
def mi_cuenta(request):
    u = request.user

    # Las cuentas del equipo (dueña, administradora, trabajadoras) van al panel,
    # no a la pantalla de clientas.
    if _es_equipo(u):
        return redirect("/panel/gestionar/citas/")

    cliente = _cliente(u)
    Cita = _modelo_cita()
    c = _campos_cita(Cita) if Cita else None

    servicios = [{
        "pk": s.pk, "nombre": s.nombre, "descripcion": s.descripcion,
        "duracion": s.duracion_minutos, "precio": _precio(s.precio),
        "categoria": CATEGORIAS.get(s.nombre, "Otros"),
    } for s in ServicioBelleza.objects.filter(activo=True).order_by("nombre")]
    categorias = sorted({s["categoria"] for s in servicios})

    encabezados, filas, citas = [], [], []
    if Cita and c and c["cli"] and cliente:
        campos = [f for f in Cita._meta.fields if f.name not in ("id", c["cli"].name)]
        encabezados = [str(f.verbose_name).capitalize() for f in campos]
        for o in Cita.objects.filter(**{c["cli"].name: cliente}).order_by("-pk"):
            filas.append([getattr(o, f.name) for f in campos])
            citas.append({"pk": o.pk, "texto": str(o)})

    n = len(citas)
    niveles = [(0, "Clienta Bronce"), (3, "Clienta Plata"), (6, "Clienta Oro"), (10, "Clienta Platino")]
    nivel_i = max(i for i, (m, _) in enumerate(niveles) if n >= m)
    sig = niveles[nivel_i + 1] if nivel_i + 1 < len(niveles) else None
    faltan = (sig[0] - n) if sig else 0
    progreso = 100 if not sig else int(100 * (n - niveles[nivel_i][0]) / (sig[0] - niveles[nivel_i][0]))

    return render(request, "ventas/mi_cuenta.html", {
        "nombre": (u.first_name or (cliente.nombre if cliente else u.username)).split()[0],
        "servicios": servicios, "categorias": categorias,
        "encabezados": encabezados, "filas": filas, "citas": citas,
        "tiene_cliente": cliente is not None, "cliente": cliente,
        "nivel": niveles[nivel_i][1], "siguiente": sig[1] if sig else "",
        "faltan": faltan, "progreso": progreso, "n_citas": n,
    })


@login_required(login_url="/")
def horarios(request):
    Cita = _modelo_cita()
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        return JsonResponse({"slots": []})
    if not Cita:
        return JsonResponse({"slots": []})
    return JsonResponse({"slots": _estado_horas(Cita, _campos_cita(Cita), fecha)})


@login_required(login_url="/")
@require_POST
def agendar_cita(request):
    destino = "/mi-cuenta/#agendar"
    cliente = _cliente(request.user)
    Cita = _modelo_cita()
    c = _campos_cita(Cita) if Cita else None
    if not (cliente and c and c["cli"]):
        messages.error(request, "Tu usuario aún no está vinculado a una ficha de clienta.")
        return redirect(destino)
    if not c["srv"] or not (c["dt"] or (c["d"] and c["t"])):
        messages.error(request, "El modelo Cita no tiene campos de servicio y fecha/hora que pueda usar.")
        return redirect(destino)

    servicio = get_object_or_404(ServicioBelleza, pk=request.POST.get("servicio"), activo=True)
    try:
        fecha = date.fromisoformat(request.POST.get("fecha", ""))
        h, m = request.POST.get("hora", "").split(":")
        hora = time(int(h), int(m))
    except ValueError:
        messages.error(request, "Elige un día y una hora.")
        return redirect(destino)

    libres = {x["hora"] for x in _estado_horas(Cita, c, fecha) if x["libre"]}
    if hora.strftime("%H:%M") not in libres:
        messages.error(request, "Esa hora ya no está disponible. Elige otra.")
        return redirect(destino)

    datos = {c["cli"].name: cliente, c["srv"].name: servicio}
    if c["dt"]:
        v = datetime.combine(fecha, hora)
        datos[c["dt"].name] = timezone.make_aware(v) if settings.USE_TZ else v
    else:
        datos[c["d"].name] = fecha
        datos[c["t"].name] = hora
    try:
        Cita.objects.create(**datos)
    except Exception as e:
        messages.error(request, f"No se pudo agendar: {e}")
        return redirect(destino)
    messages.success(request, f"¡Listo! Tu cita quedó para el {fecha:%d-%m-%Y} a las {hora:%H:%M}.")
    return redirect("/mi-cuenta/#historial")


@login_required(login_url="/")
@require_POST
def cancelar_cita(request, pk):
    cliente = _cliente(request.user)
    Cita = _modelo_cita()
    c = _campos_cita(Cita) if Cita else None
    if cliente and c and c["cli"]:
        get_object_or_404(Cita, pk=pk, **{c["cli"].name: cliente}).delete()
        messages.success(request, "Tu cita fue cancelada.")
    return redirect("/mi-cuenta/#cancelar")


@login_required(login_url="/")
@require_POST
def editar_perfil(request):
    cliente = _cliente(request.user)
    if cliente:
        cliente.nombre = request.POST.get("nombre", cliente.nombre).strip() or cliente.nombre
        cliente.telefono = request.POST.get("telefono", cliente.telefono).strip()
        cliente.save()
        messages.success(request, "Perfil actualizado.")
    return redirect("/mi-cuenta/#perfil")