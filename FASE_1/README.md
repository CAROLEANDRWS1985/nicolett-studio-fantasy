
Nicolette Studio Fantasy
Plataforma web de gestión, ventas y atención de clientes para la peluquería Nicolette Studio Fantasy.

Descripción
Qué hace: es una plataforma web que da a la peluquería presencia en internet y un sistema propio para administrar el negocio. Va más allá de la agenda: reúne la oferta de servicios, la venta de productos, el registro de las clientas y su historial de atenciones, y la comunicación con ellas.

Para la dueña: un panel administrativo donde puede agendar y cancelar citas, bloquear días completos en los que no quiere trabajar (incluso con anticipación), vender productos y ofrecer sus servicios por internet y por Instagram. Además, lleva el historial de servicios de cada cliente y sabe cuáles son menores de edad, para quienes existe el Rincón Kids.

Para las clientas: pueden crear una cuenta, iniciar sesión, ver los servicios de la peluquería, revisar su perfil y conocer los beneficios por ser clientes frecuentes. También agendan sus horas por sí mismas y, para confirmar una cita, deben pagar un abono por el servicio, que se cobra de inmediato mediante WebPay. Al pagar, reciben una boleta de simulación por correo.

Avisos: cada vez que una cliente agenda o cancela, se notifica por correo a la dueña y en el panel administrativo.

A quién va dirigido:

La dueña de la peluquería, que administra el negocio.
Los trabajadores del local, que atienden a las clientas.
Las clientas, que consultan servicios y reservan sus horas.
Qué problema resuelve: la dueña no tenía página web y llevaba toda su agenda en un cuaderno o en una planilla de Excel. Esto provocaba que las horas se duplicaran o se perdieran, y que las clientas tuvieran que buscarla por WhatsApp para agendar. Tampoco quedaba registro de qué servicio se realizó, cuánto se cobró ni qué profesional atendió, lo que generaba pérdida de clientela. Además, no existía ningún mecanismo de pago previo, por lo que una cliente podía reservar y no asistir. La plataforma ordena la agenda, asegura cada reserva con un abono, deja un registro de cada atención y de cada cliente, y le da a la dueña un canal propio para ofrecer sus servicios y vender sus productos.

Funcionalidades principales
Catálogo de servicios (59 servicios en categorías como colorimetría, tratamientos, manicure, pedicure, podología, corte de cabello, cejas, pestañas, uñas y depilación).
Registro e inicio de sesión de clientes, con perfil y panel personal (/mi-cuenta/).
Beneficios para clientes frecuentes, visibles en su perfil.
Historial de servicios de cada cliente, con registro de si es menor de edad.
Rincón Kids, orientado a clientes menores de edad.
Agendamiento y cancelación de citas, con abono obligatorio según el tipo de servicio, pagado en línea por WebPay.
Boleta de simulación en PDF al pagar el abono, guardada en media/boletas/ y enviada por correo a la clienta y a la dueña.
Panel administrativo para agendar y cancelar citas, y para gestionar clientes.
Bloqueo de días en los que la dueña no atiende, de forma inmediata o con anticipación y por emergencia.
Venta de productos desde la página web.
Notificaciones por correo a la dueña al agendar o cancelar.
Boleta de simulación por correo al comprar productos en la tienda: la clienta recibe su boleta con el detalle de lo comprado y la dueña recibe un aviso de la venta con el duplicado de la boleta, ambos con el PDF adjunto.
Formulario de contacto con el WhatsApp de la clienta, y correo a la dueña con un botón para responderle por WhatsApp.
Al cerrar sesión, tanto la clienta como la dueña vuelven a la página principal de la peluquería.
Gestión de proveedores y de compras a proveedores desde el panel administrativo.
Tecnologías utilizadas
Área	Tecnología
Lenguaje	Python, HTML, CSS, JavaScript
Estructura	Django
Base de datos	SQLite
Pagado	WebPay Plus (ambiente de pruebas de Transbank)
Correo	SMTP con Gmail (contraseña de aplicación)
Boletas PDF de la tienda	xhtml2pdf
Contenedores	Docker y Docker Compose
Configuración	Variables de entorno (archivo .env)
Nube / alojamiento	Ninguno por ahora: el sistema funciona en entorno local
Control de versiones	Git
Contenerización con Docker
El proyecto se ejecuta dentro de un contenedor Docker, por lo que funciona igual en cualquier computador sin instalar Python ni las librerías a mano.

