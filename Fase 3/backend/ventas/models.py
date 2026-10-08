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
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
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
    creado = models.DateTimeField(auto_now_add=True)

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