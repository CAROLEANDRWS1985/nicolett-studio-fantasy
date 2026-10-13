# Agregar en Url Principal
#   from .views_serializer import router
#   path('api/', include(router.urls)),

from django.apps import apps
from django.db import models
from rest_framework import serializers, viewsets, routers
from django.http import JsonResponse
from ventas.models import *

def create_serializer_and_viewset(modelos):
    nombre_modelo = modelos.__name__  
    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = modelos
            fields = '__all__'

    class ViewSet(viewsets.ModelViewSet):
        #print("    ViewSet",nombre_modelo)
        queryset = modelos.objects.all()
        serializer_class = Serializer

        def create(self, request, *args, **kwargs):
            #print('       Post: ' + nombre_modelo)
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({  'codigo':201
                                      ,'Mensaje':'Datos incorrectos...'
                                      ,'error':serializer.errors})

            #print('     Modelo: ' + nombre_modelo)
            self.perform_create(serializer)
            return JsonResponse({  'codigo':0
                            ,'Mensaje':'Ha sido creado...'
                            ,'error':''})

        def update(self, request, *args, **kwargs):
            #print('       Put: ' + nombre_modelo)
            instancia = self.get_object()
            super().update(request, *args, **kwargs)
            return JsonResponse({  'codigo':0
                            ,'Mensaje':'Actualización exitosa'
                            ,'error':''})

        def destroy(self, request, *args, **kwargs):
            #print('       Delete: ' + nombre_modelo)
            instancia = self.get_object()
            super().destroy(request, *args, **kwargs)
            return JsonResponse({  'codigo':0
                            ,'Mensaje':'Eliminación exitosa'
                            ,'error':''})
        
    #print("    return ViewSet",nombre_modelo)
    return ViewSet


def get_dynamic_viewsets():
    # Lista de nombres de modelos a excluir
    excluded_models = ['LogEntry','Permission','Group','User','ContentType','Session',]
    viewsets_dict = {}
    for model in apps.get_models():
        if issubclass(model, models.Model) and not model.__name__ in excluded_models:
            #print(model.__name__)
            viewset_class = create_serializer_and_viewset(model)
            viewsets_dict[model.__name__.lower()] = viewset_class
    return viewsets_dict

def crear_view_serial():
    dynamic_viewsets = get_dynamic_viewsets()
    for model_name, viewset in dynamic_viewsets.items():
         router.register(model_name, viewset)

router = routers.DefaultRouter()
crear_view_serial()