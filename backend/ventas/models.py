from datetime import date
from django.db import models
from django.contrib.auth.models import User


class Comuna(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    # NUEVO: vincula la ficha con el usuario que inicia sesión (portal "Mi cuenta")
    usuario = models.OneToOneField(User, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='cliente')
    # Colaborador (profesional del salón) que atiende a la clienta
    profesional = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name='clientas_atendidas', verbose_name='Colaborador')
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name='Fecha de cumpleaños')
    comuna = models.ForeignKey(Comuna, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Inventario(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='inventario')
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.producto.nombre} - Stock: {self.stock_actual}"


class ServicioBelleza(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    duracion_minutos = models.PositiveIntegerField(default=30)
    # Precio "desde". Si el servicio tiene tallas, es igual al precio de la talla S.
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # NUEVO: precios por largo de cabello (vacíos si el servicio tiene precio único)
    precio_s = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   # hasta hombros
    precio_m = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   # hasta axila
    precio_l = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   # hasta codo
    precio_xl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # bajo codo
    activo = models.BooleanField(default=True)

    @property
    def tiene_tallas(self):
        return self.precio_s is not None

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('atendida', 'Atendida'),
        ('cancelada', 'Cancelada'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='citas')
    servicio = models.ForeignKey(ServicioBelleza, on_delete=models.SET_NULL, blank=True, null=True)
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    notas = models.TextField(blank=True, null=True)
    # NUEVO: colaboradora que atiende la cita (si queda vacío, se toma la colaboradora de la clienta)
    profesional = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name='citas_asignadas', verbose_name='Colaborador')
    creado = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # NUEVO: si la cita no tiene colaboradora, se le asigna la de la clienta
        if self.profesional_id is None and self.cliente_id:
            prof = Cliente.objects.filter(pk=self.cliente_id).values_list('profesional', flat=True).first()
            if prof:
                self.profesional_id = prof
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente.nombre} - {self.fecha} {self.hora}"


class Pago(models.Model):
    METODOS = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Débito'),
        ('credito', 'Crédito'),
        ('transferencia', 'Transferencia'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.SET_NULL, blank=True, null=True, related_name='pagos')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS, default='efectivo')
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.monto} - {self.cliente.nombre}"


class Abono(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='abonos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=200, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Abono {self.monto} - {self.cliente.nombre}"


# NUEVO: avisos para la dueña (cuando una clienta agenda o cancela)
class AvisoDuena(models.Model):
    titulo = models.CharField(max_length=120)
    mensaje = models.TextField(blank=True)
    cita = models.ForeignKey(Cita, null=True, blank=True, on_delete=models.SET_NULL)
    leido = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['leido', '-creado']   # los no leídos primero

    def __str__(self):
        return self.titulo


class DiaBloqueado(models.Model):
    fecha = models.DateField(unique=True)
    motivo = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"{self.fecha} - {self.motivo or 'Sin atención'}"


# NUEVO: registro de lo que se le hizo a cada clienta
class Atencion(models.Model):
    ACOMPANANTE = [
        ('sola', 'Vino sola'),
        ('con_hijo', 'Vino con hijo/a'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='atenciones')
    cita = models.ForeignKey(Cita, on_delete=models.SET_NULL, blank=True, null=True,
                             related_name='atenciones')
    fecha = models.DateField(default=date.today)
    servicio = models.ForeignKey(ServicioBelleza, on_delete=models.SET_NULL, blank=True, null=True)
    profesional = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name='atenciones_realizadas', verbose_name='Colaborador')
    monto_cobrado = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    acompanante = models.CharField(max_length=10, choices=ACOMPANANTE, default='sola',
                                   verbose_name='Vino')
    notas = models.TextField(blank=True, null=True)
    recordatorio_enviado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado']

    def __str__(self):
        return f"{self.cliente.nombre} - {self.fecha}"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='atenciones')
    cita = models.ForeignKey(Cita, on_delete=models.SET_NULL, blank=True, null=True,
                             related_name='atenciones')
    fecha = models.DateField(default=date.today)
    servicio = models.ForeignKey(ServicioBelleza, on_delete=models.SET_NULL, blank=True, null=True)
    profesional = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name='atenciones_realizadas', verbose_name='Colaborador')
    monto_cobrado = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    acompanante = models.CharField(max_length=10, choices=ACOMPANANTE, default='sola',
                                   verbose_name='Vino')
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado']

    def __str__(self):
        return f"{self.cliente.nombre} - {self.fecha}"

    

# ===================== PROVEEDORES =====================

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    rut = models.CharField(max_length=15, blank=True, verbose_name='RUT')
    contacto = models.CharField(max_length=150, blank=True, verbose_name='Persona de contacto')
    telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    correo = models.EmailField(blank=True, verbose_name='Correo')
    notas = models.TextField(blank=True, verbose_name='Notas')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre


class CompraProveedor(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT,
                                  related_name='compras', verbose_name='Proveedor')
    fecha = models.DateField(default=date.today, verbose_name='Fecha de compra')
    documento = models.CharField(max_length=50, blank=True, verbose_name='N° factura o boleta')
    monto = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Monto total')
    nota = models.TextField(verbose_name='Qué se compró')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Compra a proveedor'
        verbose_name_plural = 'Compras a proveedores'

    def __str__(self):
        return f"{self.proveedor.nombre} - {self.fecha}"


# ===================== HORARIO DEL EQUIPO (NUEVO) =====================

class HorarioColaboradora(models.Model):
    DIAS = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
        (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    colaborador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='horarios',
                                    verbose_name='Colaborador')
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS, verbose_name='Día')
    hora_entrada = models.TimeField(verbose_name='Entrada')
    hora_salida = models.TimeField(verbose_name='Salida')

    class Meta:
        ordering = ['colaborador', 'dia_semana']
        unique_together = [('colaborador', 'dia_semana')]
        verbose_name = 'Horario de colaboradora'
        verbose_name_plural = 'Horarios de colaboradoras'

    def __str__(self):
        return f"{self.colaborador} - {self.get_dia_semana_display()} {self.hora_entrada:%H:%M}-{self.hora_salida:%H:%M}"


class DiaLibreColaboradora(models.Model):
    colaborador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dias_libres',
                                    verbose_name='Colaborador')
    fecha = models.DateField(verbose_name='Fecha')
    motivo = models.CharField(max_length=150, blank=True, verbose_name='Motivo')

    class Meta:
        ordering = ['fecha']
        unique_together = [('colaborador', 'fecha')]
        verbose_name = 'Día libre de colaboradora'
        verbose_name_plural = 'Días libres de colaboradoras'

    def __str__(self):
        return f"{self.colaborador} - {self.fecha} ({self.motivo or 'Libre'})"

    

# ===================== VENTAS DE LA TIENDA (NUEVO) =====================

class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name='ventas', verbose_name='Clienta')
    nombre_cliente = models.CharField(max_length=150, blank=True, verbose_name='Nombre')
    email = models.EmailField(blank=True, verbose_name='Correo')
    orden_compra = models.CharField(max_length=50, unique=True, verbose_name='Orden de compra')
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Total')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        return f"Venta {self.orden_compra} - {self.nombre_cliente or 'Sin nombre'}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, blank=True, null=True,
                                 related_name='ventas_detalle')
    nombre_producto = models.CharField(max_length=150, verbose_name='Producto')
    cantidad = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                          verbose_name='Precio unitario')

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.nombre_producto} x {self.cantidad}"