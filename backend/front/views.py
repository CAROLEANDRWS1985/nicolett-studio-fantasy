import os
import smtplib
import traceback
from email.message import EmailMessage
from pathlib import Path

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from .models import MensajeContacto
from .forms import RegistroForm


# ---------------------------------------------------------------------------
# CORREO DE CONTACTO
# Usa la cuenta de Gmail y la contraseña de aplicación guardadas en el .env
# del backend (carpeta hermana de "frontend"), así no depende de la
# configuración de esta página.
# ---------------------------------------------------------------------------

# >>> RELLENA ESTOS 3 DATOS (entre las comillas) si el correo no te llega <<<
# Si los dejas vacíos, el programa los busca solo en el .env del backend.
MI_GMAIL = ''            # Gmail que ENVÍA los mensajes, ej: 'micuenta@gmail.com'
MI_CLAVE_APP = ''        # Contraseña de aplicación de Gmail (16 letras, con o sin espacios)
CORREO_DE_LA_DUENA = ''  # Correo donde debe LLEGAR el mensaje de la persona


def _leer_env_backend():
    """Lee ...\\nicolett\\backend\\.env y devuelve un diccionario."""
    datos = {}
    ruta = Path(__file__).resolve().parents[2] / 'backend' / '.env'
    try:
        for linea in ruta.read_text(encoding='utf-8-sig').splitlines():
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            if linea.lower().startswith('export '):
                linea = linea[7:]
            clave, valor = linea.split('=', 1)
            datos[clave.strip()] = valor.strip().strip('"').strip("'")
    except OSError:
        print('AVISO: no se pudo leer el .env del backend en', ruta)
    return datos


def _config_correo():
    env = _leer_env_backend()

    def buscar(*nombres, default=''):
        for n in nombres:
            valor = env.get(n) or os.environ.get(n) or getattr(settings, n, '')
            if valor:
                return str(valor).strip()
        return default

    usuario = MI_GMAIL.strip() or buscar('EMAIL_HOST_USER', 'EMAIL_USER', 'GMAIL_USER')
    clave = (MI_CLAVE_APP or buscar('EMAIL_HOST_PASSWORD', 'EMAIL_PASSWORD',
                                    'GMAIL_APP_PASSWORD', 'GMAIL_PASSWORD')).replace(' ', '')
    destino = CORREO_DE_LA_DUENA.strip() or buscar('CORREO_DUENA', 'DUENA_EMAIL', 'EMAIL_DUENA',
                                                   'EMAIL_DESTINO', 'CORREO_DESTINO')
    if not destino:
        for k, v in env.items():
            if ('DUENA' in k.upper() or 'DESTINO' in k.upper()) and '@' in v:
                destino = v
                break
    return usuario, clave, destino or usuario


def enviar_correo_contacto(nombre, email, asunto, mensaje):
    usuario, clave, destino = _config_correo()
    if not usuario or not clave:
        raise ValueError(
            'Faltan el correo o la contraseña de aplicación en el .env del backend '
            '(EMAIL_HOST_USER / EMAIL_HOST_PASSWORD).'
        )

    asunto_limpio = ' '.join((asunto or 'Sin asunto').split())
    email_limpio = ' '.join((email or '').split())

    cuerpo = (
        "Nuevo mensaje desde la página web de Nicolett Studio\n"
        "----------------------------------------------------\n\n"
        f"Nombre:  {nombre}\n"
        f"Correo:  {email_limpio}\n"
        f"Asunto:  {asunto_limpio}\n\n"
        f"Mensaje:\n{mensaje}\n\n"
        "----------------------------------------------------\n"
        "Para responder, usa el botón Responder de tu correo."
    )

    msg = EmailMessage()
    msg['Subject'] = f'Nuevo mensaje web: {asunto_limpio}'
    msg['From'] = usuario
    msg['To'] = destino
    if email_limpio:
        msg['Reply-To'] = email_limpio
    msg.set_content(cuerpo)

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as servidor:
        servidor.starttls()
        servidor.login(usuario, clave)
        servidor.send_message(msg)
    print(f'CORREO CONTACTO ENVIADO: de {usuario} para {destino}')
    return usuario, destino


# ---------------------------------------------------------------------------
# PÁGINAS
# ---------------------------------------------------------------------------

def index(request):
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        email = (request.POST.get("email") or "").strip()
        asunto = (request.POST.get("asunto") or "").strip()
        mensaje = (request.POST.get("mensaje") or "").strip()

        MensajeContacto.objects.create(
            nombre=nombre,
            email=email,
            asunto=asunto,
            mensaje=mensaje,
        )

        try:
            de, para = enviar_correo_contacto(nombre, email, asunto, mensaje)
            messages.success(request, "¡Gracias! Tu mensaje fue enviado, te contactaremos pronto.")
            if settings.DEBUG:
                messages.info(request, f"[Modo pruebas] Correo enviado desde {de} hacia {para}.")
        except Exception as e:
            print("ERROR CORREO CONTACTO:", repr(e))
            traceback.print_exc()
            messages.warning(request, "Recibimos tu mensaje, pero no pudimos enviarlo por correo en este momento.")
            if settings.DEBUG:
                messages.error(request, f"[Modo pruebas] Motivo del error: {e!r}")

        return redirect(reverse('index') + '#mensajes-contacto')

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