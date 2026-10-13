import re
from datetime import date, datetime
from urllib.parse import quote

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.shortcuts import render, redirect

from .models import Cita, AvisoDuena

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _fecha_larga(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _wa_numero(tel):
    """Deja el teléfono en formato WhatsApp (56 + 9 dígitos). Vacío si no sirve."""
    d = re.sub(r'\D', '', tel or '')
    if d.startswith('56') and len(d) == 11:
        return d
    if len(d) == 9:
        return '56' + d
    if len(d) == 8:
        return '569' + d
    return ''


def _activas():
    return (Cita.objects
            .filter(estado__in=['pendiente', 'confirmada'], fecha__gte=date.today())
            .select_related('cliente', 'servicio'))


def _mostrar_form(request, error=''):
    activas = _activas()
    fechas = []
    for f in activas.values('fecha').annotate(n=Count('id')).order_by('fecha'):
        fechas.append({
            'iso': f['fecha'].isoformat(),
            'texto': f"{_fecha_larga(f['fecha'])} ({f['n']} cita{'s' if f['n'] != 1 else ''})",
        })
    return render(request, 'ventas/cancelar_emergencia.html', {
        'modo': 'form',
        'total': activas.count(),
        'fechas': fechas,
        'error': error,
        'motivo': request.POST.get('motivo', 'Tuvimos una emergencia y no podremos atender.'),
    })


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='/')
def cancelar_emergencia(request):
    # ---- Pantalla con la lista de clientas para avisar por WhatsApp ----
    if request.method == 'GET' and request.GET.get('listo'):
        datos = request.session.get('emergencia')
        if datos:
            return render(request, 'ventas/cancelar_emergencia.html', {
                'modo': 'lista', 'lista': datos['lista'], 'n_citas': datos['n'],
            })
        return redirect('cancelar_emergencia')

    # ---- Cancelar ----
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        citas = _activas()

        if request.POST.get('alcance') == 'dia':
            try:
                dia = datetime.strptime(request.POST.get('fecha', ''), '%Y-%m-%d').date()
            except ValueError:
                return _mostrar_form(request, 'Elige un día de la lista.')
            citas = citas.filter(fecha=dia)

        citas = list(citas.order_by('cliente_id', 'fecha', 'hora'))
        if not citas:
            return _mostrar_form(request, 'No hay citas para cancelar con esa selección.')

        por_clienta = {}
        for c in citas:
            por_clienta.setdefault(c.cliente, []).append(c)

        lista = []
        for cli, cs in por_clienta.items():
            lineas = [
                f"• {c.servicio.nombre if c.servicio else 'Cita'} – "
                f"{_fecha_larga(c.fecha)}, {c.hora.strftime('%H:%M')}"
                for c in cs
            ]
            msg = f"Hola {cli.nombre.split()[0]}, te escribimos de Nicolett Studio. "
            msg += ("Lamentablemente debemos cancelar tu cita:\n" if len(cs) == 1
                    else "Lamentablemente debemos cancelar tus citas:\n")
            msg += "\n".join(lineas)
            if motivo:
                msg += f"\n\n{motivo}"
            msg += "\n\nPedimos disculpas por las molestias. Nos pondremos en contacto contigo para reagendar tu hora."

            num = _wa_numero(cli.telefono)
            lista.append({
                'nombre': cli.nombre,
                'detalle': "; ".join(l[2:] for l in lineas),
                'wa': f"https://wa.me/{num}?text={quote(msg)}" if num else '',
            })

        Cita.objects.filter(pk__in=[c.pk for c in citas]).update(estado='cancelada')
        AvisoDuena.objects.create(
            titulo='Citas canceladas por emergencia',
            mensaje=f"Se cancelaron {len(citas)} cita(s) de {len(lista)} clienta(s). Motivo: {motivo or 'sin detalle'}",
        )
        request.session['emergencia'] = {'n': len(citas), 'lista': lista}
        return redirect('/panel/cancelar-emergencia/?listo=1')

    # ---- Formulario ----
    request.session.pop('emergencia', None)
    return _mostrar_form(request)