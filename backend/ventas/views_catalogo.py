from django.core.cache import cache
from .models import Producto
from .correos import enviar_boletas
import re
import time
import random
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Producto, Inventario

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from django.core.cache import cache
from .models import Producto
from .correos import enviar_boletas

TIENDA_URL = 'http://127.0.0.1:9020/venta/index#productos'
# Al volver con ?pago=ok, la tienda vacía el carrito del navegador.
TIENDA_OK_URL = 'http://127.0.0.1:9020/venta/index?pago=ok#productos'

ABONOS_VALIDOS = (5000, 10000)
_ITEM = re.compile(r'^([pa])(\d+)x(\d+)$')


def _tx():
    # Ambiente de pruebas. Con el código real de la dueña, aquí se cambia a producción.
    return Transaction(WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST,
    ))


def _pagina(titulo, mensaje, volver=TIENDA_URL):
    return HttpResponse(
        '<html><head><meta charset="utf-8"><title>' + titulo + '</title></head>'
        '<body style="font-family:Arial,sans-serif; background:#F7F2EC; text-align:center; padding-top:120px;">'
        '<h1>' + titulo + '</h1><p>' + mensaje + '</p>'
        '<a href="' + volver + '" style="display:inline-block; margin-top:24px; padding:14px 28px; '
        'background:#231F1B; color:#F7F2EC; text-decoration:none;">VOLVER A LA TIENDA</a>'
        '</body></html>'
    )


def _stock(p):
    return p.inventario.stock_actual if hasattr(p, 'inventario') else 0


def productos_publicos(request):
    datos = []
    for p in Producto.objects.filter(activo=True):
        datos.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion or '',
            'precio': int(p.precio),
            'categoria': p.categoria or '',
            'stock': _stock(p),
            'imagen': request.build_absolute_uri(p.imagen.url) if p.imagen else None,
        })
    respuesta = JsonResponse(datos, safe=False)
    respuesta['Access-Control-Allow-Origin'] = '*'
    return respuesta


# ---------- COMPRA DIRECTA DE UN PRODUCTO ----------

def comprar_producto(request, pk):
    p = get_object_or_404(Producto, pk=pk, activo=True)
    if _stock(p) <= 0:
        return _pagina('Sin stock', 'Este producto no está disponible por ahora.')

    orden = 'P' + str(p.id) + 'T' + str(int(time.time()))
    retorno = request.build_absolute_uri(reverse('webpay_producto_retorno'))
    r = _tx().create(orden, orden, int(p.precio), retorno)

    return HttpResponse(
        '<form id="f" action="' + r['url'] + '" method="post">'
        '<input type="hidden" name="token_ws" value="' + r['token'] + '"></form>'
        '<script>document.getElementById("f").submit();</script>'
    )


@csrf_exempt
def webpay_producto_retorno(request):
    datos = request.POST or request.GET
    token = datos.get('token_ws')
    if not token:
        return _pagina('Pago cancelado', 'No se realizó ningún cobro.')

    try:
        r = _tx().commit(token)
    except Exception:
        return _pagina('Pago no disponible', 'Esta transacción ya fue procesada o no es válida.')

    if r.get('status') == 'AUTHORIZED' and r.get('response_code') == 0:
        pk = int(r['buy_order'][1:].split('T')[0])
        Inventario.objects.filter(producto_id=pk, stock_actual__gt=0).update(stock_actual=F('stock_actual') - 1)
        _registrar_venta(request, r, [('p', pk, 1)])   # NUEVO: guarda la venta
        monto = '{:,}'.format(int(r['amount'])).replace(',', '.')
        return _pagina('¡Pago aprobado!', 'Monto pagado: $' + monto + '. Gracias por tu compra.')

    return _pagina('Pago rechazado', 'No se realizó ningún cobro. Puedes intentarlo de nuevo.')


# ---------- PAGO DEL CARRITO (productos + abonos) ----------

