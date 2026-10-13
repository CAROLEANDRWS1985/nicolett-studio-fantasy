from django.shortcuts import render
from ventas.models import *

# Create your views here.


def index(request):
    registros = Productos.objects.all()
    datos = {'harrys_prod':registros
             ,'msg':"Hola como estas, Yo Buen?"
             ,'msgHarrys':"Eres Puletno"
             }
    print("produc",registros)
    return render(request, 'index.html',datos)