Archivos de Docker
Están en la carpeta backend, junto a manage.py.

Archivo	Para qué sirve
Dockerfile	Receta para construir la imagen del proyecto.
docker-compose.yml	Define cómo se ejecuta el contenedor: puerto, variables de entorno y volúmenes.
.env	Variables de entorno con las claves (no se sube a Git).
.dockerignore	Evita copiar a la imagen archivos innecesarios o secretos.
requirements.txt	Lista de librerías de Python que se instalan en la imagen.
La página principal de la peluquería (proyecto frontend) tiene sus propios archivos de Docker, en la carpeta frontend, junto a su manage.py:

Archivo	Para qué sirve
Dockerfile	Receta para construir la imagen de la página principal (puerto 9020).
.env	Variables de entorno del correo del formulario de contacto (no se sube a Git).
.dockerignore	Evita copiar a la imagen archivos temporales y el .env.
requirements.txt	Librerías del frontend: Django==5.2.3, python-dotenv y tzdata.
En el requirements.txt del backend se agregaron xhtml2pdf (PDF de las boletas de la tienda) y python-dotenv (lectura del .env), y reportlab quedó en la versión 4, que es la que exige xhtml2pdf.

Dockerfile
Parte de la imagen python:3.12-slim.
Define /app como carpeta de trabajo.
Copia requirements.txt e instala las librerías con pip.
Copia el código del proyecto.
Expone el puerto 8000.
Arranca Django con python manage.py runserver 0.0.0.0:8000.
Docker Compose
El archivo docker-compose.yml levanta el servicio web con esta configuración:

Construcción: arma la imagen desde el Dockerfile.
Puerto: publica el 8000 del contenedor en el 8000 del computador.
Variables de entorno: las lee desde el archivo .env.
Volúmenes: db.sqlite3 y media/ se guardan en el computador, así la base de datos y las boletas no se pierden al apagar el contenedor.
Reinicio: restart: unless-stopped.
El mismo docker-compose.yml levanta también el servicio frontend, la página principal de la peluquería:

Construcción: arma la imagen desde ../frontend/Dockerfile.
Puerto: publica el 9020 del contenedor en el 9020 del computador.
Variables de entorno: las lee desde ../frontend/.env.
Volúmenes: ../frontend/db.sqlite3 se guarda en el computador, así los mensajes del formulario de contacto no se pierden.
Orden de arranque: depends_on: web, primero se levanta el backend.
Reinicio: restart: unless-stopped.
Servicio	Contenedor	Puerto	Dirección
web(backend)	nicolett	8000	http://localhost:8000/
frontend(página principal)	nicolett-frontend	9020	http://127.0.0.1:9020/venta/index
Variables de entorno
Las claves no están escritas en el código: settings.py las lee con os.environ.get(...) desde el archivo .env.

Variable	Descripción
SECRET_KEY	Clave interna de Django (sesiones y cookies).
DEBUG	True en desarrollo, False en producción.
ALLOWED_HOSTS	Dominios permitidos, separados por coma.
EMAIL_HOST_USER	Correo Gmail desde el que se envían los avisos y boletas.
EMAIL_HOST_PASSWORD	Contraseña de aplicación de Google (no es la contraseña normal del correo).
EMAIL_DUENA	Correo de la dueña, donde llegan los avisos de reservas.
Ejemplo de .env (usar valores propios, sin comillas ni espacios alrededor del =):

SECRET_KEY=clave-larga-y-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST_USER=correo@gmail.com
EMAIL_HOST_PASSWORD=contraseñadeaplicacion
EMAIL_DUENA=correo@gmail.com
Para generar una SECRET_KEY:

python -c "import secrets; print(secrets.token_urlsafe(50))"
La contraseña de aplicación se crea en la cuenta de Google, en Seguridad → Contraseñas de aplicaciones (requiere la verificación en 2 pasos activada).

