"""Portal de la clienta (/mi-cuenta/) + avisos para la dueña.

Usa tus modelos: Cliente, ServicioBelleza, Cita (+ AvisoDuena nuevo).
"""
from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .avisos import avisar_duena
from .models import AvisoDuena, Cita, Cliente, ServicioBelleza

# ---- Ajusta a tu estudio -------------------------------------
LOGIN = "/admin-login/"      # misma página de login que ya usas
HORA_INICIO = 9              # abre a las 9:00
HORA_FIN = 19                # cierra a las 19:00
PASO_MIN = 30                # las horas se ofrecen cada 30 min
DIAS_CERRADOS = {6}          # 0=lunes ... 6=domingo (el calendario ya bloquea domingos)
CANCELAR_HASTA_HORAS = 12    # se puede cancelar hasta X horas antes
# --------------------------------------------------------------

CATEGORIAS = [
    ("Uñas", ("uña", "manicure", "pedicure", "gel", "acrílic", "acrilic")),
    ("Cejas y pestañas", ("ceja", "pestaña", "lifting", "laminad")),
    ("Depilación", ("depil", "cera")),
    ("Masajes", ("masaje", "drenaje", "relajación", "relajacion")),
    ("Color y cabello", ("color", "tinte", "balayage", "mechas", "corte", "peinado", "alisado", "cabello")),
]


def clp(valor):
    return f"${int(valor):,}".replace(",", ".")


def categoria_de(nombre):
    n = nombre.lower()
    for cat, claves in CATEGORIAS:
        if any(k in n for k in claves):
            return cat
    return "Otros"


def inicio(cita):
    return datetime.combine(cita.fecha, cita.hora)


def texto_cita(c):
    servicio = c.servicio.nombre if c.servicio else "Servicio"
    return f"{servicio} · {c.fecha:%d/%m/%Y} a las {c.hora:%H:%M} ({c.get_estado_display()})"


def ir(seccion):
    return redirect(f"/mi-cuenta/#{seccion}")


def obtener_cliente(user):
    """Devuelve la ficha de la clienta. La vincula por correo o la crea,
    así nunca aparece el mensaje de 'usuario no vinculado'."""
    cliente = Cliente.objects.filter(usuario=user).first()
    if cliente:
        return cliente
    if user.email:
        cliente = Cliente.objects.filter(email__iexact=user.email, usuario__isnull=True).first()
    if cliente:
        cliente.usuario = user
        cliente.save(update_fields=["usuario"])
        return cliente
    return Cliente.objects.create(
        usuario=user,
        nombre=user.get_full_name() or user.username,
        email=user.email or None,
    )


def calcular_slots(fecha, minutos):
    """Horas del día con su disponibilidad, considerando la duración del servicio."""
    if fecha.weekday() in DIAS_CERRADOS:
        return []
    dur = timedelta(minutes=minutos)
    ocupadas = []
    for c in Cita.objects.filter(fecha=fecha).exclude(estado="cancelada").select_related("servicio"):
        ini = inicio(c)
        ocupadas.append((ini, ini + timedelta(minutes=c.servicio.duracion_minutos if c.servicio else PASO_MIN)))

    ahora = datetime.now()
    h = datetime.combine(fecha, time(HORA_INICIO))
    cierre = datetime.combine(fecha, time(HORA_FIN))
    slots = []
    while h + dur <= cierre:
        choca = any(h < fin and h + dur > ini for ini, fin in ocupadas)
        slots.append({"hora": h.strftime("%H:%M"), "libre": h > ahora and not choca})
        h += timedelta(minutes=PASO_MIN)
    return slots


# ======================= PORTAL DE LA CLIENTA =======================

@login_required(login_url=LOGIN)
def mi_cuenta(request):
    cliente = obtener_cliente(request.user)
    ahora = datetime.now()

    servicios = [
        SimpleNamespace(
            pk=s.pk, nombre=s.nombre, descripcion=s.descripcion,
            duracion=s.duracion_minutos, precio=clp(s.precio), categoria=categoria_de(s.nombre),
        )
        for s in ServicioBelleza.objects.filter(activo=True).order_by("nombre")
    ]

    todas = list(cliente.citas.select_related("servicio").order_by("-fecha", "-hora"))
    proximas = [c for c in reversed(todas)
                if c.estado in ("pendiente", "confirmada") and inicio(c) >= ahora]

    return render(request, "ventas/mi_cuenta.html", {
        "nombre": cliente.nombre,
        "cliente": cliente,
        "tiene_cliente": True,
        "servicios": servicios,
        "categorias": sorted({s.categoria for s in servicios}),
        "citas": [SimpleNamespace(pk=c.pk, texto=texto_cita(c)) for c in proximas],
        "encabezados": ["Fecha", "Hora", "Servicio", "Estado"],
        "filas": [
            [c.fecha.strftime("%d/%m/%Y"), c.hora.strftime("%H:%M"),
             c.servicio.nombre if c.servicio else "—", c.get_estado_display()]
            for c in todas
        ],
    })


