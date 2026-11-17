"""NUEVO: las colaboradoras solo pueden entrar a su agenda.
Si intentan abrir el panel de la dueña, la API o los recordatorios, vuelven a "Mi agenda"."""
from django.shortcuts import redirect

GRUPO = 'Colaboradoras'
BLOQUEADAS = ('/panel', '/recordatorios', '/api/', '/menu')
PERMITIDAS = ('/panel/mi-agenda/', '/api/catalogo/')


class SoloAgendaColaboradoras:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        ruta = request.path
        if (user is not None and user.is_authenticated and not user.is_superuser
                and ruta.startswith(BLOQUEADAS) and not ruta.startswith(PERMITIDAS)
                and user.groups.filter(name=GRUPO).exists()):
            return redirect('/panel/mi-agenda/')
        return self.get_response(request)