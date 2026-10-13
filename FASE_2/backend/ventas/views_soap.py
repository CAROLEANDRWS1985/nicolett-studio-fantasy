
#  SOAP
#  https://ducminhgd.wordpress.com/2017/09/17/create-soap-web-service-with-django/
#  https://www.youtube.com/watch?v=yK1ZQ9O3RVg
from rest_framework.views import APIView

from django.views.decorators.csrf import csrf_exempt
from spyne.application import Application
from spyne.decorator import rpc
from spyne.model.primitive import Unicode, Integer, String
from spyne.model.complex import Iterable
from spyne.protocol.soap import Soap11
from spyne.server.django import DjangoApplication
from spyne.service import ServiceBase
from spyne.util.django import DjangoComplexModel

from .models import Region,Persona,Comuna

# http://127.0.0.1:9010/ventas/soap_service/
# http://127.0.0.1:9010/ventas/soap_service/?WSDL
class SoapService(ServiceBase):
    @rpc(Unicode(nillable=False), _returns=Unicode)
    def hello(ctx, name):
        return 'Hello, {}'.format(name)

    @rpc(Integer(nillable=False), Integer(nillable=False), _returns=Integer)
    def sum(ctx, a, b):
        return int(a + b)


soap_app = Application(
    [SoapService],
    tns='django.soap.example',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(),
)

django_soap_application = DjangoApplication(soap_app)
my_soap_application = csrf_exempt(django_soap_application)
##########################################
# pruebas Soap 222
class SoapServiceHarrys(ServiceBase):
    @rpc(Unicode(nillable=False), _returns=Unicode)
    def harrysHola(ctx, nombre):
        return 'Hola Profesor, {}'.format(nombre)

    @rpc(Integer(nillable=False), Integer(nillable=False), Integer(nillable=False), _returns=Integer)
    def harrysSuma(ctx, a, b, c):
        return int(a + b + c)
    
    @rpc(String, Integer, _returns=Iterable(String))
    def repetirHola(ctx,name, times):
        for i in range(times):
            yield 'Harrys Dice Hola a , %s' % name    

soap_app_harrys = Application(
    [SoapServiceHarrys],
    tns='django.soap.example',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(),
)

django_soap_harrys = DjangoApplication(soap_app_harrys)
pruebaHarrys = csrf_exempt(django_soap_harrys)


####  Consumir
from suds.client import Client
from suds.cache import NoCache
class SoapList(APIView):
    def get(self, request, format=None):
        my_client = Client('http://127.0.0.1:8000/ventas/soap_service/?WSDL', cache=NoCache())
        print("WSDL Metodos : ", my_client)
        stResult = 'Function hello: ' +  str(my_client.service.hello('Harrys el magnifico'))
        stResult = stResult + '<br>'+ 'Function sum: ' + str(my_client.service.sum(10, 25))
        return HttpResponse(stResult) # type: ignore

################################################################
# https://github.com/arskom/spyne/blob/master/doc/source/manual/05-03_django.rst
# https://snyk.io/advisor/python/spyne/functions/spyne.protocol.http.HttpRpc


class TodoListPersona(DjangoComplexModel):
    class Attributes(DjangoComplexModel.Attributes):
        django_model = Persona


class SoapServicePersona(ServiceBase):
    #se crean los 4 metodos

    @rpc(Unicode(nillable=False), Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Integer(nillable=False),_returns=Unicode)
    def personaCrear(ctx,rut,nombre,ap_paterno,ap_materno,mail,fechaNacimiento,idComuna):
        registro = Persona()
        registro.rut = rut
        registro.nombre = nombre
        registro.papellido = ap_paterno
        registro.sapellido = ap_materno
        registro.email = mail
        #registro.fechaNacimiento = fechaNacimiento
        comuna = Comuna()
        comuna.idComuna=idComuna
        registro.comuna= comuna
        registro.save()
        return 'Soap Creado : '+ rut
    
    @rpc(Unicode(nillable=False), Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Unicode(nillable=False),Integer(nillable=False),_returns=Unicode)
    def personaActualizar(ctx,rut,nombre,ap_paterno,ap_materno,mail,fechaNacimiento,idComuna):
        registro = Persona.objects.get(pk=rut)
        registro.nombre = nombre
        registro.papellido = ap_paterno
        registro.sapellido = ap_materno
        registro.email = mail
        #registro.fechaNacimiento = fechaNacimiento
        #registro.idComuna = idComuna
        registro.save()
        return 'Registro Actualizado : '+ rut

    @rpc(Integer(nillable=False),_returns=TodoListPersona)
    def personaLeer(ctx,rut):
        registro = Persona.objects.get(pk=rut)
        return registro

    @rpc(_returns=Iterable(TodoListPersona))
    def personaLeerTodos(ctx):
        registro = Persona.objects.all()
        return registro

    @rpc(Unicode(nillable=False),_returns=Unicode)
    def personaEliminar(ctx,rut):
        registro = Persona.objects.get(pk=rut)
        registro.delete()
        return 'Soap '+ rut + " Eliminado"
    

soap_app_persona = Application(
    [SoapServicePersona],
    tns='django.soap.example',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(),
)

django_soap_persona = DjangoApplication(soap_app_persona)
crud_persona = csrf_exempt(django_soap_persona)
#http://localhost:9010/ventas/soap_service_persona/?WSDL








# class Venta(APIView):

#     def post(self, request, format=None):
#         data = JSONParser().parse(request)
#         rut = data['rut']
#         nombre = data['nombre']
#         if (not existe_cliente):
#             creo cliente
#             creo Persona
#             creo usuario
        
#         productos = data['productos']
#         for x in productos.len:
#              codigo = productos['codigo']
#              cantidad = productos['cantidad']
#              cantidad = productos['total']
#              #grabar en la tabla venta
#              #Descontar Stock Bodega y el producto
#              return JSONResponse(registro.data, status=status.HTTP_201_CREATED)
#         return JSONResponse(registro.errors, status=status.HTTP_400_BAD_REQUEST)