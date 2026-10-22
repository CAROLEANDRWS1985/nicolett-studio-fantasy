import html
import io
import os
import re
import time as _time
from datetime import date, datetime, time
from urllib.parse import quote
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ServicioBelleza, Cliente, Cita as CitaModel, Abono, DiaBloqueado
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
ABONO_TRATAMIENTOS = 10000   # solo tratamientos capilares
ABONO_OTROS = 5000           # todos los demás servicios, incluidos los cortes de cabello
ABONO_BASE = ABONO_OTROS
CATEGORIAS_TRATAMIENTOS = ("tratamientos",)


def _abono(servicio):
    if _categoria(servicio.nombre).lower() in CATEGORIAS_TRATAMIENTOS:
        monto = ABONO_TRATAMIENTOS
    else:
        monto = ABONO_OTROS
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
    if _es_equipo(u):
        return None
    cliente = Cliente.objects.filter(usuario=u).first()
    if cliente is None and u.email:
        cliente = Cliente.objects.filter(email__iexact=u.email).first()
    if cliente is None:
        cliente = Cliente.objects.create(
            usuario=u, nombre=u.get_full_name() or u.username, email=u.email or None)
    elif cliente.usuario_id is None:
        cliente.usuario = u
        cliente.save(update_fields=["usuario"])
    return cliente

def _es_equipo(u):
    return u.is_staff or u.is_superuser


def _precio(p):
    return "$" + f"{int(p):,}".replace(",", ".")


# ---- Fechas en español para los correos ----
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _fecha_larga(f):
    """Ej: lunes 26 de octubre de 2026"""
    return f"{DIAS[f.weekday()]} {f.day} de {MESES[f.month - 1]} de {f.year}"


def _fecha_hora_obj(cita):
    """Devuelve (fecha, hora) de la cita como objetos date y time. Si falla, (None, None)."""
    try:
        c = _campos_cita(CitaModel)
        if c["dt"]:
            v = getattr(cita, c["dt"].name)
            if v and timezone.is_aware(v):
                v = timezone.localtime(v)
            return v.date(), v.time()
        if c["d"] and c["t"]:
            return getattr(cita, c["d"].name), getattr(cita, c["t"].name)
    except Exception:
        pass
    return None, None


def _avisar_duena(asunto, mensaje, mensaje_html=None):
    """Manda un correo a la dueña. Si falla, no impide agendar ni cancelar."""
    try:
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL,
                  [settings.EMAIL_DUENA], fail_silently=False,
                  html_message=mensaje_html)
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


def _fecha_hora_cita(cita):
    """Devuelve (fecha, hora) de la cita como texto, ej: ('26-10-2026', '15:00')."""
    try:
        c = _campos_cita(CitaModel)
        if c["dt"]:
            v = getattr(cita, c["dt"].name)
            if v and timezone.is_aware(v):
                v = timezone.localtime(v)
            return v.strftime("%d-%m-%Y"), v.strftime("%H:%M")
        if c["d"] and c["t"]:
            f = getattr(cita, c["d"].name)
            h = getattr(cita, c["t"].name)
            return f.strftime("%d-%m-%Y"), h.strftime("%H:%M")
    except Exception:
        pass
    return "-", "-"


