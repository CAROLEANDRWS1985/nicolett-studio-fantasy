from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Recuperación de clave
    path('recuperar-clave/', auth_views.PasswordResetView.as_view(
        template_name='ventas/recuperar_clave.html'), name='password_reset'),
    path('recuperar-clave/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='ventas/recuperar_enviado.html'), name='password_reset_done'),
    path('recuperar-clave/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='ventas/nueva_clave.html'), name='password_reset_confirm'),
    path('recuperar-clave/listo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='ventas/clave_lista.html'), name='password_reset_complete'),
]