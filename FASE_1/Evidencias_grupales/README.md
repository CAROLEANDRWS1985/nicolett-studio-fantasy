# Nicolette Studio Fantasy

Plataforma web de gestión, ventas y atención de clientes para la peluquería Nicolette Studio Fantasy.

## Descripción

**Qué hace:** es una plataforma web que da a la peluquería presencia en internet y un sistema propio para administrar el negocio. Va más allá de la agenda: reúne la oferta de servicios, la venta de productos, el registro de las clientas y su historial de atenciones, y la comunicación con ellas.

**Para la dueña:** un panel administrativo donde puede agendar y cancelar citas, bloquear días completos en los que no quiere trabajar (incluso con anticipación), vender productos y ofrecer sus servicios por internet y por Instagram. Además, lleva el historial de servicios de cada cliente y sabe cuáles son menores de edad, para quienes existe el Rincón Kids.

**Para las clientas:** pueden crear una cuenta, iniciar sesión, ver los servicios de la peluquería, revisar su perfil y conocer los beneficios por ser clientes frecuentes. También agendan sus horas por sí mismas y, para confirmar una cita, deben pagar un abono por el servicio, que se cobra de inmediato mediante WebPay. Al pagar, reciben una boleta de simulación por correo.

**Avisos:** cada vez que una cliente agenda o cancela, se notifica por correo a la dueña y en el panel administrativo.

**A quién va dirigido:**

- La dueña de la peluquería, que administra el negocio.
- Los trabajadores del local, que atienden a las clientas.
- Las clientas, que consultan servicios y reservan sus horas.

**Qué problema resuelve:** la dueña no tenía página web y llevaba toda su agenda en un cuaderno o en una planilla de Excel. Esto provocaba que las horas se duplicaran o se perdieran, y que las clientas tuvieran que buscarla por WhatsApp para agendar. Tampoco quedaba registro de qué servicio se realizó, cuánto se cobró ni qué profesional atendió, lo que generaba pérdida de clientela. Además, no existía ningún mecanismo de pago previo, por lo que una cliente podía reservar y no asistir. La plataforma ordena la agenda, asegura cada reserva con un abono, deja un registro de cada atención y de cada cliente, y le da a la dueña un canal propio para ofrecer sus servicios y vender sus productos.

## Funcionalidades principales

- Catálogo de servicios (59 servicios en categorías como colorimetría, tratamientos, manicure, pedicure, podología, corte de cabello, cejas, pestañas, uñas y depilación).
- Registro e inicio de sesión de clientes, con perfil y panel personal (`/mi-cuenta/`).
- Beneficios para clientes frecuentes, visibles en su perfil.
- Historial de servicios de cada cliente, con registro de si es menor de edad.
- Rincón Kids, orientado a clientes menores de edad.
- Agendamiento y cancelación de citas, con abono obligatorio según el tipo de servicio, pagado en línea por WebPay.
- Boleta de simulación en PDF al pagar el abono, guardada en `media/boletas/` y enviada por correo a la clienta y a la dueña.
- Panel administrativo para agendar y cancelar citas, y para gestionar clientes.
- Bloqueo de días en los que la dueña no atiende, de forma inmediata o con anticipación y por emergencia.
- Venta de productos desde la página web.
- Notificaciones por correo a la dueña al agendar o cancelar.

## Tecnologías utilizadas

| Área | Tecnología |
|---|---|
| Lenguaje | Python, HTML, CSS, JavaScript |
| Estructura | Django |
| Base de datos | SQLite |
| Pagos | WebPay Plus (ambiente de pruebas de Transbank) |
| Correo | SMTP con Gmail (contraseña de aplicación) |
| Contenedores | Docker y Docker Compose |
| Configuración | Variables de entorno (archivo `.env`) |
| Nube / alojamiento | Ninguno por ahora: el sistema funciona en entorno local |
| Control de versiones | Git |

## Contenerización con Docker

El proyecto se ejecuta dentro de un contenedor Docker, por lo que funciona igual en cualquier computador sin instalar Python ni las librerías a mano.

### Archivos de Docker

Están en la carpeta `backend`, junto a `manage.py`.

| Archivo | Para qué sirve |
|---|---|
| `Dockerfile` | Receta para construir la imagen del proyecto. |
| `docker-compose.yml` | Define cómo se ejecuta el contenedor: puerto, variables de entorno y volúmenes. |
| `.env` | Variables de entorno con las claves (no se sube a Git). |
| `.dockerignore` | Evita copiar a la imagen archivos innecesarios o secretos. |
| `requirements.txt` | Lista de librerías de Python que se instalan en la imagen. |

### Dockerfile

1. Parte de la imagen `python:3.12-slim`.
2. Define `/app` como carpeta de trabajo.
3. Copia `requirements.txt` e instala las librerías con `pip`.
4. Copia el código del proyecto.
5. Expone el puerto `8000`.
6. Arranca Django con `python manage.py runserver 0.0.0.0:8000`.

### Docker Compose

El archivo `docker-compose.yml` levanta el servicio `web` con esta configuración:

- **Construcción:** arma la imagen desde el `Dockerfile`.
- **Puerto:** publica el `8000` del contenedor en el `8000` del computador.
- **Variables de entorno:** las lee desde el archivo `.env`.
- **Volúmenes:** `db.sqlite3` y `media/` se guardan en el computador, así la base de datos y las boletas no se pierden al apagar el contenedor.
- **Reinicio:** `restart: unless-stopped`.