El frontend necesita su propio .env en la carpeta frontend, con las variables EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y EMAIL_DUENA. Se puede crear copiando el del backend:

copy backend\.env frontend\.env
En el backend, el correo de la dueña que recibe el aviso de venta de la tienda (NICOLETT_EMAIL) se toma de EMAIL_DUENA. En el frontend, CORREO_DUENA también se toma de EMAIL_DUENA.

El archivo .env está en .gitignore y nunca debe subirse al repositorio.

Instrucciones para ejecutar el proyecto localmente
Opción 1: con Docker (recomendada)
Requisitos previos: Git y Docker Desktop instalados y abiertos (debe decir "Engine running"). En Windows, también WSL 2.

Clonar el repositorio y entrar a la carpeta del backend (la que contiene manage.py, Dockerfile y docker-compose.yml):
git clone <URL-DEL-REPOSITORIO>
cd backend
Crear el archivo .env con las variables descritas arriba, en la carpeta backend y en la carpeta frontend.
Construir y levantar el sistema (backend y página principal juntos):
docker compose up --build
Esperar a que aparezcan las dos líneas Starting development server, una de nicolett (puerto 8000) y otra de nicolett-frontend (puerto 9020).
Abrir en el navegador:
Página principal de la peluquería: http://127.0.0.1:9020/venta/index
Backend: http://localhost:8000/
Antes de levantar con Docker hay que cerrar los servidores que estén corriendo a mano con runserver, para que los puertos 8000 y 9020 queden libres.

Comandos útiles:

Acción	Dominio
Levantar en segundo plano	docker compose up -d
Reconstruir después de cambiar código	docker compose up --build -d
Ver los mensajes del sistema	docker compose logs -f
Ver si está corriendo	docker compose ps
Apagar el sistema	docker compose down
Aplicar migraciones	docker compose exec web python manage.py migrate
Crear un superusuario	docker compose exec web python manage.py createsuperuser
Opción 2: sin Docker
Requisitos previos: Python 3 y Git instalados.

Clonar el repositorio y entrar a la carpeta del backend:
git clone <URL-DEL-REPOSITORIO>
cd backend
Crear y activar un entorno virtual (Windows):
python -m venv venv
venv\Scripts\activate
Instalar las dependencias:
pip install -r requirements.txt
Configurar las variables de entorno, en especial las del correo (SMTP) que se usan para avisar a la dueña. Para pruebas se puede usar un correo propio como destinatario.
Crear la base de datos (SQLite) y un usuario administrador:
python manage.py migrate
python manage.py createsuperuser
Levantar el servidor:
python manage.py runserver
Abrir en el navegador http://127.0.0.1:8000/
Página principal de la peluquería (frontend)
La página pública de la peluquería (inicio, servicios, nosotras, contacto, productos, Rincón Kids y carrito) corre en un proyecto Django aparte, en el puerto 9020. Se levanta en otra terminal, con el backend corriendo en el puerto 8000:

cd frontend
python manage.py runserver 9020
Y se abre en http://127.0.0.1:9020/venta/index

Pago de prueba (WebPay Plus)
El sistema usa el ambiente de integración de Transbank. Para probar un pago:

Tarjeta VISA: 4051 8856 0044 6623, CVV 123, cualquier fecha futura.
Autenticación: RUT 11.111.111-1, clave 123, y elegir Aceptar.
Para probar un pago rechazado se puede usar la tarjeta MASTERCARD 5186 0595 5959 0568.
Al aprobarse el pago, la cita queda confirmada y se genera una boleta de simulación en media/boletas/, que además se envía por correo a la clienta y a la dueña.

Boletas por compra de productos
Cuando una clienta compra productos desde la tienda y el pago con WebPay es aprobado, se envían dos correos con la boleta de simulación en PDF adjunta:

