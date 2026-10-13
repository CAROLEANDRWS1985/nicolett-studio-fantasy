#pip install Suds
####  Consumir
from rest_framework.views import APIView
from suds.client import Client
from suds.cache import NoCache
from django.http import HttpResponse
class SoapList(APIView):
    def get(self, request, format=None):
        my_client = Client('http://127.0.0.1:8000/ventas/soap_service/?WSDL', cache=NoCache())
        print("WSDL Metodos : ", my_client)
        stResult = 'Function hello: ' +  str(my_client.service.hello('Harrys el magnifico'))
        stResult = stResult + '<br>'+ 'Function sum: ' + str(my_client.service.sum(10, 25))
        return HttpResponse(stResult)