### Variables de entorno

Las claves no están escritas en el código: `settings.py` las lee con `os.environ.get(...)` desde el archivo `.env`.

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave interna de Django (sesiones y cookies). |
| `DEBUG` | `True` en desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Dominios permitidos, separados por coma. |
| `EMAIL_HOST_USER` | Correo Gmail desde el que se envían los avisos y boletas. |
| `EMAIL_HOST_PASSWORD` | Contraseña de aplicación de Google (no es la contraseña normal del correo). |
| `EMAIL_DUENA` | Correo de la dueña, donde llegan los avisos de reservas. |

Ejemplo de `.env` (usar valores propios, sin comillas ni espacios alrededor del `=`):

```
SECRET_KEY=clave-larga-y-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST_USER=correo@gmail.com
EMAIL_HOST_PASSWORD=contraseñadeaplicacion
EMAIL_DUENA=correo@gmail.com
```

Para generar una `SECRET_KEY`:

```
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

La contraseña de aplicación se crea en la cuenta de Google, en *Seguridad → Contraseñas de aplicaciones* (requiere la verificación en 2 pasos activada).

> El archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

## Instrucciones para ejecutar el proyecto localmente

### Opción 1: con Docker (recomendada)

**Requisitos previos:** Git y Docker Desktop instalados y abiertos (debe decir "Engine running"). En Windows, también WSL 2.

1. Clonar el repositorio y entrar a la carpeta del backend (la que contiene `manage.py`, `Dockerfile` y `docker-compose.yml`):

```
git clone <URL-DEL-REPOSITORIO>
cd backend
```

2. Crear el archivo `.env` con las variables descritas arriba.
3. Construir y levantar el sistema:

```
docker compose up --build
```

4. Abrir en el navegador **http://localhost:8000/**

Comandos útiles:

| Acción | Comando |
|---|---|
| Levantar en segundo plano | `docker compose up -d` |
| Reconstruir después de cambiar código | `docker compose up --build -d` |
| Ver los mensajes del sistema | `docker compose logs -f` |
| Ver si está corriendo | `docker compose ps` |
| Apagar el sistema | `docker compose down` |
| Aplicar migraciones | `docker compose exec web python manage.py migrate` |
| Crear un superusuario | `docker compose exec web python manage.py createsuperuser` |

### Opción 2: sin Docker

**Requisitos previos:** Python 3 y Git instalados.

1. Clonar el repositorio y entrar a la carpeta del backend:

```
git clone <URL-DEL-REPOSITORIO>
cd backend
```

2. Crear y activar un entorno virtual (Windows):

```
python -m venv venv
venv\Scripts\activate
```

3. Instalar las dependencias:

```
pip install -r requirements.txt
```

4. Configurar las variables de entorno, en especial las del correo (SMTP) que se usan para avisar a la dueña. Para pruebas se puede usar un correo propio como destinatario.
5. Crear la base de datos (SQLite) y un usuario administrador:

```
python manage.py migrate
python manage.py createsuperuser
```

6. Levantar el servidor:

```
python manage.py runserver
```

7. Abrir en el navegador **http://127.0.0.1:8000/**

## Pago de prueba (WebPay Plus)

El sistema usa el ambiente de integración de Transbank. Para probar un pago:

- **Tarjeta VISA:** 4051 8856 0044 6623, CVV 123, cualquier fecha futura.
- **Autenticación:** RUT 11.111.111-1, clave 123, y elegir *Aceptar*.
- Para probar un pago rechazado se puede usar la tarjeta MASTERCARD 5186 0595 5959 0568.

Al aprobarse el pago, la cita queda confirmada y se genera una boleta de simulación en `media/boletas/`, que además se envía por correo a la clienta y a la dueña.

## Estado del despliegue

El sistema está contenerizado con Docker y Docker Compose, y se ejecuta de forma local. Todavía no está desplegado en un servidor ni en la nube. La configuración actual usa el servidor de desarrollo de Django (`runserver`); para producción se recomienda `gunicorn`, `DEBUG=False` y una base de datos como PostgreSQL.

## Integrantes del equipo

| Integrante | Rol |
|---|---|
| Carol García | Gerente de proyecto y desarrolladora (backend, frontend, pruebas y documentación) |

## Metodología de trabajo

El proyecto se desarrolla con Scrum. Se trabaja con un Product Backlog priorizado, Sprint Backlog por sprint, Definición de Done y una retrospectiva al cierre de cada sprint.

## Arquitectura de la solución

La aplicación sigue la arquitectura MTV (Modelo – Plantilla – Vista) de Django, con una base de datos SQLite:

- **Modelos:** guardan clientas, servicios, citas y el registro de cada atención (servicio realizado, monto cobrado, profesional y si la clienta vino sola o con un hijo).
- **Vistas:** contienen la lógica de inicio de sesión, agendamiento y cancelación de citas, pago del abono con WebPay, boletas y notificaciones.
- **Plantillas:** generan la interfaz que ven las clientes y la administración.
- **Despliegue:** contenedor Docker con Django y SQLite, orquestado con Docker Compose. La base de datos y las boletas se conservan mediante volúmenes.

### Diagrama de arquitectura

_(Insertar aquí la imagen del diagrama)_
