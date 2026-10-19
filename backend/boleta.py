from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white

ROSA = HexColor("#C2185B")
OSCURO = HexColor("#2B2B2B")
GRIS = HexColor("#777777")
CLARO = HexColor("#FBEAF1")


def pesos(n):
    return "$" + format(int(n), ",").replace(",", ".")


def generar_boleta(datos, ruta):
    ancho, alto = A5
    c = canvas.Canvas(ruta, pagesize=A5)
    m = 30

    # Marca de agua
    c.saveState()
    c.setFillColor(HexColor("#EFEFEF"))
    c.setFont("Helvetica-Bold", 56)
    c.translate(ancho / 2, alto / 2 - 40)
    c.rotate(40)
    c.drawCentredString(0, 0, "SIMULACION")
    c.restoreState()

    # Franja superior
    c.setFillColor(ROSA)
    c.rect(0, alto - 110, ancho, 110, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(m, alto - 55, "NICOLETT STUDIO")
    c.setFont("Helvetica", 10)
    c.drawString(m, alto - 75, "Estetica y belleza")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(ancho - m, alto - 50, "BOLETA ELECTRONICA")
    c.setFont("Helvetica", 10)
    c.drawRightString(ancho - m, alto - 68, "N " + str(datos["orden"]))

    # Caja de datos
    y = alto - 130
    c.setFillColor(CLARO)
    c.roundRect(m, y - 60, ancho - 2 * m, 60, 8, stroke=0, fill=1)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 9)
    c.drawString(m + 12, y - 18, "CLIENTA")
    c.drawString(m + 12, y - 44, "FECHA")
    c.setFillColor(OSCURO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(m + 70, y - 18, datos["cliente"])
    c.drawString(m + 70, y - 44, datos["fecha"])

    # Detalle
    y = y - 90
    c.setFillColor(ROSA)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(m, y, "DETALLE")
    c.drawRightString(ancho - m, y, "MONTO")
    c.setStrokeColor(ROSA)
    c.setLineWidth(1.2)
    c.line(m, y - 6, ancho - m, y - 6)

    c.setFillColor(OSCURO)
    c.setFont("Helvetica", 11)
    servicio = datos.get("servicio", "Abono reserva de servicio")
    c.drawString(m, y - 28, servicio)
    c.drawRightString(ancho - m, y - 28, pesos(datos["monto"]))

    saldo = datos.get("saldo")
    if saldo is not None:
        c.setFillColor(GRIS)
        c.setFont("Helvetica", 9)
        c.drawString(m, y - 46, "Saldo pendiente a pagar en el local: " + pesos(saldo))

    # Total
    y = y - 80
    c.setFillColor(ROSA)
    c.roundRect(m, y - 34, ancho - 2 * m, 40, 8, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(m + 14, y - 20, "TOTAL PAGADO")
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(ancho - m - 14, y - 22, pesos(datos["monto"]))

    # Datos del pago
    y = y - 70
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(m, y, "DATOS DEL PAGO")
    c.setFont("Helvetica", 10)
    c.setFillColor(OSCURO)
    c.drawString(m, y - 18, "Medio de pago: Webpay (Transbank)")
    c.drawString(m, y - 34, "Tarjeta: **** **** **** " + datos["tarjeta"])
    c.drawString(m, y - 50, "Codigo de autorizacion: " + datos["autorizacion"])

    # Pie
    c.setStrokeColor(HexColor("#DDDDDD"))
    c.setLineWidth(0.6)
    c.line(m, 78, ancho - m, 78)
    c.setFillColor(OSCURO)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(ancho / 2, 60, "Gracias por reservar con nosotras!")
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(ancho / 2, 42, "Documento de SIMULACION - sin validez tributaria")
    c.save()