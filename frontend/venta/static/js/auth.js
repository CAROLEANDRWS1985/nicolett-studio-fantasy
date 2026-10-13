const API_BACKEND = 'http://127.0.0.1:8000';

// Registro de usuario
async function registrarUsuario(username, email, password) {
  const respuesta = await fetch(`${API_BACKEND}/segur/registro/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password })
  });
  const datos = await respuesta.json();
  if (respuesta.ok) {
    alert('Cuenta creada correctamente');
  } else {
    alert('Error al crear la cuenta: ' + JSON.stringify(datos));
  }
}

// Inicio de sesión
async function iniciarSesion(username, password) {
  const respuesta = await fetch(`${API_BACKEND}/segur/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const datos = await respuesta.json();
  if (respuesta.ok) {
    localStorage.setItem('access', datos.access);
    localStorage.setItem('refresh', datos.refresh);
    alert('Sesión iniciada correctamente');
  } else {
    alert('Usuario o contraseña incorrectos');
  }
}