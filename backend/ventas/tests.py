
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from backend import views
from ventas.models import (
    Comuna, Cliente, Producto, Inventario, ServicioBelleza, Cita, Pago,
    Abono, AvisoDuena, DiaBloqueado, Atencion,
)


def crear_equipo(username="equipo"):
    return User.objects.create_user(username=username, password="clave12345", is_staff=True)


def crear_clienta_usuario(username="clienta"):
    return User.objects.create_user(username=username, password="clave12345")


def llamar_vista(vista, usuario):
    """Llama a una vista directamente, sin depender de las rutas."""
    request = RequestFactory().get("/prueba/")
    request.user = usuario
    return vista(request)


# ======================================================================
# MODELOS
# ======================================================================
class ModelosTests(TestCase):
    def setUp(self):
        self.comuna = Comuna.objects.create(nombre="Providencia")
        self.cliente = Cliente.objects.create(nombre="Ana PÃ©rez", rut="123456789",
                                              telefono="912345678", comuna=self.comuna)
        self.servicio = ServicioBelleza.objects.create(nombre="Corte", precio=10000)

    def test_str_comuna(self):
        self.assertEqual(str(self.comuna), "Providencia")

    def test_str_cliente(self):
        self.assertEqual(str(self.cliente), "Ana PÃ©rez")

    def test_cliente_activo_por_defecto(self):
        self.assertTrue(self.cliente.activo)

    def test_rut_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cliente.objects.create(nombre="Otra", rut="123456789")

    def test_producto_precio_por_defecto_y_str(self):
        p = Producto.objects.create(nombre="Shampoo")
        self.assertEqual(p.precio, 0)
        self.assertTrue(p.activo)
        self.assertEqual(str(p), "Shampoo")

    def test_inventario_str(self):
        p = Producto.objects.create(nombre="Shampoo")
        inv = Inventario.objects.create(producto=p, stock_actual=5, stock_minimo=2)
        self.assertEqual(str(inv), "Shampoo - Stock: 5")

    def test_servicio_sin_tallas(self):
        self.assertFalse(self.servicio.tiene_tallas)
        self.assertEqual(self.servicio.duracion_minutos, 30)

    def test_servicio_con_tallas(self):
        s = ServicioBelleza.objects.create(nombre="Tinte", precio=20000, precio_s=20000,
                                           precio_m=25000, precio_l=30000, precio_xl=35000)
        self.assertTrue(s.tiene_tallas)

    def test_cita_estado_pendiente_por_defecto(self):
        c = Cita.objects.create(cliente=self.cliente, servicio=self.servicio,
                                fecha=date.today(), hora=time(10, 0))
        self.assertEqual(c.estado, "pendiente")
        self.assertIn("Ana PÃ©rez", str(c))

    def test_borrar_cliente_borra_sus_citas(self):
        Cita.objects.create(cliente=self.cliente, fecha=date.today(), hora=time(10, 0))
        self.cliente.delete()
        self.assertEqual(Cita.objects.count(), 0)

    def test_borrar_servicio_no_borra_la_cita(self):
        c = Cita.objects.create(cliente=self.cliente, servicio=self.servicio,
                                fecha=date.today(), hora=time(10, 0))
        self.servicio.delete()
        c.refresh_from_db()
        self.assertIsNone(c.servicio)

    def test_pago_y_abono(self):
        pago = Pago.objects.create(cliente=self.cliente, monto=Decimal("15000"))
        abono = Abono.objects.create(cliente=self.cliente, monto=Decimal("5000"), motivo="Reserva")
        self.assertEqual(pago.metodo_pago, "efectivo")
        self.assertEqual(str(pago), "Pago 15000 - Ana PÃ©rez")
        self.assertEqual(str(abono), "Abono 5000 - Ana PÃ©rez")

    def test_aviso_duena_no_leidos_primero(self):
        leido = AvisoDuena.objects.create(titulo="Viejo", leido=True)
        nuevo = AvisoDuena.objects.create(titulo="Nuevo", leido=False)
        self.assertEqual(list(AvisoDuena.objects.all()), [nuevo, leido])

    def test_dia_bloqueado_fecha_unica(self):
        DiaBloqueado.objects.create(fecha=date(2026, 12, 25), motivo="Navidad")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DiaBloqueado.objects.create(fecha=date(2026, 12, 25))

    def test_dia_bloqueado_str_sin_motivo(self):
        d = DiaBloqueado.objects.create(fecha=date(2026, 12, 24))
        self.assertIn("Sin aten", str(d))

    def test_atencion_valores_por_defecto(self):
        a = Atencion.objects.create(cliente=self.cliente)
        self.assertEqual(a.fecha, date.today())
        self.assertEqual(a.acompanante, "sola")
        self.assertFalse(a.recordatorio_enviado)
        self.assertEqual(a.monto_cobrado, 0)


