import time
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from backend import views
from ventas.models import Cliente, Producto, Cita, Pago, Atencion, ServicioBelleza


def llamar_vista(vista, usuario):
    request = RequestFactory().get("/prueba/")
    request.user = usuario
    return vista(request)


def medir(vista, usuario):
    """Devuelve (respuesta, segundos, cantidad de consultas a la base)."""
    with CaptureQueriesContext(connection) as ctx:
        inicio = time.perf_counter()
        resp = llamar_vista(vista, usuario)
        segundos = time.perf_counter() - inicio
    return resp, segundos, len(ctx)


class RendimientoTests(TestCase):
    """Pruebas de rendimiento con volumen alto de datos."""

    @classmethod
    def setUpTestData(cls):
        cls.equipo = User.objects.create_user("equipo", password="clave12345", is_staff=True)
        hoy = timezone.localdate()

        # 500 clientas
        Cliente.objects.bulk_create([
            Cliente(nombre="Clienta %d" % i, rut=str(10000000 + i),
                    telefono="9%08d" % i)
            for i in range(500)
        ])
        cls.clientas = list(Cliente.objects.all())

        cls.servicio = ServicioBelleza.objects.create(nombre="Corte", precio=10000)

        # 1000 citas (algunas de hoy) y 1000 pagos
        Cita.objects.bulk_create([
            Cita(cliente=cls.clientas[i % 500], servicio=cls.servicio,
                 fecha=hoy - timedelta(days=i % 20), hora="10:00",
                 estado="cancelada" if i % 10 == 0 else "pendiente")
            for i in range(1000)
        ])
        Pago.objects.bulk_create([
            Pago(cliente=cls.clientas[i % 500], monto=Decimal("10000"))
            for i in range(1000)
        ])

        # 300 productos
        Producto.objects.bulk_create([
            Producto(nombre="Producto %d" % i, precio=5000, categoria="Cat %d" % (i % 10))
            for i in range(300)
        ])

        # 200 atenciones de hace 28 dias (aparecen en recordatorios)
        Atencion.objects.bulk_create([
            Atencion(cliente=cls.clientas[i], fecha=hoy - timedelta(days=28))
            for i in range(200)
        ])

    def test_dashboard_con_mucha_informacion(self):
        resp, seg, consultas = medir(views.admin_dashboard, self.equipo)
        print("\n[Dashboard] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 2.0)
        self.assertLess(consultas, 15)

    def test_usuarios_con_500_clientas(self):
        resp, seg, consultas = medir(views.admin_usuarios, self.equipo)
        print("\n[Usuarios] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 2.0)
        # solo se detallan 10 clientas, asi que las consultas no deben crecer con las 500
        self.assertLess(consultas, 40)

    def test_citas_de_hoy_con_mucha_informacion(self):
        resp, seg, consultas = medir(views.admin_citas_hoy, self.equipo)
        print("\n[Citas hoy] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 2.0)
        self.assertLess(consultas, 10)

    def test_servicios_con_mucha_informacion(self):
        resp, seg, consultas = medir(views.admin_servicios, self.equipo)
        print("\n[Servicios] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 2.0)

    def test_panel_con_300_productos(self):
        resp, seg, consultas = medir(views.panel_administrativo, self.equipo)
        print("\n[Panel] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 3.0)

    def test_recordatorios_con_200_atenciones(self):
        resp, seg, consultas = medir(views.recordatorios, self.equipo)
        print("\n[Recordatorios] %.3f s, %d consultas" % (seg, consultas))
        self.assertEqual(resp.status_code, 200)
        self.assertLess(seg, 3.0)

    def test_busqueda_de_clienta_por_rut_entre_500(self):
        inicio = time.perf_counter()
        for i in range(100):
            Cliente.objects.get(rut=str(10000000 + i))
        seg = time.perf_counter() - inicio
        print("\n[Busqueda por RUT] 100 busquedas en %.3f s" % seg)
        self.assertLess(seg, 2.0)