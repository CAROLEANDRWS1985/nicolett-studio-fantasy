from rest_framework import serializers
from .models import Comuna, Cliente, Producto, Inventario, ServicioBelleza, Cita, Pago, Abono


class ComunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comuna
        fields = '__all__'


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'


class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields = '__all__'


class ServicioBellezaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicioBelleza
        fields = '__all__'


class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = '__all__'


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'


class AbonoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abono
        fields = '__all__'