# ======================================================================
# FUNCIONES AUXILIARES
# ======================================================================
class AuxiliaresTests(TestCase):
    def test_telefono_nueve_digitos(self):
        self.assertEqual(views._telefono_wa("912345678"), "56912345678")

    def test_telefono_ocho_digitos(self):
        self.assertEqual(views._telefono_wa("12345678"), "56912345678")

    def test_telefono_con_prefijo_56(self):
        self.assertEqual(views._telefono_wa("+56 9 1234 5678"), "56912345678")

    def test_telefono_vacio_o_invalido(self):
        self.assertEqual(views._telefono_wa(None), "")
        self.assertEqual(views._telefono_wa("123"), "")

    def test_formato_clp(self):
        self.assertEqual(views.formato_clp(15000), "$15.000")
        self.assertEqual(views.formato_clp(1250000), "$1.250.000")


# ======================================================================
# PERMISOS DEL PANEL (la clienta recibe 403, el equipo entra)
# ======================================================================
class PermisosPanelTests(TestCase):
    VISTAS = [
        views.panel_administrativo,
        views.admin_dashboard,
        views.admin_servicios,
        views.admin_usuarios,
        views.admin_citas_hoy,
        views.admin_precios_promos,
        views.recordatorios,
    ]

    def setUp(self):
        self.equipo = crear_equipo()
        self.clienta = crear_clienta_usuario()

    def test_clienta_recibe_403_en_todas_las_vistas(self):
        for vista in self.VISTAS:
            with self.subTest(vista=vista.__name__):
                with self.assertRaises(PermissionDenied):
                    llamar_vista(vista, self.clienta)

    def test_anonimo_es_enviado_al_login(self):
        for vista in self.VISTAS:
            with self.subTest(vista=vista.__name__):
                resp = llamar_vista(vista, AnonymousUser())
                self.assertEqual(resp.status_code, 302)
                self.assertTrue(resp.url.startswith("/segur/login/"))

    def test_equipo_entra_a_todas_las_vistas(self):
        for vista in self.VISTAS:
            with self.subTest(vista=vista.__name__):
                resp = llamar_vista(vista, self.equipo)
                self.assertEqual(resp.status_code, 200)

    def test_superusuario_tambien_entra(self):
        admin = User.objects.create_superuser("jefa", "j@x.cl", "clave12345")
        resp = llamar_vista(views.admin_dashboard, admin)
        self.assertEqual(resp.status_code, 200)


