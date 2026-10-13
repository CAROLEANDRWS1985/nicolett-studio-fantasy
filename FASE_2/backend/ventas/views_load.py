import requests
from rest_framework.views import APIView
from django.http import JsonResponse
from django.apps import apps
import json
from .models import *
#https://docs.djangoproject.com/en/4.2/ref/models/meta/
class LoadData(APIView):
    def saveData(self,tabModel,dataCols):
        #print("saveData",dataCols)
        for dataRow in dataCols:
            if tabModel._meta.get_fields(include_parents=False, include_hidden=True):
                for campo in tabModel._meta.get_fields(include_parents=False, include_hidden=True):
                    if campo.is_relation and campo.name in dataRow:
                        rel_modelo = campo.related_model
                        rel_id = dataRow.pop(campo.name)
                        relacion = rel_modelo.objects.get(pk=rel_id)
                        dataRow[campo.name] = relacion

            obj = tabModel(**dataRow)
            obj.save()

    def saveUrl(self,stUrl,stDataArreglo):
        #print("saveUrl",stUrl,stDataArreglo)
        for stDataRow in stDataArreglo:
            #print("envioUrl",stUrl,stDataRow)
            response = requests.post(stUrl,json = stDataRow)

    def get(self, request, format=None):
        ###   Elimina las tablas Ordenadamente dependiendo de FK
        FormaPago.objects.all().delete()
        Cargo.objects.all().delete()
        Sucursal.objects.all().delete()
        Usuario.objects.all().delete()
        Cliente.objects.all().delete()
        Persona.objects.all().delete()
        Genero.objects.all().delete()
        Comuna.objects.all().delete()
        Provincia.objects.all().delete()
        Region.objects.all().delete()

        ##   Lee un Archivo JSON
        with open('load_data/data.json', 'r') as f:
            my_data = json.load(f)

        # Leo el modelo desde la models
        bdModel = apps.get_models()

        # Recorro cata tabla del archivo Json
        for tabla, tabAtrib in my_data.items():
            ##   Si la tabla esta dentro del models
            if tabla  in [modelo.__name__.lower() for modelo in bdModel]:
                # Rescata los campos de  la Tabla
                tabModel = next(modelo for modelo in bdModel if modelo.__name__.lower() == tabla)
                ## Inicializamos variales
                stMetodo="save"
                stUrl=""
                objData=None
                for atKey,atVal in tabAtrib.items():
                    #print("    ==>",atKey,atVal)
                    if atKey=="metodo":
                        stMetodo = atVal
                    elif atKey=="data":
                        objData = atVal
                    elif atKey=="url":
                        stUrl = atVal

                #  SAVE  ==> Graba directamente en la base de datos
                #  URL   ==> Realiza la carga por medio de una URL ( RestFull  )
                #  TEST_BLACK  ==> Realiza Pruebas de Caca negra     
                #  TEST_WHITE  ==> Realiza Pruebas de Caca blanca     
                #  TEST_URL  ==> Realiza Pruebas de Caca blanca
                if stMetodo=="SAVE":
                    self.saveData(tabModel,objData)
                elif stMetodo=="URL":
                    self.saveUrl(stUrl,objData)
                elif stMetodo=="TEST_BLACK":
                    print("Pruebas de Caja Negra")
                    #self.saveUrl(stUrl,objData)
                elif stMetodo=="TEST_WHITE":
                    print("Pruebas de Caja Blanca")
                    #self.saveUrl(stUrl,objData)

        return JsonResponse({'Resultados': "Datos Cargados"})


