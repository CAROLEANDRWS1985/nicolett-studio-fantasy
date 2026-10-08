# RestFull Con Simples Métodos
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .serializers import RegionSerializer,PersonaSerializer
from .models import Region,Persona,Comuna

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

def rf_harrys(request):
    return HttpResponse("harrysito es el mas pulento")

#https://gist.github.com/juque/465814
@csrf_exempt
def rf_load_region(request):
    data = JSONParser().parse(request)
    #print("data",data)
    registro = RegionSerializer(data=data)
    if registro.is_valid():
        registro.save()
        return JSONResponse(registro.data, status=201)
    
    ##  Ya Existe
    registroUpd = Region.objects.filter(codigo=data['codigo'])
    if registroUpd.count() > 0:
        #print("registro sii",registroUpd)
        registroUpd[0].nombre=data['nombre']
        registroUpd[0].save()
        return JSONResponse(registro.data, status=201)    
        
    print(registro.errors)    
    return JSONResponse(registro.errors, status=400)             
     
@csrf_exempt
def rf_region(request):
    if request.method == 'GET':
         registro = Region.objects.all()
         serializer = RegionSerializer(registro, many=True)
         return JSONResponse(serializer.data)

    elif request.method == 'POST':
         data = JSONParser().parse(request)
         print("data",data)
         registro = RegionSerializer(data=data)
         #print("registro",registro)
         if registro.is_valid():
              registro.save()
              return JSONResponse(registro.data, status=201)
         
    return JSONResponse(registro.errors, status=400) 

@csrf_exempt
def rf_region_pk(request,cod_region):
    try:
        print("cod_region",cod_region)
        registro = Region.objects.get(pk=cod_region)
    except Region.DoesNotExist:
        return HttpResponse(status=408)

    ##   Ya lei el registros
    if request.method == 'GET':
        # region = Region.objects.get(pk=cod_region) #ya lo lei antes
        registro = RegionSerializer(registro)
        return JSONResponse(registro.data)

    elif request.method == 'PUT':
        # region = Region.objects.get(pk=cod_region) #ya lo lei antes
        data = JSONParser().parse(request)
        registro = RegionSerializer(registro, data=data)
        if registro.is_valid():
            registro.save()
            return JSONResponse(registro.data)

    elif request.method == 'DELETE':
        # region = Region.objects.get(pk=cod_region) #ya lo lei antes
        registro.delete()
        return HttpResponse(status=204)
        

    return JSONResponse(registro.errors, status=400) 

"""
{ "ok": true,
  "rows": 1,
  "msg"  :"Mensaje de Error"
  "codErr": "ORA-1010"
  "reg":  {
        "idRegion": 1,
        "codigo": "1harrys ta",
        "nombre": "Region Metropolina"
    }
}
"""    