# ======================================================================
# EDICIÃ“N DE PRECIOS
# ======================================================================
class PreciosTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_equipo())
        self.url = reverse("admin_precios_promos")
        self.simple = ServicioBelleza.objects.create(nombre="Corte", precio=10000)
        self.tallas = ServicioBelleza.objects.create(
            nombre="Tinte", precio=20000, precio_s=20000, precio_m=25000,
            precio_l=30000, precio_xl=35000)

    def test_guardar_precio_simple(self):
        self.client.post(self.url, {"servicio_id": self.simple.pk, "nombre": "Corte Pro",
                                    "precio": "12000"})
        self.simple.refresh_from_db()
        self.assertEqual(self.simple.precio, 12000)
        self.assertEqual(self.simple.nombre, "Corte Pro")

    def test_precio_negativo_se_rechaza(self):
        self.client.post(self.url, {"servicio_id": self.simple.pk, "precio": "-5"})
        self.simple.refresh_from_db()
        self.assertEqual(self.simple.precio, 10000)

    def test_precio_con_letras_se_rechaza(self):
        self.client.post(self.url, {"servicio_id": self.simple.pk, "precio": "abc"})
        self.simple.refresh_from_db()
        self.assertEqual(self.simple.precio, 10000)

    def test_guardar_precios_por_talla(self):
        self.client.post(self.url, {"servicio_id": self.tallas.pk, "precio_s": "21000",
                                    "precio_m": "26000", "precio_l": "31000",
                                    "precio_xl": "36000"})
        self.tallas.refresh_from_db()
        self.assertEqual(self.tallas.precio_m, 26000)
        self.assertEqual(self.tallas.precio_xl, 36000)
        # el precio "desde" siempre es el de la talla S
        self.assertEqual(self.tallas.precio, 21000)

    def test_talla_incompleta_no_guarda_nada(self):
        self.client.post(self.url, {"servicio_id": self.tallas.pk, "precio_s": "1",
                                    "precio_m": "", "precio_l": "3", "precio_xl": "4"})
        self.tallas.refresh_from_db()
        self.assertEqual(self.tallas.precio_s, 20000)

    def test_eliminar_desactiva_el_servicio(self):
        self.client.post(self.url, {"servicio_id": self.simple.pk, "accion": "eliminar"})
        self.simple.refresh_from_db()
        self.assertFalse(self.simple.activo)

    def test_reactivar_servicio(self):
        self.simple.activo = False
        self.simple.save()
        self.client.post(self.url, {"servicio_id": self.simple.pk, "accion": "reactivar"})
        self.simple.refresh_from_db()
        self.assertTrue(self.simple.activo)

    def test_servicio_inexistente_redirige_sin_error(self):
        resp = self.client.post(self.url, {"servicio_id": 9999, "precio": "100"})
        self.assertEqual(resp.status_code, 302)

    def test_clienta_no_puede_editar_precios(self):
        self.client.force_login(crear_clienta_usuario())
        resp = self.client.post(self.url, {"servicio_id": self.simple.pk, "precio": "1"})
        self.assertEqual(resp.status_code, 403)
        self.simple.refresh_from_db()
        self.assertEqual(self.simple.precio, 10000)


# ======================================================================
# RECORDATORIOS DE 30 DÃAS
# ======================================================================
class RecordatoriosTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_equipo())
        self.url = reverse("recordatorios")
        self.hoy = timezone.localdate()
        self.cliente = Cliente.objects.create(nombre="Ana", rut="111", telefono="912345678")

    def _pendientes(self):
        return self.client.get(self.url).context["pendientes"]

    def test_atencion_de_hace_26_dias_aparece(self):
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=26))
        self.assertEqual(len(self._pendientes()), 1)

    def test_atencion_reciente_no_aparece(self):
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=10))
        self.assertEqual(len(self._pendientes()), 0)

    def test_si_la_clienta_ya_volvio_no_aparece(self):
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=2))
        self.assertEqual(len(self._pendientes()), 0)

    def test_sin_telefono_valido_no_aparece(self):
        self.cliente.telefono = ""
        self.cliente.save()
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        self.assertEqual(len(self._pendientes()), 0)

    def test_recordatorio_ya_enviado_no_aparece(self):
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28),
                                recordatorio_enviado=True)
        self.assertEqual(len(self._pendientes()), 0)

    def test_clienta_inactiva_no_aparece(self):
        self.cliente.activo = False
        self.cliente.save()
        Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        self.assertEqual(len(self._pendientes()), 0)

    def test_link_de_whatsapp_y_fecha_de_aviso(self):
        fecha = self.hoy - timedelta(days=27)
        Atencion.objects.create(cliente=self.cliente, fecha=fecha)
        item = self._pendientes()[0]
        self.assertTrue(item["link"].startswith("https://wa.me/56912345678?text="))
        self.assertEqual(item["fecha_aviso"], fecha + timedelta(days=30))

    def test_marcar_recordatorio_como_enviado(self):
        a = Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        resp = self.client.post(reverse("marcar_recordatorio", args=[a.pk]))
        self.assertEqual(resp.status_code, 302)
        a.refresh_from_db()
        self.assertTrue(a.recordatorio_enviado)
        self.assertEqual(len(self._pendientes()), 0)

    def test_marcar_recordatorio_solo_acepta_post(self):
        a = Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        resp = self.client.get(reverse("marcar_recordatorio", args=[a.pk]))
        self.assertEqual(resp.status_code, 405)
        a.refresh_from_db()
        self.assertFalse(a.recordatorio_enviado)

    def test_clienta_no_puede_marcar_recordatorios(self):
        a = Atencion.objects.create(cliente=self.cliente, fecha=self.hoy - timedelta(days=28))
        self.client.force_login(crear_clienta_usuario())
        resp = self.client.post(reverse("marcar_recordatorio", args=[a.pk]))
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertFalse(a.recordatorio_enviado)

