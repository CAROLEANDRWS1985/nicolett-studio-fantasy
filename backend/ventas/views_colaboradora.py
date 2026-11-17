"""Panel de colaboradoras: agenda propia, horario de trabajo e historial.
También la página donde la dueña define el horario de cada colaboradora."""
import calendar
from datetime import date, datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Cita, DiaBloqueado, DiaLibreColaboradora, HorarioColaboradora

GRUPO = 'Colaboradoras'
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def es_colaboradora(user):
    return (user.is_authenticated and not user.is_superuser
            and user.groups.filter(name=GRUPO).exists())


def solo_equipo(view):
    """Cualquier cuenta del equipo (dueña o colaboradora)."""
    @login_required(login_url='/admin-login/')
    @wraps(view)
    def envoltura(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return envoltura


def solo_duena(view):
    """Equipo, pero no colaboradoras: la dueña o la administración."""
    @solo_equipo
    @wraps(view)
    def envoltura(request, *args, **kwargs):
        if es_colaboradora(request.user):
            return redirect('mi_agenda')
        return view(request, *args, **kwargs)
    return envoltura


def _citas_de(user):
    """Citas de la colaboradora: las asignadas a ella, o sin asignar de sus clientas."""
    return (Cita.objects
            .filter(Q(profesional=user) | Q(profesional__isnull=True, cliente__profesional=user))
            .select_related('cliente', 'servicio'))


def _leer_mes(texto, defecto):
    try:
        d = datetime.strptime(texto or '', '%Y-%m').date()
        return d.year, d.month
    except ValueError:
        return defecto.year, defecto.month


def _leer_fecha(texto):
    try:
        return datetime.strptime(texto or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _estado_dia(fecha, horarios, libres, bloqueados):
    """Qué pasa ese día para la colaboradora: cerrado, libre o trabaja (con su horario)."""
    if fecha in bloqueados:
        return {'estado': 'cerrado', 'texto': bloqueados[fecha] or 'Peluquería cerrada'}
    if fecha in libres:
        return {'estado': 'libre', 'texto': libres[fecha] or 'Día libre'}
    h = horarios.get(fecha.weekday())
    if h:
        return {'estado': 'trabaja', 'texto': f'{h.hora_entrada:%H:%M} – {h.hora_salida:%H:%M}',
                'entrada': h.hora_entrada, 'salida': h.hora_salida}
    if horarios:
        return {'estado': 'libre', 'texto': 'Libre'}
    return {'estado': 'sin_horario', 'texto': ''}


def _mes_vecino(anio, mes, paso):
    mes += paso
    if mes == 0:
        return anio - 1, 12
    if mes == 13:
        return anio + 1, 1
    return anio, mes


# ---------------------------------------------------------------------------
# PANEL DE LA COLABORADORA
# ---------------------------------------------------------------------------

@solo_equipo
def mi_agenda(request):
    user = request.user
    hoy = timezone.localdate()

    anio, mes = _leer_mes(request.GET.get('mes'), hoy)
    ini = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    semanas_fechas = calendar.Calendar(firstweekday=0).monthdatescalendar(anio, mes)
    cal_ini, cal_fin = semanas_fechas[0][0], semanas_fechas[-1][-1]

    horarios = {h.dia_semana: h for h in HorarioColaboradora.objects.filter(colaborador=user)}
    libres = dict(DiaLibreColaboradora.objects
                  .filter(colaborador=user, fecha__range=(min(cal_ini, hoy), max(cal_fin, hoy)))
                  .values_list('fecha', 'motivo'))
    bloqueados = dict(DiaBloqueado.objects
                      .filter(fecha__range=(min(cal_ini, hoy), max(cal_fin, hoy)))
                      .values_list('fecha', 'motivo'))

    mis_citas = _citas_de(user)

    # Citas del mes visible (sin canceladas), agrupadas por día
    por_dia = {}
    for c in (mis_citas.filter(fecha__range=(cal_ini, cal_fin))
              .exclude(estado='cancelada').order_by('fecha', 'hora')):
        por_dia.setdefault(c.fecha, []).append(c)

    semanas = []
    for semana in semanas_fechas:
        fila = []
        for f in semana:
            info = _estado_dia(f, horarios, libres, bloqueados)
            info.update({
                'fecha': f,
                'en_mes': f.month == mes,
                'es_hoy': f == hoy,
                'num_citas': len(por_dia.get(f, [])),
            })
            fila.append(info)
        semanas.append(fila)

    # Día elegido en el calendario (por defecto hoy, si cae en el mes visible)
    dia_sel = _leer_fecha(request.GET.get('dia'))
    if dia_sel is None and ini <= hoy <= fin:
        dia_sel = hoy
    dia_sel_info = None
    if dia_sel:
        dia_sel_info = _estado_dia(dia_sel, horarios, libres, bloqueados)
        dia_sel_info.update({
            'fecha': dia_sel,
            'nombre_dia': DIAS[dia_sel.weekday()],
            'citas': list(mis_citas.filter(fecha=dia_sel).order_by('hora')),
        })

    # Hoy
    hoy_info = _estado_dia(hoy, horarios, libres, bloqueados)
    citas_hoy = list(mis_citas.filter(fecha=hoy).order_by('hora'))

    # Historial (citas pasadas), filtrable por mes
    hist_mes = request.GET.get('hist', '')
    historial = mis_citas.filter(fecha__lt=hoy).order_by('-fecha', '-hora')
    if hist_mes:
        ha, hm = _leer_mes(hist_mes, hoy)
        historial = historial.filter(fecha__year=ha, fecha__month=hm)
        hist_mes = f'{ha}-{hm:02d}'
    else:
        historial = historial[:60]

    semana_trabajo = [{'dia': DIAS[i], 'h': horarios.get(i)} for i in range(7)]

    pa, pm = _mes_vecino(anio, mes, -1)
    sa, sm = _mes_vecino(anio, mes, 1)

    return render(request, 'ventas/colaboradora_agenda.html', {
        'nombre': user.get_full_name() or user.username,
        'hoy': hoy,
        'hoy_nombre': DIAS[hoy.weekday()],
        'hoy_info': hoy_info,
        'citas_hoy': citas_hoy,
        'semanas': semanas,
        'dias_cortos': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
        'titulo_mes': f'{MESES[mes]} {anio}',
        'mes_actual': f'{anio}-{mes:02d}',
        'mes_anterior': f'{pa}-{pm:02d}',
        'mes_siguiente': f'{sa}-{sm:02d}',
        'dia_sel': dia_sel_info,
        'historial': historial,
        'hist_mes': hist_mes,
        'semana_trabajo': semana_trabajo,
        'tiene_horario': bool(horarios),
        'es_colaboradora': es_colaboradora(user),
        'proximos_libres': (DiaLibreColaboradora.objects
                            .filter(colaborador=user, fecha__gte=hoy).order_by('fecha')[:10]),
    })


# ---------------------------------------------------------------------------
# HORARIOS DEL EQUIPO (lo maneja la dueña)
# ---------------------------------------------------------------------------

def _hora(texto):
    try:
        return datetime.strptime(texto or '', '%H:%M').time()
    except ValueError:
        return None


@solo_duena
def horarios_equipo(request):
    equipo = User.objects.filter(is_active=True).filter(
        Q(is_staff=True) | Q(is_superuser=True)).order_by('first_name', 'username')
    grupo, _ = Group.objects.get_or_create(name=GRUPO)

    sel = None
    if request.GET.get('u') or request.POST.get('u'):
        sel = get_object_or_404(equipo, pk=request.GET.get('u') or request.POST.get('u'))

    if request.method == 'POST' and sel:
        accion = request.POST.get('accion')
        volver = redirect(f"{request.path}?u={sel.pk}")

        if accion == 'semana':
            # Rol: colaboradora (solo ve su agenda) o no
            if request.POST.get('es_colaboradora'):
                if sel.is_superuser:
                    messages.error(request, 'Una cuenta de superusuario no puede ser colaboradora.')
                    return volver
                sel.groups.add(grupo)
            else:
                sel.groups.remove(grupo)

            errores = []
            nuevos = []
            for i, nombre in enumerate(DIAS):
                if not request.POST.get(f'trabaja_{i}'):
                    continue
                e, s = _hora(request.POST.get(f'entrada_{i}')), _hora(request.POST.get(f'salida_{i}'))
                if not e or not s:
                    errores.append(f'{nombre}: falta la hora de entrada o de salida.')
                elif s <= e:
                    errores.append(f'{nombre}: la salida debe ser después de la entrada.')
                else:
                    nuevos.append(HorarioColaboradora(colaborador=sel, dia_semana=i,
                                                      hora_entrada=e, hora_salida=s))
            if errores:
                for e in errores:
                    messages.error(request, e)
                return volver
            HorarioColaboradora.objects.filter(colaborador=sel).delete()
            HorarioColaboradora.objects.bulk_create(nuevos)
            messages.success(request, f'Horario de {sel.get_full_name() or sel.username} guardado.')
            return volver

        if accion == 'agregar_libre':
            f = _leer_fecha(request.POST.get('fecha'))
            if not f:
                messages.error(request, 'Elige una fecha válida.')
            else:
                DiaLibreColaboradora.objects.update_or_create(
                    colaborador=sel, fecha=f,
                    defaults={'motivo': request.POST.get('motivo', '').strip()[:150]})
                messages.success(request, f'Día libre agregado: {f:%d/%m/%Y}.')
            return volver

        if accion == 'borrar_libre':
            DiaLibreColaboradora.objects.filter(colaborador=sel, pk=request.POST.get('libre_id')).delete()
            messages.success(request, 'Día libre eliminado.')
            return volver

    filas = []
    libres = []
    sel_es_colab = False
    if sel:
        h = {x.dia_semana: x for x in HorarioColaboradora.objects.filter(colaborador=sel)}
        filas = [{'i': i, 'dia': d, 'h': h.get(i)} for i, d in enumerate(DIAS)]
        libres = DiaLibreColaboradora.objects.filter(
            colaborador=sel, fecha__gte=timezone.localdate()).order_by('fecha')
        sel_es_colab = sel.groups.filter(name=GRUPO).exists()

    lista = [{'u': u, 'colab': u.groups.filter(name=GRUPO).exists(),
              'dias': HorarioColaboradora.objects.filter(colaborador=u).count()} for u in equipo]

    return render(request, 'ventas/colaboradora_horarios.html', {
        'lista': lista,
        'sel': sel,
        'sel_es_colab': sel_es_colab,
        'filas': filas,
        'libres': libres,
    })