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


def carrito_pagar(request):
    try:
        items = _leer_items(request.GET.get('items', ''))
    except ValueError:
        return _pagina('Carrito no válido', 'No pudimos leer tu carrito. Vuelve a la tienda e inténtalo de nuevo.')

    # Los precios se leen de la base de datos, nunca del navegador.
    total = 0
    for tipo, num, cant in items:
        if tipo == 'a':
            if num not in ABONOS_VALIDOS or cant != 1:
                return _pagina('Abono no válido', 'Los abonos disponibles son de $5.000 y $10.000.')
            total += num
        else:
            p = Producto.objects.filter(pk=num, activo=True).first()
            if p is None:
                return _pagina('Producto no disponible', 'Uno de los productos de tu carrito ya no está disponible.')
            stock = _stock(p)
            if cant > stock:
                return _pagina('Stock insuficiente',
                               'Solo quedan ' + str(stock) + ' unidades de ' + escape(p.nombre) + '.')
            total += int(p.precio) * cant

    # El carrito viaja en session_id (máx. 61 caracteres) y Webpay lo devuelve al confirmar.
    session_id = ','.join(t + str(n) + 'x' + str(c) for t, n, c in items)
    if len(session_id) > 61:
        return _pagina('Carrito muy grande', 'Reduce la cantidad de productos distintos e inténtalo de nuevo.')

    orden = 'C' + str(int(time.time())) + str(random.randint(100, 999))

    # Guardar quién compra, para enviarle la boleta al volver de Webpay          # ← NUEVO
    print('Compra iniciada por:', request.user)                                   # ← NUEVO
    if request.user.is_authenticated:                                             # ← NUEVO
        email_clienta = request.user.email                                        # ← NUEVO
        nombre_clienta = request.user.get_full_name() or request.user.username    # ← NUEVO
    else:                                                                         # ← NUEVO
        email_clienta = request.GET.get('email', '')                              # ← NUEVO
        nombre_clienta = request.GET.get('nombre', '') or 'Clienta'               # ← NUEVO
    if email_clienta:                                                             # ← NUEVO
        cache.set('compra_' + orden, {                                            # ← NUEVO
            'email': email_clienta,                                               # ← NUEVO
            'nombre': nombre_clienta,                                             # ← NUEVO
        }, 60 * 60)                                                               # ← NUEVO

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
        )
    except Exception as e:
        print('Error enviando boleta:', e)


@csrf_exempt
def webpay_carrito_retorno(request):
    datos = request.POST or request.GET
    token = datos.get('token_ws')
    if not token:
        return _pagina('Pago cancelado', 'No se realizó ningún cobro.')

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

        _enviar_boleta_compra(request, r, items)   # ← envía la boleta

        monto = '{:,}'.format(int(r['amount'])).replace(',', '.')
        return _pagina('¡Pago aprobado!', 'Monto pagado: $' + monto + '. Gracias por tu compra.', TIENDA_OK_URL)

    return _pagina('Pago rechazado', 'No se realizó ningún cobro. Puedes intentarlo de nuevo.')