from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
class Nucleo(models.Model):
 nombre=models.CharField(max_length=120,unique=True)
 activo=models.BooleanField(default=True)
 class Meta: ordering=["nombre"]
 def __str__(self): return self.nombre
class Programa(models.Model):
 categoria=models.CharField(max_length=12,choices=[("PNF","PNF"),("PNFA","PNFA"),("PFG","PFG")])
 nombre=models.CharField(max_length=180,unique=True)
 nivel=models.CharField(max_length=30,blank=True)
 activo=models.BooleanField(default=True)
 class Meta: ordering=["categoria","nombre"]
 def __str__(self): return self.nombre
class Dependencia(models.Model):
 nombre=models.CharField(max_length=180,unique=True)
 def __str__(self): return self.nombre
class Profile(models.Model):
 TYPES=[("PNF","Estudiante PNF"),("PNFA","Estudiante PNFA"),("PFG","Estudiante PFG"),("DOCENTE","Docente"),("ADMIN","Personal Administrativo")]
 ROLES=[("student","Estudiante"),("teacher","Docente"),("nucleus_admin","Administrador de núcleo"),("staff","Personal administrativo"),("superadmin","Superadministrador")]
 STATUS=[("pendiente_verificacion","Pendiente de verificación"),("activo","Activo"),("suspendido","Suspendido")]
 user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="profile")
 cedula=models.CharField(max_length=12,unique=True,validators=[RegexValidator(r"^[VE]-?\d{5,10}$","Use V/E seguido de 5 a 10 dígitos.")])
 genero=models.CharField(max_length=20,blank=True)
 telefono=models.CharField(max_length=20)
 tipo_estudiante=models.CharField(max_length=10,choices=TYPES)
 programa_detalle=models.CharField(max_length=200,blank=True)
 nivel_pnfa=models.CharField(max_length=30,blank=True)
 nucleo=models.ForeignKey(Nucleo,on_delete=models.PROTECT,related_name="perfiles")
 dependencia=models.ForeignKey(Dependencia,null=True,blank=True,on_delete=models.SET_NULL)
 rol=models.CharField(max_length=20,choices=ROLES,default="student")
 estado=models.CharField(max_length=30,choices=STATUS,default="pendiente_verificacion")
 verificado=models.DateTimeField(null=True,blank=True)
 def __str__(self): return f"{self.user.get_full_name()} · {self.cedula}"
class Course(models.Model):
 titulo=models.CharField(max_length=180)
 codigo=models.CharField(max_length=30,unique=True)
 descripcion=models.TextField(blank=True)
 programa=models.ForeignKey(Programa,null=True,blank=True,on_delete=models.SET_NULL)
 unidad_curricular=models.ForeignKey("UnidadCurricular",null=True,blank=True,on_delete=models.SET_NULL,related_name="aulas")
 nucleo=models.ForeignKey(Nucleo,on_delete=models.PROTECT,related_name="cursos")
 docente=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="cursos_docente")
 periodo=models.CharField(max_length=80,blank=True)
 clave_matricula=models.CharField(max_length=32,blank=True)
 publicado=models.BooleanField(default=False)
 creado=models.DateTimeField(auto_now_add=True)
 def __str__(self): return f"{self.codigo} · {self.titulo}"
class Enrollment(models.Model):
 curso=models.ForeignKey(Course,on_delete=models.CASCADE,related_name="matriculas")
 estudiante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="matriculas")
 fecha=models.DateTimeField(auto_now_add=True)
 activo=models.BooleanField(default=True)
 class Meta: constraints=[models.UniqueConstraint(fields=["curso","estudiante"],name="uq_curso_estudiante")]
class Section(models.Model):
 curso=models.ForeignKey(Course,on_delete=models.CASCADE,related_name="secciones")
 titulo=models.CharField(max_length=180)
 contenido=models.TextField(blank=True)
 orden=models.PositiveSmallIntegerField(default=0)
 class Meta: ordering=["orden"]
class Resource(models.Model):
 seccion=models.ForeignKey(Section,on_delete=models.CASCADE,related_name="recursos")
 titulo=models.CharField(max_length=180)
 tipo=models.CharField(max_length=12,choices=[("file","Archivo"),("link","Enlace"),("video","Video"),("page","Página")])
 archivo=models.FileField(upload_to="recursos/%Y/%m/",blank=True)
 url=models.URLField(blank=True)
 contenido=models.TextField(blank=True)