@login_required(login_url="/")
def mi_cuenta(request):
    u = request.user

    # Si quedó una sesión del equipo abierta, se cierra: el portal es solo para clientas.
    if _es_equipo(u):
        logout(request)
        return redirect("/")

    # Reservar desde la web: solo entra quien acaba de iniciar sesión (vale una sola vez).
    entro_recien = request.session.pop("puede_abrir", False)
    if request.GET.get("abrir") and not entro_recien:
        destino_login = "/segur/login/?next=" + quote(request.get_full_path())
        logout(request)
        return redirect(destino_login)

    cliente = _cliente(u)
    Cita = _modelo_cita()
    c = _campos_cita(Cita) if Cita else None

    servicios = [{
        "pk": s.pk, "nombre": s.nombre, "descripcion": s.descripcion,
        "duracion": s.duracion_minutos, "precio": _precio(s.precio),
        "categoria": _categoria(s.nombre), "abono": _abono(s),
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

        # Se guardan los datos ANTES de borrar la cita
        try:
            servicio = cita.servicio.nombre if cita.servicio else "No especificado"
        except Exception:
            servicio = "No especificado"
        try:
            estado = cita.get_estado_display()
        except Exception:
            estado = "-"
        fecha, hora = _fecha_hora_obj(cita)

        cita.delete()

        # ---- Correo completo para la dueña ----
        if fecha and hora:
            fecha_txt = _fecha_larga(fecha)
            hora_txt = hora.strftime("%H:%M") + " hrs"
            asunto = (f"Cita cancelada: {cliente.nombre}, "
                      f"{fecha.day} de {MESES[fecha.month - 1]} a las {hora.strftime('%H:%M')}")
        else:
            fecha_txt = hora_txt = "-"
            asunto = f"Cita cancelada: {cliente.nombre}"

        cancelada_el = timezone.localtime().strftime("%d-%m-%Y %H:%M")
        telefono = cliente.telefono or "No registrado"
        correo = cliente.email or "No registrado"

        texto = (
            "Hola Nicolett,\n\n"
            f"{cliente.nombre} ha cancelado su cita.\n\n"
            "DETALLE DE LA CITA CANCELADA\n"
            "----------------------------\n"
            f"Clienta:  {cliente.nombre}\n"
            f"Servicio: {servicio}\n"
            f"Fecha:    {fecha_txt}\n"
            f"Hora:     {hora_txt}\n"
            f"Estado de la cita: {estado}\n"
            f"Cancelada el: {cancelada_el}\n\n"
            "CONTACTO DE LA CLIENTA\n"
            "----------------------\n"
            f"Teléfono: {telefono}\n"
            f"Correo:   {correo}\n\n"
            "Ese horario ya quedó libre en tu agenda.\n\n"
            "Nicolett Studio"
        )

        e = html.escape
        filas = [
            ("Clienta", cliente.nombre), ("Servicio", servicio),
            ("Fecha", fecha_txt), ("Hora", hora_txt),
            ("Estado de la cita", estado), ("Cancelada el", cancelada_el),
        ]
        filas_html = "".join(
            f'<tr><td style="padding:8px 12px;color:#6E655C;border-bottom:1px solid #E4DCD1;">{e(k)}</td>'
            f'<td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #E4DCD1;">{e(str(v))}</td></tr>'
            for k, v in filas
        )
        cuerpo_html = (
            '<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#231F1B;">'
            '<h2 style="margin:0 0 8px;">Cita cancelada</h2>'
            f'<p>Hola Nicolett, <b>{e(cliente.nombre)}</b> ha cancelado su cita.</p>'
            '<h3 style="margin:24px 0 8px;font-size:15px;">Detalle de la cita cancelada</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#F7F2EC;">{filas_html}</table>'
            '<h3 style="margin:24px 0 8px;font-size:15px;">Contacto de la clienta</h3>'
            f'<p style="margin:0;">Teléfono: {e(telefono)}<br>Correo: {e(correo)}</p>'
            '<p style="margin-top:24px;">Ese horario ya quedó libre en tu agenda.</p>'
            '<p style="color:#6E655C;">Nicolett Studio</p></div>'
        )

        _avisar_duena(asunto, texto, cuerpo_html)

        # ---- Correo de cancelación para la clienta ----
        # Se usa el correo de su cuenta o el de su ficha, nunca el de la dueña.
        try:
            duena = (getattr(settings, "EMAIL_DUENA", "") or "").strip().lower()
            usuario = getattr(cliente, "usuario", None)
            candidatos = [
                (getattr(usuario, "email", "") or "").strip(),
                (getattr(cliente, "email", "") or "").strip(),
            ]
            correo_clienta = next((x for x in candidatos if x and x.lower() != duena), "")
            if correo_clienta:
                texto_clienta = (
                    f"Hola {cliente.nombre},\n\n"
                    "Tu cita fue cancelada.\n\n"
                    "DETALLE DE LA CITA CANCELADA\n"
                    "----------------------------\n"
                    f"Servicio: {servicio}\n"
                    f"Fecha:    {fecha_txt}\n"
                    f"Hora:     {hora_txt}\n\n"
                    "Nicolett Studio"
                )
                filas_cli = [("Servicio", servicio), ("Fecha", fecha_txt), ("Hora", hora_txt)]
                filas_cli_html = "".join(
                    f'<tr><td style="padding:8px 12px;color:#6E655C;border-bottom:1px solid #E4DCD1;">{e(k)}</td>'
                    f'<td style="padding:8px 12px;font-weight:600;border-bottom:1px solid #E4DCD1;">{e(str(v))}</td></tr>'
                    for k, v in filas_cli
                )
                html_clienta = (
                    '<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#231F1B;">'
                    '<h2 style="margin:0 0 8px;">Tu cita fue cancelada</h2>'
                    f'<p>Hola <b>{e(cliente.nombre)}</b>, tu cita fue cancelada.</p>'
                    '<h3 style="margin:24px 0 8px;font-size:15px;">Detalle de la cita cancelada</h3>'
                    f'<table style="width:100%;border-collapse:collapse;background:#F7F2EC;">{filas_cli_html}</table>'
                    '<p style="color:#6E655C;margin-top:24px;">Nicolett Studio</p></div>'
                )
                send_mail("Tu cita fue cancelada - Nicolett Studio", texto_clienta,
                          settings.DEFAULT_FROM_EMAIL, [correo_clienta],
                          fail_silently=False, html_message=html_clienta)
            else:
                print("La clienta no tiene un correo propio distinto al de la dueña; "
                      "no se envió su aviso de cancelación.")
        except Exception as err:
            print("No se pudo enviar el correo de cancelación a la clienta:", err)

        primer_nombre = (cliente.nombre or "").split()[0] if (cliente.nombre or "").strip() else ""
        messages.success(
            request,
            f"Hola {primer_nombre}, tu cita fue cancelada. "
            "Para volver a reagendar, utiliza la página web o escríbenos por WhatsApp. "
            "Te estaremos esperando pronto.")
    return redirect("/mi-cuenta/#cancelar")


@login_required(login_url="/")
@require_POST
def editar_perfil(request):
    cliente = _cliente(request.user)
    if cliente:
        # Cumpleaños (opcional): se valida antes de guardar nada
        nacimiento = None
        texto = request.POST.get("fecha_nacimiento", "").strip()
        if texto:
            try:
                nacimiento = date.fromisoformat(texto)
            except ValueError:
                messages.error(request, "La fecha de cumpleaños no es válida.")
                return redirect("/mi-cuenta/#perfil")
            if nacimiento > date.today():
                messages.error(request, "La fecha de cumpleaños no puede ser futura.")
                return redirect("/mi-cuenta/#perfil")

        # Correo (opcional): también se valida antes de guardar nada
        correo = (request.POST.get("email") or request.POST.get("correo") or "").strip().lower()
        if correo:
            try:
                validate_email(correo)
            except ValidationError:
                messages.error(request, "El correo no es válido.")
                return redirect("/mi-cuenta/#perfil")
            User = get_user_model()
            en_uso = (
                User.objects.filter(email__iexact=correo).exclude(pk=request.user.pk).exists()
                or Cliente.objects.filter(email__iexact=correo).exclude(pk=cliente.pk).exists()
            )
            if en_uso:
                messages.error(request, "Ese correo ya está en uso por otra cuenta.")
                return redirect("/mi-cuenta/#perfil")

        cliente.nombre = request.POST.get("nombre", cliente.nombre).strip() or cliente.nombre
        cliente.telefono = request.POST.get("telefono", cliente.telefono or "").strip()
        cliente.fecha_nacimiento = nacimiento
        if correo:
            cliente.email = correo
            request.user.email = correo          # el correo de la cuenta también
            request.user.save(update_fields=["email"])
        cliente.save()
        messages.success(request, "Perfil actualizado.")
    return redirect("/mi-cuenta/#perfil")


@login_required(login_url="/")
@require_POST
def eliminar_cuenta(request):
    destino = "/mi-cuenta/#cancelar"
    u = request.user
    if _es_equipo(u):
        messages.error(request, "Las cuentas del equipo no se eliminan desde aquí.")
        return redirect(destino)

    if not authenticate(request, username=u.get_username(),
                        password=request.POST.get("password", "")):
        messages.error(request, "La contraseña no es correcta. Tu cuenta no fue eliminada.")
        return redirect(destino)

    cliente = _cliente(u)
    if cliente:
        pendientes = CitaModel.objects.filter(
            cliente=cliente, fecha__gte=date.today()
        ).exclude(estado__in=["cancelada", "atendida"])
        if pendientes.exists():
            messages.error(request, "Tienes citas por venir. Cancélalas antes de eliminar tu cuenta.")
            return redirect(destino)
        # La ficha y su historial se conservan, solo queda inactiva
        cliente.activo = False
        cliente.save(update_fields=["activo"])
        _avisar_duena("Cuenta eliminada", f"{cliente.nombre} eliminó su cuenta.")

    logout(request)
    u.delete()
    return redirect("/")


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


def _enviar_boleta(cita, orden, monto, resp):
    """Genera la boleta de SIMULACIÓN, la guarda en media/boletas y la envía
    por correo a la clienta y a la dueña.
    Si algo falla, NO afecta al pago: solo se muestra el error en la terminal."""
    try:
        from boleta import generar_boleta

        try:
            tarjeta = _r(resp, "card_detail") or {}
        except Exception:
            tarjeta = {}
        if not isinstance(tarjeta, dict):
            tarjeta = {"card_number": getattr(tarjeta, "card_number", "")}

        datos = {
            "orden": orden,
            "fecha": timezone.localtime().strftime("%d-%m-%Y %H:%M"),
            "cliente": cita.cliente.nombre,
            "monto": monto,
            "tarjeta": str(tarjeta.get("card_number", "0000"))[-4:],
            "autorizacion": str(_r(resp, "authorization_code") or "-"),
        }
        nombre_servicio = "-"
        try:
            if cita.servicio:
                nombre_servicio = cita.servicio.nombre
                datos["servicio"] = "Abono - " + nombre_servicio
        except Exception:
            pass

        # Día y hora de la cita agendada (para el correo)
        fecha_cita, hora_cita = _fecha_hora_cita(cita)

        buffer = io.BytesIO()
        generar_boleta(datos, buffer)
        pdf = buffer.getvalue()

        # Copia en disco, para poder verla aunque el correo no esté configurado
        carpeta = os.path.join(settings.BASE_DIR, "media", "boletas")
        os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, f"boleta_{orden}.pdf"), "wb") as f:
            f.write(pdf)

        detalle_cita = (
            f"Clienta: {cita.cliente.nombre}\n"
            f"Servicio: {nombre_servicio}\n"
            f"Fecha: {fecha_cita}\n"
            f"Hora: {hora_cita}\n"
        )

        # Detalle de la cita para el correo de la clienta (sin la línea "Clienta")
        detalle_clienta = (
            f"Servicio: {nombre_servicio}\n"
            f"Fecha: {fecha_cita}\n"
            f"Hora: {hora_cita}\n"
        )

        # Correo de la clienta: se toma el de su cuenta (usuario) o el de su ficha,
        # pero NUNCA el de la dueña (así no se le manda a Nicolett el correo de la clienta).
        duena = (getattr(settings, "EMAIL_DUENA", "") or "").strip().lower()
        usuario = getattr(cita.cliente, "usuario", None)
        candidatos = [
            (getattr(usuario, "email", "") or "").strip(),
            (getattr(cita.cliente, "email", "") or "").strip(),
        ]
        correo_clienta = next((e for e in candidatos if e and e.lower() != duena), "")

        nombre = cita.cliente.nombre

        def _mandar(destino, asunto, cuerpo):
            msg = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=[destino],
            )
            msg.attach(f"boleta_{orden}.pdf", pdf, "application/pdf")
            msg.send(fail_silently=False)

        # ---- 1) Correo para la dueña (va primero y solo, para que siempre llegue) ----
        if duena:
            try:
                _mandar(
                    settings.EMAIL_DUENA,
                    f"Nueva reserva pagada - {nombre}",
                    f"Hola Nicolett, {nombre} pagó su abono de {_precio(monto)}.\n"
                    "Adjuntamos la boleta del abono de la clienta.\n\n"
                    "Reserva agendada:\n"
                    f"Clienta: {nombre}\n"
                    f"Servicio: {nombre_servicio}\n"
                    f"Fecha: {fecha_cita}\n"
                    f"Hora: {hora_cita}\n\n"
                    "Boleta adjunta (simulación).")
            except Exception as err:
                print("No se pudo enviar el correo a la dueña:", err)
        else:
            print("EMAIL_DUENA está vacío en el .env; no se envió el correo a la dueña.")

        # ---- 2) Correo para la clienta (si falla, ya no afecta el de la dueña) ----
        if correo_clienta:
            try:
                _mandar(
                    correo_clienta,
                    "Tu cita está confirmada - Nicolett Studio",
                    f"Hola {nombre}! Tu cita está registrada con éxito.\n"
                    f"Esta es tu boleta del abono de {_precio(monto)} "
                    "(documento de simulación).\n\n"
                    "Tu cita:\n" + detalle_clienta +
                    "\nTe esperamos en Nicolett Studio.")
            except Exception as err:
                print("No se pudo enviar el correo a la clienta:", err)
        else:
            print("La clienta no tiene un correo propio distinto al de la dueña; "
                  "no se envió su comprobante.")
    except Exception as e:
        print("No se pudo generar/enviar la boleta:", e)


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
        # Un solo correo a la dueña: lo manda _enviar_boleta (con servicio, fecha, hora y boleta)
        _enviar_boleta(cita, orden, monto, resp)      # <-- BOLETA DE SIMULACIÓN
        messages.success(request, f"¡Pago recibido! Tu cita quedó confirmada. Abono pagado: {_precio(monto)}.")
        return redirect("/mi-cuenta/#historial")

    _liberar(cita)
    messages.error(request, "El pago no fue aprobado. Tu hora quedó libre, puedes intentar con otra tarjeta.")
    return redirect("/mi-cuenta/#agendar")

@login_required(login_url="/")
def dias_bloqueados(request):
    fechas = DiaBloqueado.objects.filter(fecha__gte=date.today()).values_list("fecha", flat=True)
    return JsonResponse({"bloqueados": [f.isoformat() for f in fechas]})