@login_required(login_url=LOGIN)
def horarios(request):
    try:
        fecha = datetime.strptime(request.GET["fecha"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        return JsonResponse({"slots": []})
    minutos = PASO_MIN
    servicio_id = request.GET.get("servicio")
    if servicio_id:
        s = ServicioBelleza.objects.filter(pk=servicio_id, activo=True).first()
        if s:
            minutos = s.duracion_minutos
    return JsonResponse({"slots": calcular_slots(fecha, minutos)})


@login_required(login_url=LOGIN)
@require_POST
def agendar_cita(request):
    cliente = obtener_cliente(request.user)
    try:
        servicio = ServicioBelleza.objects.get(pk=request.POST["servicio"], activo=True)
        fecha = datetime.strptime(request.POST["fecha"], "%Y-%m-%d").date()
        hora = datetime.strptime(request.POST["hora"], "%H:%M").time()
    except (KeyError, ValueError, ServicioBelleza.DoesNotExist):
        messages.error(request, "Revisa el formulario: elige servicio, día y hora.")
        return ir("agendar")

    nombre = request.POST.get("nombre", "").strip()
    if not nombre:
        messages.error(request, "Escribe tu nombre para agendar.")
        return ir("agendar")

    libres = {s["hora"] for s in calcular_slots(fecha, servicio.duracion_minutos) if s["libre"]}
    if hora.strftime("%H:%M") not in libres:
        messages.error(request, "Esa hora ya no está disponible. Elige otra.")
        return ir("agendar")

    cliente.nombre = nombre
    cliente.save(update_fields=["nombre"])

    cita = Cita.objects.create(
        cliente=cliente, servicio=servicio, fecha=fecha, hora=hora,
        estado="pendiente", notas="Agendada por la clienta desde Mi cuenta",
    )

    avisar_duena(
        "Nueva cita agendada",
        f"{cliente.nombre} agendó {servicio.nombre} el {fecha:%d/%m/%Y} a las {hora:%H:%M}.\n"
        f"Teléfono: {cliente.telefono or 'sin teléfono'}\n"
        f"Correo: {cliente.email or 'sin correo'}",
        cita,
    )
    messages.success(request, "¡Cita agendada! Te avisaremos cuando esté confirmada.")
    return ir("inicio")


@login_required(login_url=LOGIN)
@require_POST
def cancelar_cita(request, pk):
    cliente = obtener_cliente(request.user)
    cita = get_object_or_404(Cita, pk=pk, cliente=cliente)

    if cita.estado not in ("pendiente", "confirmada"):
        messages.error(request, "Esa cita ya no se puede cancelar.")
    elif inicio(cita) - datetime.now() < timedelta(hours=CANCELAR_HASTA_HORAS):
        messages.error(request, f"Solo puedes cancelar hasta {CANCELAR_HASTA_HORAS} horas antes. Escríbenos para ayudarte.")
    else:
        cita.estado = "cancelada"
        cita.save(update_fields=["estado"])
        servicio = cita.servicio.nombre if cita.servicio else "su cita"
        avisar_duena(
            "Cita cancelada por la clienta",
            f"{cliente.nombre} canceló {servicio} del {cita.fecha:%d/%m/%Y} a las {cita.hora:%H:%M}.\n"
            f"Teléfono: {cliente.telefono or 'sin teléfono'}\n"
            f"Correo: {cliente.email or 'sin correo'}",
            cita,
        )
        messages.success(request, "Tu cita fue cancelada. Ya avisamos al estudio.")
    return ir("cancelar")


@login_required(login_url=LOGIN)
@require_POST
def editar_perfil(request):
    cliente = obtener_cliente(request.user)
    nombre = request.POST.get("nombre", "").strip()
    if not nombre:
        messages.error(request, "El nombre no puede quedar vacío.")
        return ir("perfil")
    cliente.nombre = nombre
    cliente.telefono = request.POST.get("telefono", "").strip() or None
    cliente.save(update_fields=["nombre", "telefono"])
    messages.success(request, "Perfil actualizado.")
    return ir("perfil")


# ======================= AVISOS PARA LA DUEÑA =======================

def _es_staff(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(_es_staff, login_url=LOGIN)
def panel_avisos(request):
    if request.method == "POST":
        AvisoDuena.objects.filter(leido=False).update(leido=True)
        return redirect("panel_avisos")
    return render(request, "ventas/avisos.html", {
        "avisos": AvisoDuena.objects.select_related("cita")[:100],
        "sin_leer": AvisoDuena.objects.filter(leido=False).count(),
    })