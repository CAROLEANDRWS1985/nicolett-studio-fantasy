from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ventas.models import Cliente, ServicioBelleza, Cita, Abono, DiaBloqueado

CLAVE = "clave12345"


def dia_habil(dias=3):
    """Primer día futuro que no sea domingo (el salón cierra los domingos)."""
    d = date.today() + timedelta(days=dias)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


def proximo_domingo():
    d = date.today() + timedelta(days=1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d


@override_settings(EMAIL_DUENA="duena@test.cl", DEFAULT_FROM_EMAIL="no-responder@test.cl")
class BaseIntegracion(TestCase):
    """Datos comunes: dos clientas, una cuenta del equipo, un servicio y Webpay simulado."""

    def setUp(self):
        self.user_a = User.objects.create_user("ana", password=CLAVE, email="ana@test.cl")
        self.user_b = User.objects.create_user("bea", password=CLAVE, email="bea@test.cl")
        self.equipo = User.objects.create_user("equipo", password=CLAVE, is_staff=True)
        self.cli_a = Cliente.objects.create(usuario=self.user_a, nombre="Ana", rut="111",
                                            telefono="911111111")
        self.cli_b = Cliente.objects.create(usuario=self.user_b, nombre="Bea", rut="222")
        self.servicio = ServicioBelleza.objects.create(nombre="Corte", precio=10000,
                                                       duracion_minutos=60)
        self.fecha = dia_habil()

        self.client_a = Client()
        self.client_a.force_login(self.user_a)
        self.client_b = Client()
        self.client_b.force_login(self.user_b)

        # Webpay simulado: no se contacta a Transbank
        patcher = patch("ventas.views_cliente._webpay")
        self.wp = patcher.start()
        self.addCleanup(patcher.stop)
        self.wp.return_value.create.return_value = {"url": "https://webpay.test/pagar",
                                                    "token": "tok123"}

    # ---- ayudas ----
    def agendar(self, http, hora="10:00", fecha=None, servicio=None):
        return http.post(reverse("agendar_cita"), {
            "servicio": (servicio or self.servicio).pk,
            "fecha": (fecha or self.fecha).isoformat(),
            "hora": hora,
        })

    def crear_cita(self, cliente, hora=time(10, 0), fecha=None, estado="pendiente"):
        return Cita.objects.create(cliente=cliente, servicio=self.servicio,
                                   fecha=fecha or self.fecha, hora=hora, estado=estado)

    def citas_en(self, hora=time(10, 0), fecha=None):
        return Cita.objects.filter(fecha=fecha or self.fecha, hora=hora).count()

    def slots(self, http, fecha=None):
        resp = http.get(reverse("horarios_cita"), {"fecha": (fecha or self.fecha).isoformat()})
        return {s["hora"]: s["libre"] for s in resp.json()["slots"]}

    def responder_webpay(self, cita, monto=5000, codigo=0, estado="AUTHORIZED"):
        self.wp.return_value.commit.return_value = {
            "buy_order": "C%d-1700000000" % cita.pk, "status": estado,
            "response_code": codigo, "amount": monto,
        }
        return self.client.post(reverse("webpay_retorno"), {"token_ws": "tok123"})


# ======================================================================
# HORARIOS DISPONIBLES
# ======================================================================
class HorariosTests(BaseIntegracion):
    def test_dia_habil_ofrece_nueve_horas_libres(self):
        slots = self.slots(self.client_a)
        self.assertEqual(len(slots), 9)
        self.assertEqual(min(slots), "10:00")
        self.assertEqual(max(slots), "18:00")
        self.assertTrue(all(slots.values()))

    def test_domingo_no_ofrece_horas(self):
        self.assertEqual(self.slots(self.client_a, proximo_domingo()), {})

    def test_fecha_pasada_no_ofrece_horas(self):
        self.assertEqual(self.slots(self.client_a, date.today() - timedelta(days=3)), {})

    def test_fecha_invalida_devuelve_lista_vacia(self):
        resp = self.client_a.get(reverse("horarios_cita"), {"fecha": "no-es-fecha"})
        self.assertEqual(resp.json(), {"slots": []})

    def test_sin_sesion_es_enviado_al_login(self):
        resp = Client().get(reverse("horarios_cita"), {"fecha": self.fecha.isoformat()})
        self.assertEqual(resp.status_code, 302)


# ======================================================================
# AGENDAR CITA
# ======================================================================
class AgendarTests(BaseIntegracion):
    def test_agendar_crea_cita_pendiente_y_lleva_al_pago(self):
        resp = self.agendar(self.client_a)
        cita = Cita.objects.get(cliente=self.cli_a)
        self.assertEqual(cita.estado, "pendiente")
        self.assertEqual(cita.servicio, self.servicio)
        self.assertEqual(cita.hora, time(10, 0))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("pagar_abono", args=[cita.pk]))

    def test_servicio_inexistente_da_404(self):
        resp = self.client_a.post(reverse("agendar_cita"), {
            "servicio": 9999, "fecha": self.fecha.isoformat(), "hora": "10:00"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Cita.objects.count(), 0)

    def test_servicio_inactivo_da_404(self):
        self.servicio.activo = False
        self.servicio.save()
        resp = self.agendar(self.client_a)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Cita.objects.count(), 0)

    def test_hora_con_formato_invalido_no_agenda(self):
        resp = self.agendar(self.client_a, hora="abc")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Cita.objects.count(), 0)

    def test_fecha_vacia_no_agenda(self):
        resp = self.client_a.post(reverse("agendar_cita"), {
            "servicio": self.servicio.pk, "fecha": "", "hora": "10:00"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Cita.objects.count(), 0)

    def test_hora_fuera_del_horario_no_agenda(self):
        for hora in ("08:00", "19:00", "22:00"):
            with self.subTest(hora=hora):
                self.agendar(self.client_a, hora=hora)
                self.assertEqual(Cita.objects.count(), 0)

    def test_domingo_no_agenda(self):
        self.agendar(self.client_a, fecha=proximo_domingo())
        self.assertEqual(Cita.objects.count(), 0)

    def test_fecha_pasada_no_agenda(self):
        self.agendar(self.client_a, fecha=date.today() - timedelta(days=2))
        self.assertEqual(Cita.objects.count(), 0)

    def test_sin_sesion_no_puede_agendar(self):
        resp = self.agendar(Client())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Cita.objects.count(), 0)

    def test_el_equipo_no_agenda_como_clienta(self):
        http = Client()
        http.force_login(self.equipo)
        self.agendar(http)
        self.assertEqual(Cita.objects.count(), 0)

    def test_agendar_solo_acepta_post(self):
        resp = self.client_a.get(reverse("agendar_cita"))
        self.assertEqual(resp.status_code, 405)