def _leer_items(texto):
    """Convierte 'p4x4,p11x3,a5000x1' en [('p', 4, 4), ('p', 11, 3), ('a', 5000, 1)]."""
    juntos = {}
    for parte in (texto or '').split(','):
        m = _ITEM.match(parte.strip())
        if not m:
            raise ValueError('item inválido')
        tipo, num, cant = m.group(1), int(m.group(2)), int(m.group(3))
        if cant < 1:
            raise ValueError('cantidad inválida')
        juntos[(tipo, num)] = juntos.get((tipo, num), 0) + cant
    if not juntos:
        raise ValueError('carrito vacío')
    return [(t, n, c) for (t, n), c in juntos.items()]


def _registrar_abono(monto, orden):
    # PENDIENTE: aquí se guarda el abono pagado y se asocia a la cita de la clienta.
    # Hoy solo se cobra; falta conectarlo con tu modelo de abonos/citas.
    pass


def _registrar_venta(request, r, items):
    """NUEVO: guarda la venta y sus productos para el historial del panel."""
    from .models import Venta, DetalleVenta, Cliente
    productos = [(num, cant) for tipo, num, cant in items if tipo == 'p']
    if not productos:
        return
    try:
        orden = str(r['buy_order'])
        if Venta.objects.filter(orden_compra=orden).exists():
            return   # ya estaba guardada (por si se recarga la página)
        datos = cache.get('compra_' + orden) or {}
        email = datos.get('email', '')
        cliente = None
        if request.user.is_authenticated:
            cliente = Cliente.objects.filter(usuario=request.user).first()
        if cliente is None and email:
            cliente = Cliente.objects.filter(email__iexact=email).first()

        venta = Venta.objects.create(
            cliente=cliente,
            nombre_cliente=datos.get('nombre', '') or (cliente.nombre if cliente else ''),
            email=email or (cliente.email if cliente and cliente.email else ''),
            orden_compra=orden,
            total=0,
        )
        total = 0
        for num, cant in productos:
            p = Producto.objects.filter(pk=num).first()
            precio = int(p.precio) if p else 0
            DetalleVenta.objects.create(
                venta=venta,
                producto=p,
                nombre_producto=p.nombre if p else 'Producto ' + str(num),
                cantidad=cant,
                precio_unitario=precio,
            )
            total += precio * cant
        venta.total = total
        venta.save(update_fields=['total'])
    except Exception as e:
        print('Error guardando la venta:', e)


def _fmt(n):
    return '$' + '{:,}'.format(int(n)).replace(',', '.')


def _datos_guardados(request):
    """Si la clienta tiene sesión, trae su nombre, teléfono y correo para dejarlos escritos."""
    nombre = telefono = email = ''
    if request.user.is_authenticated:
        email = request.user.email or ''
        nombre = request.user.get_full_name() or request.user.username
        try:
            from .models import Cliente
            c = Cliente.objects.filter(usuario=request.user).first()
            if c:
                nombre = c.nombre or nombre
                telefono = c.telefono or ''
                email = c.email or email
        except Exception:
            pass
    return nombre, telefono, email


