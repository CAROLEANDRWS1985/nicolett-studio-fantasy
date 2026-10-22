import re
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape, linebreaks
from django.utils import timezone
from django.conf import settings
from .models import MensajeContacto
from .forms import RegistroForm


def link_whatsapp(numero):
    """'+569 1234 5678' -> 'https://wa.me/56912345678'"""
    digitos = re.sub(r'\D', '', numero or '')
    if len(digitos) == 9 and digitos.startswith('9'):
        digitos = '56' + digitos
    return 'https://wa.me/' + digitos


def enviar_correo_contacto(nombre, whatsapp, asunto, mensaje):
    enlace = link_whatsapp(whatsapp)
    fecha = timezone.localtime().strftime('%d-%m-%Y %H:%M')

    # Versión simple (por si el correo no muestra diseño)
    texto = (
        "Nuevo mensaje desde la página web de Nicolett Studio\n\n"
        f"Nombre: {nombre}\n"
        f"WhatsApp: {whatsapp}\n"
        f"Asunto: {asunto}\n\n"
        f"Mensaje:\n{mensaje}\n\n"
        f"Responder por WhatsApp: {enlace}"
    )

    # Versión con diseño (mismo estilo de las boletas)
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:24px;background:#f7f1ec;font-family:Arial,sans-serif;color:#2b2422;">
<table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e8dcd3;">

  <tr><td style="padding:24px;text-align:center;border-bottom:1px solid #e8dcd3;">
    <div style="font-size:26px;letter-spacing:4px;color:#2b2422;">NICOLETT</div>
    <div style="font-size:11px;letter-spacing:3px;color:#c4897a;">STUDIO FANTASY</div>
    <div style="font-size:13px;margin-top:10px;color:#6b5d57;">NUEVO MENSAJE DE CONTACTO</div>
  </td></tr>

  <tr><td style="padding:28px;font-size:14px;line-height:1.6;">

    <p style="font-size:18px;margin-top:0;">Hola Nicolett,</p>
    <p>Te escribieron desde la página web.</p>

    <table width="100%" cellpadding="8" cellspacing="0" style="font-size:13px;border-collapse:collapse;background:#f7f1ec;">
      <tr><td width="110"><b>Nombre</b></td><td>{escape(nombre)}</td></tr>
      <tr><td><b>WhatsApp</b></td><td>{escape(whatsapp)}</td></tr>
      <tr><td><b>Asunto</b></td><td>{escape(asunto)}</td></tr>
      <tr><td><b>Fecha</b></td><td>{fecha}</td></tr>
    </table>

    <p style="margin-top:20px;"><b>Mensaje:</b></p>
    <div style="border-left:3px solid #c4897a;padding:4px 16px;color:#4a403b;">
      {linebreaks(escape(mensaje))}
    </div>

    <p style="text-align:center;margin:28px 0 8px;">
      <a href="{enlace}" target="_blank"
         style="display:inline-block;background:#25D366;color:#ffffff;text-decoration:none;
                padding:14px 28px;border-radius:30px;font-weight:bold;letter-spacing:1px;">
        RESPONDER POR WHATSAPP
      </a>
    </p>

  </td></tr>

  <tr><td style="padding:16px 28px;font-size:11px;color:#a09089;text-align:center;border-top:1px solid #e8dcd3;">
    Nicolett Studio Fantasy · Mensaje automático de la página web
  </td></tr>

</table>
</body>
</html>
"""

    destino = getattr(settings, "CORREO_DUENA", settings.EMAIL_HOST_USER)
    correo = EmailMultiAlternatives(
        subject=f"Nuevo mensaje web: {asunto}",
        body=texto,
        to=[destino],
    )
    correo.attach_alternative(html, "text/html")
    correo.send()


def index(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        whatsapp = request.POST.get("whatsapp")
        asunto = request.POST.get("asunto")
        mensaje = request.POST.get("mensaje")

        MensajeContacto.objects.create(
            nombre=nombre,
            whatsapp=whatsapp,
            asunto=asunto,
            mensaje=mensaje,
        )

        try:
            enviar_correo_contacto(nombre, whatsapp, asunto, mensaje)
            messages.success(request, "¡Gracias! Tu mensaje fue enviado, te contactaremos pronto.")
        except Exception as e:
            print("No se pudo enviar el correo:", e)
            messages.error(request, "Tu mensaje quedó registrado, pero no pudimos enviarlo al correo. Escríbenos al WhatsApp +569 4032 2551.")
        return redirect(reverse('index') + '#contacto')

    return render(request, 'index.html')


def acercade(request):
    return render(request, 'acercade.html')

def inicio(request):
    return render(request, 'inicio.html')

def carro(request):
    return render(request, 'carro.html')

def productos(request):
    return render(request, 'productos.html')

def masajes(request):
    return render(request, 'masajes.html')

def coloracion(request):
    return render(request, 'coloracion.html')

def depilacion(request):
    return render(request, 'depilacion.html')

def unas(request):
    return render(request, 'unas.html')


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("index")
    else:
        form = RegistroForm()
    return render(request, "registro.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("index")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("index")