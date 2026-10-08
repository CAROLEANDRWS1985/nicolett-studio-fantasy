# RestFull Basado en Clases
# https://www.django-rest-framework.org/tutorial/3-class-based-views/

from django.shortcuts import render
from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import *
from .serializers import *

# --- FUNCIONES DE RESPUESTA QUE YA TENÍAS (Mantenidas por seguridad) ---
class JSONResponseOkRows(HttpResponse):
    def __init__(self, data, msg, **kwargs):
        data = {"OK": True, "count": len(data), "registro": data, "msg": msg}
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponseOkRows, self).__init__(content, **kwargs)

class JSONResponseOk(HttpResponse):
    def __init__(self, data, msg, **kwargs):
        data = {"OK": True, "count": "1", "registro": data, "msg": msg}
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponseOk, self).__init__(content, **kwargs)

# --- NUEVOS VIEWSETS PARA EL ESTUDIO JURÍDICO ---

class AreaPracticaViewSet(viewsets.ModelViewSet):
    queryset = AreaPractica.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AreaPracticaSerializer

class ServicioLegalViewSet(viewsets.ModelViewSet):
    queryset = ServicioLegal.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ServicioLegalSerializer

class CitaLegalViewSet(viewsets.ModelViewSet):
    queryset = CitaLegal.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = CitaLegalSerializer

class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = PersonaSerializer