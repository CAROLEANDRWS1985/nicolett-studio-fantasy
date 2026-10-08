from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegistroForm


def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(request, 'Cuenta creada correctamente')
            return redirect('mi_cuenta')
        else:
            messages.error(request, 'Revisa los datos ingresados')
    else:
        form = RegistroForm()

    return render(request, 'registro.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, username=username, password=password)
            if usuario is not None:
                login(request, usuario)

                # Respeta ?next= si venía de una página protegida
                siguiente = request.POST.get('next') or request.GET.get('next')
                if siguiente and url_has_allowed_host_and_scheme(
                    siguiente, allowed_hosts={request.get_host()}
                ):
                    return redirect(siguiente)

                # Equipo (administradora / trabajadores) -> panel
                    if usuario.is_staff or usuario.is_superuser:
                     return redirect('/panel/gestionar/citas/')
                # Clientas -> su cuenta
                return redirect('mi_cuenta')
        messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')