A	Asunto	Contenido	Asistente
Clienta	Tu boleta N° … · Nicolett Studio Fantasy	Saludo, número de boleta, fecha, medio de pago, detalle de cada producto (nombre, descripción, cantidad, precio y subtotal), neto, IVA y total.	boleta_<N°>.pdf
Dueña	Nueva venta N° … · nombre de la clienta	"Hola Nicolett, ¡tenemos una nueva venta!", quién compró, su correo, la fecha, qué compró y el total pagado.	boleta_<N°>_duplicado.pdf, con la franja DUPLICADO
Cómo funciona:

Al iniciar el pago, carrito_pagar (ventas/views_catalogo.py) guarda el correo y el nombre de la clienta en la caché de Django, asociados al número de orden.
Al volver de WebPay con el pago aprobado, webpay_carrito_retorno descuenta el stock y llama a _enviar_boleta_compra.
_enviar_boleta_compra recupera los datos de la clienta y llama a enviar_boletas (ventas/correos.py), que genera los PDF y envía los dos correos.
Si la página de retorno se recarga, WebPay rechaza la segunda confirmación, por lo que la boleta no se envía dos veces.
Archivos nuevos:

Archivo	Función
ventas/correos.py	Calcula totales, neto e IVA, genera los PDF con xhtml2pdf y envía los correos.
front/templates/emails/boleta.html	Diseño de la boleta (correo de la clienta y los dos PDF).
front/templates/emails/aviso_nicolett.html	Diseño del aviso de venta para la dueña.
Configuración usada en settings.py: DEFAULT_FROM_EMAIL (correo que envía las boletas, armado con EMAIL_HOST_USER) y NICOLETT_EMAIL (correo de la dueña que recibe el aviso de venta, tomado de EMAIL_DUENA). Ambos se leen desde el .env.

Formulario de contacto con WhatsApp
El formulario de la sección Contacto de la página principal pide el WhatsApp de la clienta en lugar de su correo. Los campos son nombre completo, WhatsApp, asunto y mensaje.

Al enviarlo:

El mensaje se guarda en el modelo MensajeContacto, que ahora tiene el campo whatsapp. El campo email quedó opcional para conservar los mensajes antiguos.
La dueña recibe un correo con diseño, con los datos de la clienta, su mensaje y un botón RESPONDER POR WHATSAPP que abre el chat directo con ella.
Archivos modificados (proyecto frontend): venta/models.py, venta/views.py, venta/templates/index.html y la migración venta/migrations/0002_mensajecontacto_whatsapp_alter_mensajecontacto_email.py.

Cierre de sesión
Quién	Botón	Ruta	Después de cerrar sesión
Clienta	SALIR, en Mi cuenta	/segur/logout/	Vuelve a la página principal de la peluquería
Dueña y equipo	Cerrar sesión, en el panel	/admin-logout/	Vuelve a la página principal de la peluquería
Archivos modificados (proyecto backend): segur/views.py (logout_view), backend/views.py (admin_logout) y ventas/templates/ventas/mi_cuenta.html (el botón SALIR usa /segur/logout/).

Proveedores y compras a proveedores
En el menú del panel administrativo, debajo de Cancelar por emergencia, se agregaron las secciones Proveedores y Compras a proveedores.

Proveedores (Proveedor):

Campo	Descripción
Nombre	Nombre del proveedor.
RODERA	Opcional.
Persona de contacto	Opcional.
Teléfono	Opcional.
Correo	Opcional.
Notas	Condiciones, días de despacho, pedido mínimo, etc.
Activo	Indica si todavía se trabaja con ese proveedor. Si se marca como no activo, su historial de compras se conserva.
Compras a proveedores (CompraProveedor):

Campo	Descripción
Proveedor	A quién se le compró.
Fecha de compra	Por defecto, el día de hoy.
N° factura o boleta	Opcional.
Monto total	Se ingresa solo el número, sin puntos ni signo $. En la lista se muestra como $185.000.
Qué se compró	Nota con el detalle de la compra.
No se puede eliminar un proveedor que tiene compras registradas; el panel muestra un aviso y sugiere marcarlo como no activo.

Ambas secciones usan el sistema genérico del panel (ventas/views_crud.py, plantillas crud_lista.html y crud_form.html). La migración es ventas/migrations/0010_proveedor_compraproveedor.py.

