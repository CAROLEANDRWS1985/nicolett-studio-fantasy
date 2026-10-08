from django.urls import re_path
from django.conf import settings
from django.views.static import serve
from ventas import views_catalogo
from django.views.generic import RedirectView
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views
from .views import (
    home, contacto, LoadMenu,
    ClienteViewSet, ProductoViewSet, InventarioViewSet,
    ServicioBellezaViewSet, CitaViewSet, PagoViewSet, AbonoViewSet
)
from ventas import views_panel
from ventas import views_crud
from ventas import views_cliente
from ventas import views_usuarios
from ventas import views_emergencia


router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'inventario', InventarioViewSet)
router.register(r'servicios', ServicioBellezaViewSet)
router.register(r'citas', CitaViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'abonos', AbonoViewSet)

urlpatterns = [   
     path('api/catalogo/', views_catalogo.productos_publicos, name='api_catalogo'),
    path('comprar/<int:pk>/', views_catalogo.comprar_producto, name='comprar_producto'),
    path('comprar/retorno/', views_catalogo.webpay_producto_retorno, name='webpay_producto_retorno'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', RedirectView.as_view(url='/segur/login/'), name='home'),
    # Rutas de la web
    path('menu/', LoadMenu.as_view()),
    path('mi-cuenta/', views_cliente.mi_cuenta, name='mi_cuenta'),
    path('mi-cuenta/horarios/', views_cliente.horarios, name='horarios_cita'),
    path('mi-cuenta/agendar/', views_cliente.agendar_cita, name='agendar_cita'),
    path('mi-cuenta/cancelar/<int:pk>/', views_cliente.cancelar_cita, name='cancelar_cita'),
    path('mi-cuenta/perfil/', views_cliente.editar_perfil, name='editar_perfil'),
    path('mi-cuenta/webpay/pagar/<int:pk>/', views_cliente.pagar_abono, name='pagar_abono'),   # NUEVO
    path('mi-cuenta/webpay/retorno/', views_cliente.webpay_retorno, name='webpay_retorno'),    # NUEVO
    path('panel/servicios/', views.admin_servicios, name='admin_servicios'),
    path('menu/', LoadMenu.as_view()),
    path('mi-cuenta/', views_cliente.mi_cuenta, name='mi_cuenta'),

    # Rutas del login de la abogada
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # CRUD
        # Usuarios (colaboradores)
    path('panel/gestionar/usuarios/', views_usuarios.usuarios_lista, name='usuarios_lista'),
    path('panel/gestionar/usuarios/nuevo/', views_usuarios.usuarios_editar, name='usuarios_nuevo'),
    path('panel/gestionar/usuarios/<int:pk>/editar/', views_usuarios.usuarios_editar, name='usuarios_editar'),
    path('panel/gestionar/usuarios/<int:pk>/borrar/', views_usuarios.usuarios_borrar, name='usuarios_borrar'),
    path('panel/gestionar/<str:clave>/', views_crud.crud_lista, name='crud_lista'),
    path('panel/gestionar/<str:clave>/nuevo/', views_crud.crud_editar, name='crud_editar'),
    path('panel/gestionar/<str:clave>/<int:pk>/editar/', views_crud.crud_editar, name='crud_editar'),
    path('panel/gestionar/<str:clave>/<int:pk>/borrar/', views_crud.crud_borrar, name='crud_borrar'),

    path('panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('panel/citas-hoy/', views.admin_citas_hoy, name='admin_citas_hoy'),
    path('panel/precios-promos/', views.admin_precios_promos, name='admin_precios_promos'),
    path('panel/cancelar-emergencia/', views_emergencia.cancelar_emergencia, name='cancelar_emergencia'),

    # Rutas de la API
    path('api/', include(router.urls)),
    path('segur/', include('segur.urls')),

    # Panel de la dueña
    path('panel-duena/', views_panel.panel_duena, name='panel_duena'),

    # Tokens
    path('apix/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('apix/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('apix/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Usuarios
    path('panel/usuarios/nuevo/', views_panel.ClienteCreate.as_view(), name='cliente_nuevo'),
    path('panel/usuarios/<int:pk>/editar/', views_panel.ClienteUpdate.as_view(), name='cliente_editar'),
    path('panel/usuarios/<int:pk>/borrar/', views_panel.ClienteDelete.as_view(), name='cliente_borrar'),

    # Citas
    path('panel/citas/nueva/', views_panel.CitaCreate.as_view(), name='cita_nueva'),
    path('panel/citas/<int:pk>/editar/', views_panel.CitaUpdate.as_view(), name='cita_editar'),
    path('panel/citas/<int:pk>/borrar/', views_panel.CitaDelete.as_view(), name='cita_borrar'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
]