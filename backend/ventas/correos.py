from io import BytesIO

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from xhtml2pdf import pisa


def clp(valor):
    """1990 -> $1.990"""
    return '$' + f'{int(valor):,}'.replace(',', '.')


def _pdf(html):
    """Convierte el HTML de la boleta en un PDF."""
    salida = BytesIO()
    pisa.CreatePDF(html, dest=salida, encoding='utf-8')
    return salida.getvalue()


def _enviar(asunto, destinatario, html, nombre_pdf, pdf):
    msg = EmailMultiAlternatives(
        subject=asunto,
        body=strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    msg.attach_alternative(html, 'text/html')
    msg.attach(nombre_pdf, pdf, 'application/pdf')
    msg.send()


def enviar_boletas(numero, cliente_nombre, cliente_email, items, metodo_pago='Webpay'):
    """
    items: lista de dicts con nombre, descripcion, cantidad, precio_unitario.
    - A la clienta: su boleta en el correo + PDF adjunto.
    - A Nicolett: aviso de la venta con el detalle + PDF del duplicado adjunto.
    """
    filas, total = [], 0
    for it in items:
        subtotal = it['cantidad'] * it['precio_unitario']
        total += subtotal
        filas.append({
            **it,
            'precio_fmt': clp(it['precio_unitario']),
            'subtotal_fmt': clp(subtotal),
        })

    neto = round(total / 1.19)
    contexto = {
        'numero': numero,
        'fecha': timezone.localtime().strftime('%d-%m-%Y %H:%M'),
        'cliente_nombre': cliente_nombre,
        'cliente_email': cliente_email,
        'items': filas,
        'neto_fmt': clp(neto),
        'iva_fmt': clp(total - neto),
        'total_fmt': clp(total),
        'metodo_pago': metodo_pago,
    }

    boleta_clienta = render_to_string('emails/boleta.html', {**contexto, 'es_copia': False})
    boleta_duplicado = render_to_string('emails/boleta.html', {**contexto, 'es_copia': True})
    aviso_nicolett = render_to_string('emails/aviso_nicolett.html', contexto)

    # 1) Clienta
    _enviar(
        f'Tu boleta N° {numero} · Nicolett Studio Fantasy',
        cliente_email,
        boleta_clienta,
        f'boleta_{numero}.pdf',
        _pdf(boleta_clienta),
    )

    # 2) Nicolett (dueña)
    _enviar(
        f'Nueva venta N° {numero} · {cliente_nombre}',
        settings.NICOLETT_EMAIL,
        aviso_nicolett,
        f'boleta_{numero}_duplicado.pdf',
        _pdf(boleta_duplicado),
    )