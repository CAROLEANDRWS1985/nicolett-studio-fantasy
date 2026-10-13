from .models import *
class Negocio:
    # Metodos Státicos no necesitan ==> self
    def get_viewcliente( rut):
        try:
            return ViewCliente.objects.get(pk=rut)
        except ViewCliente.DoesNotExist:
            raise None
    def get_cliente( rut):
        try:
            return Cliente.objects.get(pk=rut)
        except Cliente.DoesNotExist:
            return None             
    def get_persona( rut):
        try:
            return Persona.objects.get(pk=rut)
        except Persona.DoesNotExist:
            return None       
    def get_usuario( usuario):
        try:
            usuarios = Usuario.objects.filter(usuario=usuario)
            if (usuarios.count()> 0):
                return usuarios[0]
            else:
                return None
        except Usuario.DoesNotExist:
            return None
               
    def clienteCrear(rut,dv,nombres,paterno,materno,email,comuna,genero):
        persona = Negocio.get_persona(int(rut))
        cliente = Negocio.get_cliente(rut)
        usuario = Negocio.get_usuario(rut)
        if (persona== None):
            persona =  Persona(rut,dv,nombres,paterno,materno,email,'2023-01-01','2023-01-01',comuna,genero,1)
        else:
            persona.nombre=nombres

        # No tienen mucho sentido solo es para el ejemplo
        if (cliente== None):
            cliente = Cliente(rut,None,'2023-01-01',0)
        if (usuario== None):
            usuario = Usuario(None,rut,rut,rut)
        persona.save()
        cliente.save()
        usuario.save()
        return True


    def clienteGet(rut):
        return Negocio.get_viewcliente(rut)
    
    def clienteEliminar(rut):
        persona = Negocio.get_persona(int(rut))
        cliente = Negocio.get_cliente(rut)
        usuario = Negocio.get_usuario(rut)
        ###  Recuerde que no debiera eliminar, mejor desactivar el registro
        usuario.delete()
        cliente.delete()
        persona.delete()    