# ======================================================================
# AGENDAMIENTO SIN CRUCES
# ======================================================================
class CrucesTests(BaseIntegracion):
    def test_dos_clientas_no_pueden_tomar_la_misma_hora(self):
        self.agendar(self.client_a, hora="10:00")
        self.agendar(self.client_b, hora="10:00")
        self.assertEqual(self.citas_en(time(10, 0)), 1)
        self.assertEqual(Cita.objects.filter(cliente=self.cli_b).count(), 0)

    def test_la_misma_clienta_no_duplica_su_hora(self):
        self.agendar(self.client_a, hora="11:00")
        self.agendar(self.client_a, hora="11:00")
        self.assertEqual(self.citas_en(time(11, 0)), 1)

    def test_horas_distintas_si_se_pueden_agendar(self):
        self.agendar(self.client_a, hora="10:00")
        self.agendar(self.client_b, hora="11:00")
        self.assertEqual(Cita.objects.count(), 2)

    def test_la_hora_ocupada_aparece_como_no_libre(self):
        self.agendar(self.client_a, hora="10:00")
        slots = self.slots(self.client_b)
        self.assertFalse(slots["10:00"])
        self.assertTrue(slots["11:00"])

    def test_cita_cancelada_deja_la_hora_libre(self):
        self.crear_cita(self.cli_a, estado="cancelada")
        self.assertTrue(self.slots(self.client_b)["10:00"])
        self.agendar(self.client_b, hora="10:00")
        self.assertEqual(Cita.objects.filter(cliente=self.cli_b).count(), 1)

    def test_el_mismo_horario_en_otro_dia_no_choca(self):
        otro_dia = dia_habil(5)
        self.agendar(self.client_a, hora="10:00")
        self.agendar(self.client_b, hora="10:00", fecha=otro_dia)
        self.assertEqual(Cita.objects.filter(cliente=self.cli_b).count(), 1)


