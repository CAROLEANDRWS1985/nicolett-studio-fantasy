import time
from django.db.models import F
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .models import Producto, Inventario

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

TIENDA_URL = 'http://127.0.0.1:9020/venta/index#productos'


def _tx():
    # Ambiente de pruebas. Con el código real de la dueña, aquí se cambia a producción.
    return Transaction(WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST,
    ))


def _pagina(titulo, mensaje):
    return HttpResponse(
        '<html><head><meta charset="utf-8"><title>' + titulo + '</title></head>'
        '<body style="font-family:Arial,sans-serif; background:#F7F2EC; text-align:center; padding-top:120px;">'
        '<h1>' + titulo + '</h1><p>' + mensaje + '</p>'
        '<a href="' + TIENDA_URL + '" style="display:inline-block; margin-top:24px; padding:14px 28px; '
        'background:#231F1B; color:#F7F2EC; text-decoration:none;">VOLVER A LA TIENDA</a>'
        '</body></html>'
    )


def productos_publicos(request):
    datos = []
    for p in Producto.objects.filter(activo=True):
        stock = p.inventario.stock_actual if hasattr(p, 'inventario') else 0
        datos.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion or '',
            'precio': int(p.precio),
            'categoria': p.categoria or '',
            'stock': stock,
            'imagen': request.build_absolute_uri(p.imagen.url) if p.imagen else None,
        })
    respuesta = JsonResponse(datos, safe=False)
    respuesta['Access-Control-Allow-Origin'] = '*'
    return respuesta


def comprar_producto(request, pk):
    p = get_object_or_404(Producto, pk=pk, activo=True)
    stock = p.inventario.stock_actual if hasattr(p, 'inventario') else 0
    if stock <= 0:
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