from django.contrib import admin
from django.urls import path
#importar app con mis vistas
from venta import views

urlpatterns = [
    path('peluqueria', admin.site.urls),
    path('index', views.index, name='index'),
    path('acercade', views.acercade),
    path('inicio', views.inicio),
    path('login', views.login_view, name='login'),
    path('registro', views.registro, name='registro'),
    path('logout', views.logout_view, name='logout'),
    path('carro', views.carro),
    path('productos', views.productos),
    path('masajes', views.masajes),
    path('coloracion', views.coloracion),
    path('depilacion', views.depilacion),
    path('unas', views.unas),
]