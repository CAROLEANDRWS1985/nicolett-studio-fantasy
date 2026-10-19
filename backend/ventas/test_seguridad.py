from django.contrib.auth.models import User
from django.test import TestCase, Client

from ventas.models import Cliente, Producto, ServicioBelleza

CLAVE = "clave12345"
LOGIN = "/segur/login/"

# Rutas de la API que manejan datos privados
API_PRIVADA = ["clientes", "citas", "pagos", "abonos", "inventario"]
# Rutas de la API cuyo contenido puede verse sin sesión, pero no modificarse
API_PUBLICA_LECTURA = ["productos", "servicios"]

PANEL = ["admin_dashboard", "admin_servicios", "admin_usuarios",
         "admin_citas_hoy", "admin_precios_promos", "recordatorios"]


def crear_usuarios(testcase):
    testcase.equipo = User.objects.create_user("equipo", password=CLAVE, is_staff=True)
    testcase.clienta = User.objects.create_user("clienta", password=CLAVE)


# ======================================================================
# LOGIN, SESIÓN Y REDIRECCIONES
# ======================================================================
class LoginSeguridadTests(TestCase):
    def setUp(self):
        crear_usuarios(self)

    def _entrar(self, usuario, clave=CLAVE, siguiente=None):
        datos = {"username": usuario, "password": clave}
        if siguiente:
            datos["next"] = siguiente
        return self.client.post(LOGIN, datos)

    def test_equipo_entra_al_panel(self):
        resp = self._entrar("equipo")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/panel/gestionar/citas/")

    def test_clienta_entra_a_mi_cuenta(self):
        resp = self._entrar("clienta")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/mi-cuenta/")

    def test_clave_incorrecta_no_inicia_sesion(self):
        resp = self._entrar("clienta", clave="incorrecta")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_inexistente_no_inicia_sesion(self):
        self._entrar("fantasma", clave="loquesea")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inyeccion_sql_en_el_login_no_funciona(self):
        self._entrar("' OR '1'='1", clave="' OR '1'='1")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_clienta_nunca_es_enviada_al_panel(self):
        resp = self._entrar("clienta", siguiente="/panel/dashboard/")
        self.assertEqual(resp.url, "/mi-cuenta/")

    def test_redireccion_a_sitio_externo_se_bloquea(self):
        resp = self._entrar("clienta", siguiente="https://sitio-malo.com/robo")
        self.assertEqual(resp.url, "/mi-cuenta/")

    def test_redireccion_con_doble_barra_se_bloquea(self):
        resp = self._entrar("clienta", siguiente="//sitio-malo.com")
        self.assertEqual(resp.url, "/mi-cuenta/")

    def test_entrar_al_login_cierra_la_sesion_anterior(self):
        self.client.force_login(self.clienta)
        self.client.get(LOGIN)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_cierra_la_sesion(self):
        self.client.force_login(self.clienta)
        resp = self.client.get("/segur/logout/")
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_exige_token_csrf(self):
        cliente_estricto = Client(enforce_csrf_checks=True)
        resp = cliente_estricto.post(LOGIN, {"username": "clienta", "password": CLAVE})
        self.assertEqual(resp.status_code, 403)


# ======================================================================
# ACCESO AL PANEL
# ======================================================================
class PanelSeguridadTests(TestCase):
    def setUp(self):
        crear_usuarios(self)

    def _url(self, nombre):
        from django.urls import reverse
        return reverse(nombre)

    def test_anonimo_es_enviado_al_login(self):
        for nombre in PANEL:
            with self.subTest(vista=nombre):
                resp = self.client.get(self._url(nombre))
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/segur/login/", resp.url)

    def test_clienta_recibe_403(self):
        self.client.force_login(self.clienta)
        for nombre in PANEL:
            with self.subTest(vista=nombre):
                resp = self.client.get(self._url(nombre))
                self.assertEqual(resp.status_code, 403)

    def test_equipo_si_entra(self):
        self.client.force_login(self.equipo)
        for nombre in PANEL:
            with self.subTest(vista=nombre):
                resp = self.client.get(self._url(nombre))
                self.assertEqual(resp.status_code, 200)

    def test_otras_pantallas_de_gestion_no_abren_a_anonimos(self):
        for nombre in ["usuarios_lista", "calendario_bloqueos", "panel_duena"]:
            with self.subTest(vista=nombre):
                resp = self.client.get(self._url(nombre))
                self.assertNotEqual(resp.status_code, 200)

    def test_otras_pantallas_de_gestion_no_abren_a_clientas(self):
        self.client.force_login(self.clienta)
        for nombre in ["usuarios_lista", "calendario_bloqueos", "panel_duena"]:
            with self.subTest(vista=nombre):
                resp = self.client.get(self._url(nombre))
                self.assertNotEqual(resp.status_code, 200)

    def test_mi_cuenta_exige_sesion(self):
        resp = self.client.get("/mi-cuenta/")
        self.assertEqual(resp.status_code, 302)


