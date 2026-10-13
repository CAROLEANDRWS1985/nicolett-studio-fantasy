"""Avisos para la dueña cuando una clienta agenda o cancela.
Canales (se activan en settings.py > AVISOS_DUENA): panel, correo y WhatsApp.
Si un canal falla, se registra en el log y NO se interrumpe la reserva."""
import logging
import threading
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

log = logging.getLogger(__name__)


def _cfg():
    return getattr(settings, "AVISOS_DUENA", {})


def avisar_duena(titulo, mensaje, cita=None):
    from .models import AvisoDuena

    if _cfg().get("PANEL", True):
        AvisoDuena.objects.create(titulo=titulo, mensaje=mensaje, cita=cita)

    transaction.on_commit(
        lambda: threading.Thread(target=_enviar_externos, args=(titulo, mensaje), daemon=True).start()
    )


def _enviar_externos(titulo, mensaje):
    cfg = _cfg()

    correo = cfg.get("EMAIL")
    if correo:
        try:
            send_mail(f"[Nicolett Studio] {titulo}", mensaje, None, [correo], fail_silently=False)
        except Exception:
            log.exception("No se pudo enviar el correo de aviso")

    telefono, apikey = cfg.get("WHATSAPP_TELEFONO"), cfg.get("WHATSAPP_APIKEY")
    if telefono and apikey:
        try:
            params = urllib.parse.urlencode({"phone": telefono, "text": f"{titulo}\n{mensaje}", "apikey": apikey})
            urllib.request.urlopen(f"https://api.callmebot.com/whatsapp.php?{params}", timeout=10).read()
        except Exception:
            log.exception("No se pudo enviar el aviso por WhatsApp")