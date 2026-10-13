from django.db import models

# Create your models here.
class MensajeContacto(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField()
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.asunto}"