from rest_framework import permissions


class SoloEquipo(permissions.BasePermission):
    """Solo cuentas del equipo (is_staff o superusuario)."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


class LecturaPublica(permissions.BasePermission):
    """Cualquiera puede ver; solo el equipo puede crear, modificar o borrar."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return SoloEquipo().has_permission(request, view)