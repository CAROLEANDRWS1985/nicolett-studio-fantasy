from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMessage
from django.conf import settings
from .models import MensajeContacto
from .forms import RegistroForm


def enviar_correo_contacto(nombre, email, asunto, mensaje):
    cuerpo = (
        "Nuevo mensaje desde la página web de Nicolett Studio\n"
        "----------------------------------------------------\n\n"
        f"Nombre:  {nombre}\n"
        f"Correo:  {email}\n"
        f"Asunto:  {asunto}\n\n"
        f"Mensaje:\n{mensaje}\n\n"
        "----------------------------------------------------\n"
        "Para responder, usa el botón Responder de tu correo."
    )
    destino = getattr(settings, "CORREO_DUENA", settings.EMAIL_HOST_USER)
    correo = EmailMessage(
        subject=f"Nuevo mensaje web: {asunto}",
        body=cuerpo,
        to=[destino],
        reply_to=[email],
    )
    correo.send()


def index(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        asunto = request.POST.get("asunto")
        mensaje = request.POST.get("mensaje")

        MensajeContacto.objects.create(
            nombre=nombre,
            email=email,
            asunto=asunto,
            mensaje=mensaje,
        )

        try:
            enviar_correo_contacto(nombre, email, asunto, mensaje)
        except Exception as e:
            print("No se pudo enviar el correo:", e)

        messages.success(request, "¡Gracias! Tu mensaje fue enviado, te contactaremos pronto.")
        return redirect('index')

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