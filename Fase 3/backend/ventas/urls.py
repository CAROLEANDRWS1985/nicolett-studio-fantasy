from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve
from . import views_catalogo
#from django.contrib import admin
from django.urls import path
from . import views_backend
from . import views_restfull
# from . import views_soap
from . import views_load
from . import views_panel
from . import views_cuenta
from rest_framework_simplejwt import views as jwt_views
urlpatterns = [
    # path('hijo_ventas/', admin.site.urls),
    path('indexharrys/', views_backend.indexHarrys),
    path('load/', views_load.LoadData.as_view()),

    path('backend/genero/',  views_backend.GeneroList.as_view()),
    path('backend/region/',  views_backend.RegionList.as_view()),
    path('backend/provincia/<int:region>',  views_backend.ProvinciaList.as_view()),
    path('backend/comuna/<int:provincia>',  views_backend.ComunaList.as_view()),
    path('backend/persona/', views_backend.PersonaList.as_view()),
    path('backend/persona/<int:pk>', views_backend.PersonaDetail.as_view()),


    path('backend/cliente/', views_backend.ClienteList.as_view()),
    path('backend/cliente/<int:rut>', views_backend.ClienteDetail.as_view()),
    #path('backend/login/', views_backend.ClienteDetail.as_view()),

    #  BackEnd Oficial


    #  RestFull
    path('restfull/region/', views_restfull.rf_region),  
    path('restfull/region/<int:cod_region>', views_restfull.rf_region_pk),

    path('restfull/region_load', views_restfull.rf_load_region),


    # path('soap_service/', views_soap.my_soap_application),
    # path('soap_service_harrys/', views_soap.pruebaHarrys),
    # path('soap_service_persona/', views_soap.crud_persona),
    # path('soap_service_consumir/', views_soap.SoapList.as_view()),


    path('pelu/productos/',  views_backend.Pelu_ProductosList.as_view()),
    path('pelu/productos/<int:pk>',  views_backend.Pelu_ProductosDetail.as_view()),

    path('pelu/carrito/', views_backend.Pelu_CarritoList.as_view()),
    path('pelu/carrito/<int:pk>', views_backend.Pelu_CarritoDetail.as_view()),

    path('pelu/masajes/',  views_backend.Pelu_MasajesList.as_view()),
    path('pelu/masajes/<int:pk>',  views_backend.Pelu_MasajesDetail.as_view()),

    path('pelu/coloracion/',  views_backend.ColoracionList.as_view()),
    path('pelu/coloracion/<int:pk>',  views_backend.ColoracionDetail.as_view()),

    path('pelu/depilacion/',  views_backend.DepilacionList.as_view()),
    path('pelu/depilacion/<int:pk>',  views_backend.DepilacionDetail.as_view()),

    path('pelu/unas/',  views_backend.UnasList.as_view()),
    path('pelu/unas/<int:pk>',  views_backend.UnasDetail.as_view()),

    path('panel-duena/', views_panel.panel_duena, name='panel_duena'),

    # --- CRUD de Servicios ---
    path('panel/servicios/', views_panel.ServicioList.as_view(), name='servicios_lista'),
    path('panel/servicios/nuevo/', views_panel.ServicioCreate.as_view(), name='servicio_nuevo'),
    path('panel/servicios/<int:pk>/editar/', views_panel.ServicioUpdate.as_view(), name='servicio_editar'),
    path('panel/servicios/<int:pk>/borrar/', views_panel.ServicioDelete.as_view(), name='servicio_borrar'),

    # --- Portal de la clienta (NUEVO) ---
    path('mi-cuenta/', views_cuenta.mi_cuenta, name='mi_cuenta'),
    path('mi-cuenta/horarios/', views_cuenta.horarios, name='horarios'),
    path('mi-cuenta/agendar/', views_cuenta.agendar_cita, name='agendar_cita'),
    path('mi-cuenta/cancelar/<int:pk>/', views_cuenta.cancelar_cita, name='cancelar_cita'),
    path('mi-cuenta/perfil/', views_cuenta.editar_perfil, name='editar_perfil'),

    # --- Avisos para la dueña (NUEVO) ---
    path('panel/avisos/', views_cuenta.panel_avisos, name='panel_avisos'),
        # --- Productos para la página pública ---
    path('api/catalogo/', views_catalogo.productos_publicos, name='api_catalogo'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]