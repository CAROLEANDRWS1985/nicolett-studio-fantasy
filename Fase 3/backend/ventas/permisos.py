from django.contrib.auth.decorators import user_passes_test

solo_equipo = user_passes_test(lambda u: u.is_active and u.is_staff, login_url='/admin-login/')