def _formulario_datos(items_txt, resumen, total, nombre='', telefono='', email='', error=''):
    """Página que pide nombre, teléfono y correo antes de ir a Webpay."""
    filas = ''.join(
        '<tr><td>' + escape(n) + '</td><td style="text-align:center">' + str(c) + '</td>'
        '<td style="text-align:right">' + _fmt(st) + '</td></tr>'
        for n, c, st in resumen
    )
    aviso = ('<p style="background:#F8E1DC;color:#8A3B2E;padding:10px 14px;border-radius:6px;">'
             + escape(error) + '</p>') if error else ''
    campo = ('<label style="display:block;text-align:left;font-size:12px;letter-spacing:1px;'
             'margin:16px 0 6px;color:#231F1B;">{lbl}</label>'
             '<input name="{name}" type="{tipo}" value="{val}" required {extra} '
             'style="width:100%;box-sizing:border-box;padding:12px;border:1px solid #D8C3A5;'
             'border-radius:6px;font-size:15px;background:#fff;">')
    return HttpResponse(
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Tus datos para la boleta</title></head>'
        '<body style="font-family:Arial,sans-serif;background:#F7F2EC;color:#231F1B;margin:0;padding:40px 16px;">'
        '<div style="max-width:480px;margin:0 auto;background:#FFFDF9;border:1px solid #E8DCCB;'
        'border-radius:12px;padding:32px;">'
        '<h1 style="font-weight:normal;margin:0 0 6px;font-size:26px;">Tus datos para la boleta</h1>'
        '<p style="color:#6B5B4E;margin:0 0 20px;font-size:14px;">Te enviaremos la boleta a tu correo. '
        'Preséntala en la peluquería para retirar tu producto.</p>'
        + aviso +
        '<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px;">'
        '<tr style="border-bottom:1px solid #E8DCCB;"><th style="text-align:left;padding:6px 0;">Producto</th>'
        '<th>Cant.</th><th style="text-align:right">Subtotal</th></tr>' + filas +
        '<tr><td colspan="3" style="text-align:right;padding-top:10px;color:#C4867A;font-weight:bold;">'
        'Total: ' + _fmt(total) + '</td></tr></table>'
        '<form method="get" action="">'
        '<input type="hidden" name="items" value="' + escape(items_txt) + '">'
        '<input type="hidden" name="confirmar" value="1">'
        + campo.format(lbl='NOMBRE Y APELLIDO', name='nombre', tipo='text', val=escape(nombre), extra='maxlength="80"')
        + campo.format(lbl='TELÉFONO', name='telefono', tipo='tel', val=escape(telefono),
                       extra='placeholder="+56 9 1234 5678" maxlength="20"')
        + campo.format(lbl='CORREO ELECTRÓNICO', name='email', tipo='email', val=escape(email), extra='maxlength="120"') +
        '<button type="submit" style="width:100%;margin-top:24px;padding:14px;background:#231F1B;color:#F7F2EC;'
        'border:none;border-radius:6px;font-size:14px;letter-spacing:1px;cursor:pointer;">CONTINUAR AL PAGO</button>'
        '</form>'
        '<p style="text-align:center;margin-top:18px;"><a href="' + TIENDA_URL + '" '
        'style="color:#6B5B4E;font-size:13px;">Volver a la tienda</a></p>'
        '</div></body></html>'
    )


def carrito_pagar(request):
    items_txt = request.GET.get('items', '')
    try:
        items = _leer_items(items_txt)
    except ValueError:
        return _pagina('Carrito no válido', 'No pudimos leer tu carrito. Vuelve a la tienda e inténtalo de nuevo.')

    # Los precios se leen de la base de datos, nunca del navegador.
    total = 0
    resumen = []
    for tipo, num, cant in items:
        if tipo == 'a':
            if num not in ABONOS_VALIDOS or cant != 1:
                return _pagina('Abono no válido', 'Los abonos disponibles son de $5.000 y $10.000.')
            total += num
            resumen.append(('Abono a cita', 1, num))
        else:
            p = Producto.objects.filter(pk=num, activo=True).first()
            if p is None:
                return _pagina('Producto no disponible', 'Uno de los productos de tu carrito ya no está disponible.')
            stock = _stock(p)
            if cant > stock:
                return _pagina('Stock insuficiente',
                               'Solo quedan ' + str(stock) + ' unidades de ' + escape(p.nombre) + '.')
            total += int(p.precio) * cant
            resumen.append((p.nombre, cant, int(p.precio) * cant))

    # El carrito viaja en session_id (máx. 61 caracteres) y Webpay lo devuelve al confirmar.
    session_id = ','.join(t + str(n) + 'x' + str(c) for t, n, c in items)
    if len(session_id) > 61:
        return _pagina('Carrito muy grande', 'Reduce la cantidad de productos distintos e inténtalo de nuevo.')

    # Paso 1: pedir nombre, teléfono y correo (con o sin sesión).          # ← NUEVO
    if request.GET.get('confirmar') != '1':
        nombre, telefono, email = _datos_guardados(request)
        return _formulario_datos(items_txt, resumen, total, nombre, telefono, email)

    # Paso 2: revisar los datos que escribió.                              # ← NUEVO
    nombre = request.GET.get('nombre', '').strip()
    telefono = request.GET.get('telefono', '').strip()
    email = request.GET.get('email', '').strip()

    error = ''
    if len(nombre) < 2:
        error = 'Escribe tu nombre y apellido.'
    elif not (8 <= len(re.sub(r'\D', '', telefono)) <= 12):
        error = 'Escribe un teléfono válido, por ejemplo +56 9 1234 5678.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            error = 'Escribe un correo válido, por ejemplo nombre@gmail.com.'
    if error:
        return _formulario_datos(items_txt, resumen, total, nombre, telefono, email, error)

    orden = 'C' + str(int(time.time())) + str(random.randint(100, 999))

    # Guardar quién compra, para enviarle la boleta al volver de Webpay.
    cache.set('compra_' + orden, {
        'email': email,
        'nombre': nombre,
        'telefono': telefono,
    }, 60 * 60)

    retorno = request.build_absolute_uri(reverse('webpay_carrito_retorno'))
    r = _tx().create(orden, session_id, total, retorno)

    return HttpResponse(
        '<form id="f" action="' + r['url'] + '" method="post">'
        '<input type="hidden" name="token_ws" value="' + r['token'] + '"></form>'
        '<script>document.getElementById("f").submit();</script>'
    )


