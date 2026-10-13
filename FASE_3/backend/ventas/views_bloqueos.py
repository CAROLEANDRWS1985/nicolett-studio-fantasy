import json
from datetime import date

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ventas.permisos import solo_equipo
from .models import DiaBloqueado


@solo_equipo
def calendario_bloqueos(request):
    return render(request, "ventas/calendario_bloqueos.html")


@solo_equipo
def bloqueos_datos(request):
    dias = {d.fecha.isoformat(): (d.motivo or "") for d in DiaBloqueado.objects.all()}
    return JsonResponse({"dias": dias})


@solo_equipo
@require_POST
def bloqueos_guardar(request):
    try:
        datos = json.loads(request.body)
        fechas = [date.fromisoformat(f) for f in datos.get("fechas", [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "Datos inválidos."}, status=400)

    if not fechas or len(fechas) > 400:
        return JsonResponse({"error": "Elige entre 1 y 400 días."}, status=400)

    accion = datos.get("accion")
    motivo = (datos.get("motivo") or "").strip()[:200]

    if accion == "bloquear":
        for f in fechas:
            DiaBloqueado.objects.update_or_create(fecha=f, defaults={"motivo": motivo or None})
    elif accion == "desbloquear":
        DiaBloqueado.objects.filter(fecha__in=fechas).delete()
    else:
        return JsonResponse({"error": "Acción inválida."}, status=400)

    return JsonResponse({"ok": True})