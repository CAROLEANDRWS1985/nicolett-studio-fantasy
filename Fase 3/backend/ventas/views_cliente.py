import html
import re
import time as _time
from datetime import date, datetime, time
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ServicioBelleza, Cliente, Cita as CitaModel, Abono
from .servicios_nicolett import SERVICIOS

CATEGORIAS = {nombre: cat for nombre, cat, _p, _n in SERVICIOS}

# Orden en que aparecen los botones de categorías
ORDEN_CATEGORIAS = [
    "cabello", "depilación femenina", "pestañas y cejas",
    "podología", "tratamientos", "uñas", "depilación masculina",
]


def _categoria(nombre):
    cat = CATEGORIAS.get(nombre, "Otros")
    if cat.lower().startswith("depilaci"):
        return "Depilación masculina" if nombre.lower().startswith("hombre") else "Depilación femenina"
    return cat


def _orden_categoria(cat):
    c = cat.lower()
    return (ORDEN_CATEGORIAS.index(c) if c in ORDEN_CATEGORIAS else 99, c)


# ---- HORARIO DEL SALÓN (cámbialo aquí) ----
HORA_INICIO = 10   # primera cita a las 10:00
HORA_FIN = 19      # última cita termina a las 19:00
PASO = 60          # minutos entre una hora y la siguiente
# Domingo cerrado

# ---- ABONO (cámbialo aquí) ----
ABONO_BASE = 5000                 # abono para todos los servicios
ABONOS = {"corte de pelo": 5000}  # abonos distintos: parte del nombre en minúscula: monto


def _abono(servicio):
    nombre = servicio.nombre.lower()
    monto = ABONO_BASE
    for k, v in ABONOS.items():
        if k in nombre:
            monto = v
            break
    if servicio.precio and int(servicio.precio) > 0:
        monto = min(monto, int(servicio.precio))   # el abono nunca supera el precio
    return int(monto)


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
    if u.email:
        return Cliente.objects.filter(email__iexact=u.email).first()


def _es_equipo(u):
    return u.is_staff or u.is_superuser


def _precio(p):
    return "$" + f"{int(p):,}".replace(",", ".")


def _avisar_duena(asunto, mensaje):
    """Manda un correo a la dueña. Si falla, no impide agendar ni cancelar."""
    try:
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL,
                  [settings.EMAIL_DUENA], fail_silently=False)
    except Exception as e:
        print("No se pudo enviar el correo a la dueña:", e)


def _slots():
    out, m = [], HORA_INICIO * 60
    while m < HORA_FIN * 60:
        out.append(f"{m // 60:02d}:{m % 60:02d}")
        m += PASO
    return out


def _ocupadas(Cita, c, fecha):
    ocupadas = set()
    # Las citas canceladas dejan la hora libre
    if c["dt"]:
        for o in Cita.objects.filter(**{c["dt"].name + "__date": fecha}).exclude(estado="cancelada"):
            v = getattr(o, c["dt"].name)
            if v and timezone.is_aware(v):
                v = timezone.localtime(v)
            if v:
                ocupadas.add(v.strftime("%H:%M"))
    elif c["d"] and c["t"]:
        for o in Cita.objects.filter(**{c["d"].name: fecha}).exclude(estado="cancelada"):
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
        "categoria": _categoria(s.nombre),
    } for s in ServicioBelleza.objects.filter(activo=True).order_by("nombre")]
    categorias = sorted({s["categoria"] for s in servicios}, key=_orden_categoria)

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
        cita = Cita.objects.create(**datos)   # queda "pendiente" hasta pagar el abono
    except Exception as e:
        messages.error(request, f"No se pudo agendar: {e}")
        return redirect(destino)

    # Ahora la clienta paga el abono con Webpay
    return redirect("pagar_abono", pk=cita.pk)


@login_required(login_url="/")
@require_POST
def cancelar_cita(request, pk):
    cliente = _cliente(request.user)
    Cita = _modelo_cita()
    c = _campos_cita(Cita) if Cita else None
    if cliente and c and c["cli"]:
        cita = get_object_or_404(Cita, pk=pk, **{c["cli"].name: cliente})
        detalle = str(cita)
        cita.delete()
        # Aviso por correo a la dueña
        _avisar_duena("Cita cancelada", f"{cliente.nombre} canceló su cita: {detalle}")
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