class Activity(models.Model):
 curso=models.ForeignKey(Course,on_delete=models.CASCADE,related_name="actividades")
 titulo=models.CharField(max_length=180)
 tipo=models.CharField(max_length=24,choices=[("Tarea","Tarea"),("Taller","Taller"),("Foro","Foro"),("Cuestionario","Cuestionario"),("Wiki","Wiki"),("Glosario","Glosario"),("Encuesta","Encuesta"),("Clase","Clase")])
 instrucciones=models.TextField(blank=True)
 fecha_limite=models.DateTimeField(null=True,blank=True)
 puntos=models.DecimalField(max_digits=7,decimal_places=2,default=100)
 publicado=models.BooleanField(default=False)
class Submission(models.Model):
 actividad=models.ForeignKey(Activity,on_delete=models.CASCADE,related_name="entregas")
 estudiante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 texto=models.TextField(blank=True)
 archivo=models.FileField(upload_to="entregas/%Y/%m/",blank=True)
 entregada=models.DateTimeField(default=timezone.now)
class Grade(models.Model):
 entrega=models.OneToOneField(Submission,on_delete=models.CASCADE,related_name="nota")
 puntos=models.DecimalField(max_digits=7,decimal_places=2)
 retroalimentacion=models.TextField(blank=True)
 docente=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
class Announcement(models.Model):
 titulo=models.CharField(max_length=180)
 cuerpo=models.TextField()
 nucleo=models.ForeignKey(Nucleo,null=True,blank=True,on_delete=models.CASCADE)
 autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
 creado=models.DateTimeField(auto_now_add=True)
class CalendarEvent(models.Model):
 titulo=models.CharField(max_length=180)
 descripcion=models.TextField(blank=True)
 inicio=models.DateTimeField()
 nucleo=models.ForeignKey(Nucleo,null=True,blank=True,on_delete=models.CASCADE)
 programa=models.ForeignKey(Programa,null=True,blank=True,on_delete=models.CASCADE)
 creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
class Message(models.Model):
 remitente=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="enviados")
 destinatario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="recibidos")
 asunto=models.CharField(max_length=180)
 cuerpo=models.TextField()
 leido=models.DateTimeField(null=True,blank=True)
 creado=models.DateTimeField(auto_now_add=True)
class Notification(models.Model):
 usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 titulo=models.CharField(max_length=180)
 cuerpo=models.TextField(blank=True)
 leida=models.BooleanField(default=False)
 creado=models.DateTimeField(auto_now_add=True)
class AuditLog(models.Model):
 actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL)
 accion=models.CharField(max_length=120)
 detalle=models.CharField(max_length=250,blank=True)
 creado=models.DateTimeField(auto_now_add=True)

class UnidadCurricular(models.Model):
    VERSIONES = [
        ("UNICA", "Malla única"),
        ("ANTERIOR", "Malla anterior"),
        ("VIGENTE", "Malla vigente"),
    ]
    MODALIDADES = [
        ("presencial", "Presencial"),
        ("virtual", "Virtual"),
        ("mixta", "Mixta"),
    ]
    programa = models.ForeignKey(Programa, on_delete=models.PROTECT, related_name="unidades_curriculares")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=180)
    version_malla = models.CharField(max_length=20, choices=VERSIONES, default="VIGENTE")
    trayecto = models.CharField(max_length=80, blank=True)
    semestre = models.CharField(max_length=40, blank=True)
    unidades_credito = models.PositiveSmallIntegerField(default=0)
    horas_semanales = models.PositiveSmallIntegerField(null=True, blank=True)
    horas_totales = models.PositiveSmallIntegerField(null=True, blank=True)
    datos_malla = models.JSONField(default=dict, blank=True)
    fuente_malla = models.CharField(max_length=120, blank=True)
    duracion_semanas = models.PositiveSmallIntegerField(null=True, blank=True, default=None)
    modalidad = models.CharField(max_length=12, choices=MODALIDADES, default="mixta")
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["programa__nombre", "trayecto", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["programa", "codigo", "version_malla"],
                name="uq_uc_programa_codigo_version",
            )
        ]

    def __str__(self):
        return f"{self.programa.nombre} · {self.codigo} · {self.nombre}"


class TeachingAssignment(models.Model):
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="asignaciones_docentes",
    )
    nucleo = models.ForeignKey(
        Nucleo, on_delete=models.PROTECT, related_name="asignaciones_docentes",
    )
    unidad_curricular = models.ForeignKey(
        UnidadCurricular, on_delete=models.PROTECT,
        related_name="asignaciones_docentes",
    )
    periodo = models.CharField(max_length=80)
    aula = models.OneToOneField(
        Course, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="asignacion_docente",
    )
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["docente__last_name", "unidad_curricular__programa__nombre", "unidad_curricular__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["docente", "nucleo", "unidad_curricular", "periodo"],
                name="uq_docente_nucleo_uc_periodo",
            )
        ]

    def __str__(self):
        return f"{self.docente.get_full_name()} · {self.unidad_curricular.nombre} · {self.nucleo.nombre}"