Registro de cambios
21 de octubre de 2026
Boleta de simulación por correo a la clienta al comprar productos en la tienda, con PDF adjunto.
Aviso de venta por correo a la dueña, con el detalle de la compra y el duplicado de la boleta en PDF.
Nueva librería xhtml2pdf para generar los PDF de las boletas de la tienda.
Formulario de contacto con WhatsApp en lugar de correo, y correo a la dueña con diseño y botón para responder por WhatsApp.
Al cerrar sesión, la clienta y la dueña vuelven a la página principal de la peluquería.
Nuevas secciones de Proveedores y Compras a proveedores en el panel administrativo.
En las listas del panel, los montos se muestran con formato $185.000 y los campos de sí o no se muestran como "Sí" o "No".
Aviso al intentar eliminar un registro que tiene datos asociados.
Corrección del inventario del producto Inoar., que no tenía registro de stock y aparecía como sin stock.
Limpieza de los usuarios de prueba.
Docker: la página principal de la peluquería (frontend) quedó contenerizada con su propio Dockerfile, .dockerignore, requirements.txt y .env, y se agregó como servicio frontend en docker-compose.yml. Un solo docker compose up --build levanta el sistema completo.
Docker: se agregaron xhtml2pdf y python-dotenv al requirements.txt del backend, y reportlab quedó en la versión 4.
El correo del backend y del frontend se lee desde el .env; se quitaron las claves escritas directamente en settings.py.
Estado del despliegue
El sistema está contenerizado con Docker y Docker Compose (backend y página principal), y se ejecuta de forma local. Todavía no está desplegado en un servidor ni en la nube. La configuración actual usa el servidor de desarrollo de Django (runserver); para producción se recomienda gunicorn, DEBUG=False y una base de datos como PostgreSQL.

Integrantes del equipo
Integral	Role
Carol García	Gerente de proyecto y desarrolladora (backend, frontend, pruebas y documentación)
Metodología de trabajo
El proyecto se desarrolla con Scrum. Se trabaja con un Product Backlog priorizado, Sprint Backlog por sprint, Definición de Done y una retrospectiva al cierre de cada sprint.

Arquitectura de la solución
La aplicación sigue la arquitectura MTV (Modelo – Plantilla – Vista) de Django, con una base de datos SQLite:

Modelos: guardan clientas, servicios, citas y el registro de cada atención (servicio realizado, monto cobrado, profesional y si la clienta vino sola o con un hijo).
Vistas: contienen la lógica de inicio de sesión, agendamiento y cancelación de citas, pago del abono con WebPay, boletas y notificaciones.
Plantillas: generan la interfaz que ven las clientes y la administración.
Despliegue: contenedor Docker con Django y SQLite, orquestado con Docker Compose. La base de datos y las boletas se conservan mediante volúmenes.
Diagrama de arquitectura
Servicios externos
Base de datos
Backend · contenedor nicolett · puerto 8000
Frontend · contenedor nicolett-frontend · puerto 9020
Visitar la página
Mostrar la página
Catálogo de productosy pago del carrito
Solicitud HTTPlogin, panel de la clientay panel administrativo
Respuesta HTTP
Cerrar sesión: vuelvea la página de la peluquería
Enrutar solicitud
Procesar solicitud
Enviar respuesta
Consultar datos
Devolver datos
Guardar mensaje decontacto
Procesar abono ycompra de productos
Confirmar pago
Enviar recordatorios
Recordatorios, boleta PDF ala clientay aviso de venta conduplicado a la dueña
Aviso de mensaje decontacto
Botón responder porWhatsApp
Galería y contacto
Navegador web(clienta, profesional yadministrador)
Página de la peluqueríainicio, servicios, productos,Rincón Kids, carrito ycontacto con WhatsApp
Servidor web
Controlador API
Servidor de aplicaciónagendamiento, agenda,alertas, roles,fidelización, inventario,tienda,boletas PDF, proveedores ycompras
Base de datos backendSQLite
Base de datos frontendSQLite · mensajes decontacto
TransbankWebpay Plus
WhatsApp
CorreoGmail SMTP
Instagram

Claude ha terminado la respuesta