# ======================================================================
# CANCELAR CITA
# ======================================================================
class CancelarTests(BaseIntegracion):
    def test_clienta_cancela_su_cita_y_se_avisa_a_la_duena(self):
        cita = self.crear_cita(self.cli_a)
        resp = self.client_a.post(reverse("cancelar_cita", args=[cita.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Cita cancelada")
        self.assertEqual(mail.outbox[0].to, ["duena@test.cl"])

    def test_cancelar_libera_la_hora(self):
        self.agendar(self.client_a, hora="10:00")
        cita = Cita.objects.get(cliente=self.cli_a)
        self.client_a.post(reverse("cancelar_cita", args=[cita.pk]))
        self.assertTrue(self.slots(self.client_b)["10:00"])

    def test_no_se_puede_cancelar_la_cita_de_otra_clienta(self):
        cita = self.crear_cita(self.cli_b)
        resp = self.client_a.post(reverse("cancelar_cita", args=[cita.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Cita.objects.filter(pk=cita.pk).exists())

    def test_cancelar_solo_acepta_post(self):
        cita = self.crear_cita(self.cli_a)
        resp = self.client_a.get(reverse("cancelar_cita", args=[cita.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Cita.objects.filter(pk=cita.pk).exists())


# ======================================================================
# PAGO DEL ABONO (Webpay simulado)
# ======================================================================
class PagoTests(BaseIntegracion):
    def test_pagar_abono_envia_a_webpay_con_el_token(self):
        cita = self.crear_cita(self.cli_a)
        resp = self.client_a.get(reverse("pagar_abono", args=[cita.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"token_ws", resp.content)
        self.assertIn(b"tok123", resp.content)
        self.assertIn(b"https://webpay.test/pagar", resp.content)

    def test_no_se_puede_pagar_la_cita_de_otra_clienta(self):
        cita = self.crear_cita(self.cli_b)
        resp = self.client_a.get(reverse("pagar_abono", args=[cita.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_si_webpay_no_responde_la_hora_queda_libre(self):
        self.wp.return_value.create.side_effect = Exception("sin conexión")
        cita = self.crear_cita(self.cli_a)
        resp = self.client_a.get(reverse("pagar_abono", args=[cita.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())

    def test_pago_aprobado_confirma_cita_registra_abono_y_avisa(self):
        cita = self.crear_cita(self.cli_a)
        resp = self.responder_webpay(cita, monto=5000)
        self.assertEqual(resp.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, "confirmada")
        abono = Abono.objects.get(cliente=self.cli_a)
        self.assertEqual(abono.monto, 5000)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Cita confirmada con abono")

    def test_pago_rechazado_libera_la_hora_y_no_registra_abono(self):
        cita = self.crear_cita(self.cli_a)
        self.responder_webpay(cita, codigo=-1, estado="FAILED")
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())
        self.assertEqual(Abono.objects.count(), 0)

    def test_pago_anulado_por_la_clienta_libera_la_hora(self):
        cita = self.crear_cita(self.cli_a)
        resp = self.client.post(reverse("webpay_retorno"),
                                {"TBK_ORDEN_COMPRA": "C%d-1700000000" % cita.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())

    def test_si_falla_la_confirmacion_la_cita_no_se_pierde(self):
        self.wp.return_value.commit.side_effect = Exception("error")
        cita = self.crear_cita(self.cli_a)
        resp = self.client.post(reverse("webpay_retorno"), {"token_ws": "tok123"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Cita.objects.filter(pk=cita.pk).exists())
        self.assertEqual(Abono.objects.count(), 0)


# ======================================================================
# PERFIL
# ======================================================================
class PerfilTests(BaseIntegracion):
    def test_actualizar_perfil(self):
        self.client_a.post(reverse("editar_perfil"), {
            "nombre": "Ana Nueva", "telefono": "922222222", "fecha_nacimiento": "1990-05-10"})
        self.cli_a.refresh_from_db()
        self.assertEqual(self.cli_a.nombre, "Ana Nueva")
        self.assertEqual(self.cli_a.telefono, "922222222")
        self.assertEqual(self.cli_a.fecha_nacimiento, date(1990, 5, 10))

    def test_cumpleanos_futuro_se_rechaza(self):
        futuro = (date.today() + timedelta(days=30)).isoformat()
        self.client_a.post(reverse("editar_perfil"), {
            "nombre": "Cambiada", "fecha_nacimiento": futuro})
        self.cli_a.refresh_from_db()
        self.assertEqual(self.cli_a.nombre, "Ana")

    def test_cumpleanos_invalido_se_rechaza(self):
        self.client_a.post(reverse("editar_perfil"), {
            "nombre": "Cambiada", "fecha_nacimiento": "31-02-2000"})
        self.cli_a.refresh_from_db()
        self.assertEqual(self.cli_a.nombre, "Ana")

    def test_nombre_vacio_conserva_el_anterior(self):
        self.client_a.post(reverse("editar_perfil"), {"nombre": "   ", "telefono": "933333333"})
        self.cli_a.refresh_from_db()
        self.assertEqual(self.cli_a.nombre, "Ana")

    def test_perfil_solo_acepta_post(self):
        resp = self.client_a.get(reverse("editar_perfil"))
        self.assertEqual(resp.status_code, 405)


# ======================================================================
# ELIMINAR CUENTA
# ======================================================================
class EliminarCuentaTests(BaseIntegracion):
    def test_contrasena_incorrecta_no_elimina(self):
        self.client_a.post(reverse("eliminar_cuenta"), {"password": "mala"})
        self.assertTrue(User.objects.filter(pk=self.user_a.pk).exists())

    def test_con_citas_por_venir_no_elimina(self):
        self.crear_cita(self.cli_a)
        self.client_a.post(reverse("eliminar_cuenta"), {"password": CLAVE})
        self.assertTrue(User.objects.filter(pk=self.user_a.pk).exists())

    def test_sin_citas_elimina_la_cuenta_y_conserva_la_ficha(self):
        self.client_a.post(reverse("eliminar_cuenta"), {"password": CLAVE})
        self.assertFalse(User.objects.filter(pk=self.user_a.pk).exists())
        self.cli_a.refresh_from_db()
        self.assertFalse(self.cli_a.activo)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Cuenta eliminada")

    def test_cuenta_del_equipo_no_se_elimina_desde_aqui(self):
        http = Client()
        http.force_login(self.equipo)
        http.post(reverse("eliminar_cuenta"), {"password": CLAVE})
        self.assertTrue(User.objects.filter(pk=self.equipo.pk).exists())


# ======================================================================
# PORTAL "MI CUENTA"
# ======================================================================
class MiCuentaTests(BaseIntegracion):
    def test_clienta_ve_su_portal(self):
        resp = self.client_a.get("/mi-cuenta/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["n_citas"], 0)
        self.assertEqual(resp.context["nivel"], "Clienta Bronce")

    def test_el_nivel_sube_con_las_citas(self):
        for i in range(3):
            self.crear_cita(self.cli_a, fecha=dia_habil(3 + i))
        resp = self.client_a.get("/mi-cuenta/")
        self.assertEqual(resp.context["n_citas"], 3)
        self.assertEqual(resp.context["nivel"], "Clienta Plata")

    def test_sin_sesion_es_enviado_al_login(self):
        resp = Client().get("/mi-cuenta/")
        self.assertEqual(resp.status_code, 302)

    def test_el_equipo_no_puede_usar_el_portal_de_clientas(self):
        http = Client()
        http.force_login(self.equipo)
        resp = http.get("/mi-cuenta/")
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", http.session)

    def test_abrir_reserva_sin_iniciar_sesion_de_nuevo_pide_login(self):
        resp = self.client_a.get("/mi-cuenta/?abrir=agendar")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith("/segur/login/?next="))
        self.assertNotIn("_auth_user_id", self.client_a.session)


class DiasBloqueadosTests(BaseIntegracion):
    def test_solo_devuelve_dias_bloqueados_futuros(self):
        futuro = date.today() + timedelta(days=10)
        DiaBloqueado.objects.create(fecha=futuro, motivo="Feriado")
        DiaBloqueado.objects.create(fecha=date.today() - timedelta(days=10))
        resp = self.client_a.get(reverse("dias_bloqueados"))
        self.assertEqual(resp.json(), {"bloqueados": [futuro.isoformat()]})

    def test_sin_sesion_es_enviado_al_login(self):
        resp = Client().get(reverse("dias_bloqueados"))
        self.assertEqual(resp.status_code, 302)


# ======================================================================
# FLUJO COMPLETO DE PUNTA A PUNTA
# ======================================================================
class FlujoCompletoTests(BaseIntegracion):
    def test_login_agendar_pagar_confirmar_y_cancelar(self):
        http = Client()

        # 1. Inicia sesion por la pantalla de login
        resp = http.post("/segur/login/", {"username": "ana", "password": CLAVE})
        self.assertEqual(resp.url, "/mi-cuenta/")
        self.assertEqual(http.get("/mi-cuenta/").status_code, 200)

        # 2. Ve las horas libres del dia
        self.assertTrue(self.slots(http)["10:00"])

        # 3. Agenda: queda pendiente y la envian al pago
        resp = self.agendar(http, hora="10:00")
        cita = Cita.objects.get(cliente=self.cli_a)
        self.assertEqual(cita.estado, "pendiente")
        self.assertEqual(resp.url, reverse("pagar_abono", args=[cita.pk]))

        # 4. Webpay recibe el pago y la hora ya no esta libre para otra clienta
        self.assertEqual(http.get(resp.url).status_code, 200)
        self.assertFalse(self.slots(self.client_b)["10:00"])

        # 5. Pago aprobado: cita confirmada, abono registrado y aviso a la duena
        self.responder_webpay(cita, monto=5000)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, "confirmada")
        self.assertEqual(Abono.objects.filter(cliente=self.cli_a).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        # 6. La cita aparece en su historial
        self.assertEqual(http.get("/mi-cuenta/").context["n_citas"], 1)

        # 7. Cancela: la hora vuelve a quedar libre y se avisa otra vez a la duena
        http.post(reverse("cancelar_cita", args=[cita.pk]))
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())
        self.assertTrue(self.slots(self.client_b)["10:00"])
        self.assertEqual(len(mail.outbox), 2)
