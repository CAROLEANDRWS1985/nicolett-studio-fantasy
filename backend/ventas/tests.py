from django.test import TestCase
from .models import *
import requests

# Pruebas Caja Blanca Caja Negra
# Create your tests here.
# https://developer.mozilla.org/es/docs/Learn/Server-side/Django/Testing

class PersonaClass(TestCase):
    stUrlGen=f'http://localhost:9010/ventas/backend/'
    @classmethod
    def setUpTestData(cls):
        print("Se Ejecuta Solo Una Vez")
        pass

    def setUp(self):
        print("Se Ejecuta Por Cada Método *****************")
        pass

    # def test_insert(self):
    #     stUrl= self.stUrlGen + 'region/'
    #     response = requests.post(stUrl,{})
    #     print("Method response: ",response)
    #     self.assertEquals(response,'died')

    def test_getBD(self):
        registro=Persona.objects.get(pk=1)
        #registro=Persona.objects.filter()
        #registro=Persona.objects.all()
        print(registro)
        #Esto también fallará si la urlconf no está definida.
        #self.assertEquals(author.get_absolute_url(),'/catalog/author/1')        
        self.assertFalse(False)

    # def test_getOne(self):
    #     stUrl= self.stUrlGen + 'persona/1'
    #     response = requests.get(stUrl)
    #     print("Method Get: ",response.content)
    #     self.assertEqual(response.status_code, 200)

    # def test_false_is_true(self):
    #     print("Method: test_false_is_true.")
    #     self.assertTrue(False)

    # def test_one_plus_one_equals_two(self):
    #     print("Method: test_one_plus_one_equals_two.")
    #     self.assertEqual(1 + 1, 2)


    # self.assertEquals(field_label,'died')
    # self.assertEquals(max_length,100)