# =====================================================================
#  PAGO DEL ABONO CON WEBPAY PLUS (ambiente de PRUEBAS de Transbank)
#  Para pasar a producción: cambia _webpay() con el código de comercio
#  y la clave que entregue Transbank, y usa IntegrationType.LIVE.
# =====================================================================
def _webpay():
    from transbank.webpay.webpay_plus.transaction import Transaction
    from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
    from transbank.common.integration_api_keys import IntegrationApiKeys
    try:
        from transbank.common.options import WebpayOptions
        from transbank.common.integration_type import IntegrationType
        return Transaction(WebpayOptions(
            IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    except ImportError:
        return Transaction.build_for_integration(
            IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY)


def _r(resp, clave):
    """Lee un dato de la respuesta de Transbank (sirve si viene como dict u objeto)."""
    return resp[clave] if isinstance(resp, dict) else getattr(resp, clave)


def _liberar(cita):
    """Si la cita sigue sin pagar, se borra para que la hora quede libre."""
    if cita is not None and cita.estado == "pendiente":
        cita.delete()


def _cita_de_orden(orden):
    m = re.match(r"^C(\d+)-", orden or "")
    return CitaModel.objects.filter(pk=int(m.group(1))).first() if m else None


@login_required(login_url="/")
def pagar_abono(request, pk):
    cliente = _cliente(request.user)
    if not cliente:
        return redirect("/mi-cuenta/")
    cita = get_object_or_404(CitaModel, pk=pk, cliente=cliente, estado="pendiente")
    monto = _abono(cita.servicio) if cita.servicio else ABONO_BASE
    orden = f"C{cita.pk}-{int(_time.time())}"     # máx. 26 caracteres

    try:
        resp = _webpay().create(
            orden, f"U{request.user.pk}", monto,
            request.build_absolute_uri(reverse("webpay_retorno")))
        url, token = _r(resp, "url"), _r(resp, "token")
    except Exception as e:
        _liberar(cita)
        messages.error(request, f"No se pudo conectar con Webpay: {e}")
        return redirect("/mi-cuenta/#agendar")

    # Webpay pide enviar el token con un formulario: se envía solo
    return HttpResponse(
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Webpay</title></head>'
        '<body style="background:#121010;color:#D4B26A;font-family:sans-serif;text-align:center;padding-top:20vh">'
        f'<p>Te llevamos a Webpay para pagar tu abono de {_precio(monto)}...</p>'
        f'<form id="f" method="post" action="{html.escape(url)}">'
        f'<input type="hidden" name="token_ws" value="{html.escape(token)}">'
        '<noscript><button type="submit">Ir a pagar</button></noscript></form>'
        '<script>document.getElementById("f").submit()</script></body></html>')


@csrf_exempt   # Transbank devuelve a la clienta con un POST desde otro sitio
def webpay_retorno(request):
    datos = request.POST if request.method == "POST" else request.GET
    token = datos.get("token_ws")

    # Sin token_ws: la clienta apretó "anular" en Webpay o se acabó el tiempo
    if not token:
        _liberar(_cita_de_orden(datos.get("TBK_ORDEN_COMPRA", "")))
        messages.error(request, "El pago fue anulado. Tu hora quedó libre, puedes intentar de nuevo.")
        return redirect("/mi-cuenta/#agendar")

    try:
        resp = _webpay().commit(token)
    except Exception:
        messages.error(request, "No pudimos confirmar el pago. Revisa tu historial.")
        return redirect("/mi-cuenta/#historial")

    orden = _r(resp, "buy_order")
    cita = _cita_de_orden(orden)
    aprobado = _r(resp, "status") == "AUTHORIZED" and _r(resp, "response_code") == 0

    if aprobado and cita:
        monto = int(_r(resp, "amount"))
        cita.estado = "confirmada"
        cita.save(update_fields=["estado"])
        Abono.objects.create(
            cliente=cita.cliente, monto=monto,
            motivo=f"Abono Webpay - cita #{cita.pk} - orden {orden}")
        _avisar_duena(
            "Cita confirmada con abono",
            f"{cita.cliente.nombre} pagó su abono de {_precio(monto)} por Webpay. Cita: {cita}.")
        messages.success(request, f"¡Pago recibido! Tu cita quedó confirmada. Abono pagado: {_precio(monto)}.")
        return redirect("/mi-cuenta/#historial")

    _liberar(cita)
    messages.error(request, "El pago no fue aprobado. Tu hora quedó libre, puedes intentar con otra tarjeta.")
    return redirect("/mi-cuenta/#agendar")