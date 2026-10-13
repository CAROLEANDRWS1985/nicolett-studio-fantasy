from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegistroForm


def _es_equipo(u):
    return u.is_staff or u.is_superuser


def registro_view(request):
    # Si había una sesión abierta (por ejemplo el panel), se cierra antes de registrar
    if request.user.is_authenticated:
        logout(request)

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            request.session['puede_abrir'] = True
            messages.success(request, 'Cuenta creada correctamente')
            return redirect('mi_cuenta')
        else:
            messages.error(request, 'Revisa los datos ingresados')
    else:
        form = RegistroForm()

    return render(request, 'registro.html', {'form': form})


def login_view(request):
    # Al llegar al login se cierra CUALQUIER sesión abierta (clienta o equipo)
    if request.user.is_authenticated:
        logout(request)

    # Si venía desde "Reservar", se recuerda a dónde volver después de entrar
    if request.method == 'GET' and request.GET.get('next'):
        request.session['next_login'] = request.GET.get('next')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, username=username, password=password)
            if usuario is not None:
                siguiente = (request.POST.get('next') or request.GET.get('next')
                             or request.session.get('next_login'))
                login(request, usuario)
                request.session['puede_abrir'] = True
                request.session.pop('next_login', None)

                # Equipo (administradora / trabajadores) -> panel
                if _es_equipo(usuario):
                    return redirect('/panel/gestionar/citas/')

                # Clientas: vuelven a donde iban, pero nunca hacia el panel
                if (siguiente
                        and not siguiente.startswith('/panel')
                        and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()})):
                    return redirect(siguiente)

                return redirect('mi_cuenta')
        messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')