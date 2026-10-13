#pip install zeep

from zeep import Client

client = Client('http://localhost:9010/ventas/soap_service_persona/?WSDL')
#result = client.service.PersonaLeerTodos(100, 'kilometersPerhour', 'milesPerhour')
result = client.service.personaLeerTodos()

print(result)