from django.contrib import admin
from .models import Comuna, Cliente, Producto, Inventario, ServicioBelleza, Cita, Pago, Abono


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'rut', 'email', 'telefono', 'comuna', 'activo', 'fecha_registro')
    search_fields = ('nombre', 'rut', 'email')
    list_filter = ('activo', 'comuna')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'categoria', 'precio', 'activo')
    search_fields = ('nombre', 'categoria')
    list_filter = ('activo', 'categoria')


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'stock_actual', 'stock_minimo', 'actualizado')
    search_fields = ('producto__nombre',)


@admin.register(ServicioBelleza)
class ServicioBellezaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'duracion_minutos', 'precio', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'servicio', 'fecha', 'hora', 'estado')
    search_fields = ('cliente__nombre',)
    list_filter = ('estado', 'fecha')


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'cita', 'monto', 'metodo_pago', 'fecha')
    search_fields = ('cliente__nombre',)
    list_filter = ('metodo_pago', 'fecha')


@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'monto', 'motivo', 'fecha')
    search_fields = ('cliente__nombre',)