# ======================================================================
# TOKENS JWT
# ======================================================================
class TokenSeguridadTests(TestCase):
    def setUp(self):
        crear_usuarios(self)

    def test_credenciales_correctas_entregan_token(self):
        resp = self.client.post("/apix/token/", {"username": "equipo", "password": CLAVE})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())
        self.assertIn("refresh", resp.json())

    def test_credenciales_incorrectas_no_entregan_token(self):
        resp = self.client.post("/apix/token/", {"username": "equipo", "password": "mala"})
        self.assertEqual(resp.status_code, 401)

    def test_token_falso_es_rechazado(self):
        resp = self.client.post("/apix/token/verify/", {"token": "token.falso.123"})
        self.assertEqual(resp.status_code, 401)

    def test_token_no_se_entrega_por_get(self):
        resp = self.client.get("/apix/token/")
        self.assertEqual(resp.status_code, 405)


# ======================================================================
# API: CLIENTES, CITAS, PAGOS, ABONOS, INVENTARIO (datos privados)
# ======================================================================
class ApiPrivadaTests(TestCase):
    def setUp(self):
        crear_usuarios(self)
        Cliente.objects.create(nombre="Ana", rut="111")

    def test_anonimo_no_puede_leer_datos_privados(self):
        for ruta in API_PRIVADA:
            with self.subTest(ruta=ruta):
                resp = self.client.get("/api/%s/" % ruta)
                self.assertIn(resp.status_code, (401, 403),
                              "VULNERABILIDAD: /api/%s/ responde sin iniciar sesión" % ruta)

    def test_anonimo_no_puede_crear_clientes(self):
        antes = Cliente.objects.count()
        resp = self.client.post("/api/clientes/", {"nombre": "Intrusa", "rut": "999"})
        self.assertIn(resp.status_code, (401, 403))
        self.assertEqual(Cliente.objects.count(), antes)

    def test_anonimo_no_puede_borrar_clientes(self):
        c = Cliente.objects.get(rut="111")
        resp = self.client.delete("/api/clientes/%d/" % c.pk)
        self.assertIn(resp.status_code, (401, 403))
        self.assertTrue(Cliente.objects.filter(pk=c.pk).exists())

    def test_anonimo_no_puede_modificar_clientes(self):
        c = Cliente.objects.get(rut="111")
        self.client.patch("/api/clientes/%d/" % c.pk, {"nombre": "Hackeada"},
                          content_type="application/json")
        c.refresh_from_db()
        self.assertEqual(c.nombre, "Ana")

    def test_clienta_no_puede_leer_datos_privados(self):
        self.client.force_login(self.clienta)
        for ruta in API_PRIVADA:
            with self.subTest(ruta=ruta):
                resp = self.client.get("/api/%s/" % ruta)
                self.assertIn(resp.status_code, (401, 403),
                              "VULNERABILIDAD: una clienta ve /api/%s/" % ruta)

    def test_equipo_si_puede_leer_datos_privados(self):
        tok = self.client.post("/apix/token/", {"username": "equipo", "password": CLAVE}).json()["access"]
        for ruta in API_PRIVADA:
            with self.subTest(ruta=ruta):
                resp = self.client.get("/api/%s/" % ruta, HTTP_AUTHORIZATION="Bearer " + tok)
                self.assertEqual(resp.status_code, 200)


# ======================================================================
# API: PRODUCTOS Y SERVICIOS (se pueden ver, pero no modificar sin permiso)
# ======================================================================
class ApiPublicaTests(TestCase):
    def setUp(self):
        crear_usuarios(self)
        self.producto = Producto.objects.create(nombre="Shampoo", precio=5000)
        self.servicio = ServicioBelleza.objects.create(nombre="Corte", precio=10000)

    def test_anonimo_puede_ver_productos_y_servicios(self):
        for ruta in API_PUBLICA_LECTURA:
            with self.subTest(ruta=ruta):
                resp = self.client.get("/api/%s/" % ruta)
                self.assertEqual(resp.status_code, 200)

    def test_anonimo_no_puede_crear_productos(self):
        antes = Producto.objects.count()
        resp = self.client.post("/api/productos/", {"nombre": "Falso", "precio": "1"})
        self.assertIn(resp.status_code, (401, 403))
        self.assertEqual(Producto.objects.count(), antes)

    def test_anonimo_no_puede_cambiar_precio_de_servicio(self):
        self.client.patch("/api/servicios/%d/" % self.servicio.pk, {"precio": "1"},
                          content_type="application/json")
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.precio, 10000)

    def test_anonimo_no_puede_borrar_productos(self):
        resp = self.client.delete("/api/productos/%d/" % self.producto.pk)
        self.assertIn(resp.status_code, (401, 403))
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())


# ======================================================================
# ARCHIVOS ESTÁTICOS
# ======================================================================
class ArchivosSeguridadTests(TestCase):
    def test_no_se_puede_salir_de_la_carpeta_media(self):
        resp = self.client.get("/media/..%2f..%2fmanage.py")
        self.assertIn(resp.status_code, (400, 404))