def _enviar_boleta_compra(request, r, items):
    """Arma la boleta con lo comprado y la envía a la clienta y a Nicolett."""
    try:
        datos = cache.get('compra_' + str(r['buy_order'])) or {}
        user = request.user if request.user.is_authenticated else None

        email = datos.get('email') or (user.email if user else '')
        nombre = datos.get('nombre') or ((user.get_full_name() or user.username) if user else 'Clienta')

        if not email:
            print('Boleta NO enviada: no se encontró el correo de la clienta')
            return

        lineas = []
        for tipo, num, cant in items:
            if tipo == 'p':
                p = Producto.objects.filter(pk=num).first()
                if p:
                    lineas.append({
                        'nombre': getattr(p, 'nombre', str(p)),
                        'descripcion': getattr(p, 'descripcion', ''),
                        'cantidad': cant,
                        'precio_unitario': int(getattr(p, 'precio', 0)),
                    })
            else:
                lineas.append({
                    'nombre': 'Abono a cita',
                    'descripcion': '',
                    'cantidad': 1,
                    'precio_unitario': int(num),
                })

        enviar_boletas(
            numero=r['buy_order'],
            cliente_nombre=nombre,
            cliente_email=email,
            items=lineas,
            cliente_telefono=datos.get('telefono', ''),   # NUEVO
        )
    except Exception as e:
        print('Error enviando boleta:', e)


def _volver(orden, defecto):
    """A dónde vuelve la clienta: a Mi cuenta si compró desde ahí, si no a la tienda."""
    datos = cache.get('compra_' + str(orden or '')) or {}
    return datos.get('volver') or defecto


@csrf_exempt
def webpay_carrito_retorno(request):
    datos = request.POST or request.GET
    token = datos.get('token_ws')
    if not token:
        return _pagina('Pago cancelado', 'No se realizó ningún cobro.',
                       _volver(datos.get('TBK_ORDEN_COMPRA'), TIENDA_URL))

    try:
        r = _tx().commit(token)
    except Exception:
        return _pagina('Pago no disponible', 'Esta transacción ya fue procesada o no es válida.')

    if r.get('status') == 'AUTHORIZED' and r.get('response_code') == 0:
        try:
            items = _leer_items(r.get('session_id'))
        except ValueError:
            items = []

        abonos = 0
        for tipo, num, cant in items:
            if tipo == 'p':
                Inventario.objects.filter(producto_id=num).update(
                    stock_actual=Greatest(F('stock_actual') - cant, Value(0))
                )
            else:
                abonos += num
        if abonos:
            _registrar_abono(abonos, r['buy_order'])

        _registrar_venta(request, r, items)         # NUEVO: guarda la venta
        _enviar_boleta_compra(request, r, items)   # ← envía la boleta

        monto = '{:,}'.format(int(r['amount'])).replace(',', '.')
        return _pagina('¡Pago aprobado!',
                       'Monto pagado: $' + monto + '. Gracias por tu compra. '
                       'Te enviamos la boleta a tu correo: preséntala en la peluquería para retirar tu producto.',
                       _volver(r['buy_order'], TIENDA_OK_URL))

    return _pagina('Pago rechazado', 'No se realizó ningún cobro. Puedes intentarlo de nuevo.',
                   _volver(r.get('buy_order'), TIENDA_URL))