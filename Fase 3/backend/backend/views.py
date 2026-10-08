from functools import wraps

from django.db.models import Sum, Count
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework import viewsets, permissions
from ventas.models import Cliente, Comuna, Producto, Inventario, ServicioBelleza, Cita, Pago, Abono
from ventas.serializers import (
    ClienteSerializer, ComunaSerializer, ProductoSerializer,
    InventarioSerializer, ServicioBellezaSerializer, CitaSerializer,
    PagoSerializer, AbonoSerializer
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout


def solo_equipo(view):
    """Solo cuentas del equipo (is_staff / superuser). Las clientas reciben 403."""
    @login_required(login_url='/segur/login/')
    @wraps(view)
    def envoltura(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return envoltura


def admin_login(request):
    error = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Equipo -> panel, clientas -> su cuenta
            if user.is_staff or user.is_superuser:
                return redirect('/panel/gestionar/citas/')
            return redirect('mi_cuenta')
        else:
            error = 'Usuario o contraseña incorrectos'
    return render(request, 'ventas/login.html', {'error': error})


def admin_logout(request):
    logout(request)
    return redirect('/')


@solo_equipo
def panel_administrativo(request):
    clientes = Cliente.objects.all().order_by('-fecha_registro')[:20]
    productos = Producto.objects.all()
    inventario = Inventario.objects.select_related('producto').all()
    citas = Cita.objects.select_related('cliente', 'servicio').order_by('-fecha', '-hora')[:20]

    total_clientes = Cliente.objects.count()
    total_productos = Producto.objects.count()
    stock_bajo = [i for i in inventario if i.stock_actual <= i.stock_minimo]

    context = {
        'clientes': clientes,
        'productos': productos,
        'inventario': inventario,
        'citas': citas,
        'total_clientes': total_clientes,
        'total_productos': total_productos,
        'stock_bajo': stock_bajo,
    }
    return render(request, 'ventas/panel.html', context)


def home(request):
    total_clientes = Cliente.objects.count()
    return render(request, 'ventas/home.html', {'total_personas': total_clientes})


def contacto(request):
    if request.method == 'POST':
        nombre   = request.POST.get('nombre')
        rut      = request.POST.get('rut')
        email    = request.POST.get('email')
        telefono = request.POST.get('telefono')
        comuna   = request.POST.get('comuna')

        rut_limpio = ''.join(filter(str.isdigit, rut))

        Cliente.objects.create(
            nombre   = nombre,
            rut      = rut_limpio,
            email    = email,
            telefono = telefono,
            comuna_id = comuna,
            activo   = True
        )
        return redirect('home')

    comunas = Comuna.objects.all()
    return render(request, 'ventas/contacto.html', {'comunas': comunas})


class LoadMenu(APIView):
    def get(self, request, format=None):
        return JsonResponse({
            'BACKEND': 'http://localhost:8000/',
            'API': 'http://localhost:8000/api/',
        })


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ClienteSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductoSerializer


class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = InventarioSerializer


class ServicioBellezaViewSet(viewsets.ModelViewSet):
    queryset = ServicioBelleza.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ServicioBellezaSerializer


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = CitaSerializer


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = PagoSerializer


class AbonoViewSet(viewsets.ModelViewSet):
    queryset = Abono.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AbonoSerializer


def formato_clp(valor):
    return f"${int(valor):,}".replace(',', '.')


@solo_equipo
def admin_dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    ingresos_mes = Pago.objects.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum('monto'))['total'] or 0
    citas_mes = Cita.objects.filter(fecha__gte=inicio_mes)
    citas_mes_count = citas_mes.count()
    canceladas_mes = citas_mes.filter(estado='cancelada').count()
    tasa_cancelacion = (canceladas_mes / citas_mes_count * 100) if citas_mes_count else 0

    clientas_activas = Cliente.objects.filter(activo=True).count()

    citas_hoy = Cita.objects.filter(fecha=hoy).select_related('cliente', 'servicio').order_by('hora')[:4]

    por_categoria = (
        Producto.objects.filter(activo=True)
        .exclude(categoria__isnull=True)
        .exclude(categoria__exact='')
        .values('categoria')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    context = {
        'ingresos_mes_fmt': formato_clp(ingresos_mes),
        'citas_mes_count': citas_mes_count,
        'clientas_activas': clientas_activas,
        'tasa_cancelacion': round(tasa_cancelacion, 1),
        'citas_hoy': citas_hoy,
        'por_categoria': por_categoria,
        'hoy': hoy,
    }
    return render(request, 'ventas/dashboard.html', context)


@solo_equipo
def admin_servicios(request):
    servicios = ServicioBelleza.objects.all().order_by('nombre')
    servicios_data = []
    for s in servicios:
        horas = s.duracion_minutos // 60
        minutos = s.duracion_minutos % 60
        if horas and minutos:
            duracion = f"{horas} h {minutos} min"
        elif horas:
            duracion = f"{horas} hrs" if horas > 1 else "1 hr"
        else:
            duracion = f"{minutos} min"
        servicios_data.append({
            'obj': s,
            'precio_fmt': formato_clp(s.precio),
            'duracion_fmt': duracion,
        })

    context = {
        'servicios_data': servicios_data,
        'activos': servicios.filter(activo=True).count(),
        'inactivos': servicios.filter(activo=False).count(),
    }
    return render(request, 'ventas/servicios.html', context)


@solo_equipo
def admin_usuarios(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    clientes = Cliente.objects.all().order_by('-fecha_registro')

    clientas_recientes = []
    for c in clientes[:10]:
        ultima_cita = c.citas.order_by('-fecha').first()
        clientas_recientes.append({
            'cliente': c,
            'num_visitas': c.citas.count(),
            'ultimo_servicio': ultima_cita.servicio.nombre if ultima_cita and ultima_cita.servicio else '—',
        })

    context = {
        'total_clientas': clientes.count(),
        'nuevas_mes': clientes.filter(fecha_registro__date__gte=inicio_mes).count(),
        'clientas_activas': clientes.filter(activo=True).count(),
        'clientas_recientes': clientas_recientes,
    }
    return render(request, 'ventas/usuarios.html', context)


@solo_equipo
def admin_citas_hoy(request):
    hoy = timezone.localdate()
    citas = Cita.objects.filter(fecha=hoy).select_related('cliente', 'servicio').order_by('hora')
    context = {
        'citas': citas,
        'hoy': hoy,
    }
    return render(request, 'ventas/citas_hoy.html', context)


@solo_equipo
def admin_precios_promos(request):
    from django.contrib import messages
    from django.shortcuts import redirect

    if request.method == 'POST':
        s = ServicioBelleza.objects.filter(pk=request.POST.get('servicio_id')).first()
        accion = request.POST.get('accion', 'guardar')
        if not s:
            messages.error(request, 'No se encontró el servicio.')
            return redirect('admin_precios_promos')

        if accion == 'eliminar':
            s.activo = False
            s.save()
            messages.success(request, f'"{s.nombre}" ya no aparece para las clientas.')
        elif accion == 'reactivar':
            s.activo = True
            s.save()
            messages.success(request, f'"{s.nombre}" volvió a estar disponible.')
        else:
            nombre = request.POST.get('nombre', '').strip() or s.nombre
            try:
                if 'precio_s' in request.POST:
                    valores = {}
                    for t in ('s', 'm', 'l', 'xl'):
                        n = int(request.POST.get('precio_' + t, ''))
                        if n < 0:
                            raise ValueError
                        valores[t] = n
                    s.precio_s, s.precio_m = valores['s'], valores['m']
                    s.precio_l, s.precio_xl = valores['l'], valores['xl']
                    s.precio = valores['s']
                else:
                    precio = int(request.POST.get('precio', ''))
                    if precio < 0:
                        raise ValueError
                    s.precio = precio
            except ValueError:
                messages.error(request, 'Escribe precios válidos (solo números, en todas las tallas).')
                return redirect('admin_precios_promos')
            try:
                s.nombre = nombre
                s.save()
                messages.success(request, f'"{s.nombre}" guardado.')
            except Exception as e:
                messages.error(request, f'No se pudo guardar: {e}')
        return redirect('admin_precios_promos')

    servicios = ServicioBelleza.objects.all().order_by('nombre')
    servicios_data = [{'obj': s, 'precio_fmt': formato_clp(s.precio)} for s in servicios]
    return render(request, 'ventas/precios_promos.html', {'servicios_data': servicios_data, 'servicios': servicios})