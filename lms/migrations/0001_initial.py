# Generated for the UNES virtual campus foundation.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Nucleo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120, unique=True)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={"ordering": ["nombre"]},
        ),
        migrations.CreateModel(
            name="Programa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("categoria", models.CharField(choices=[("PNF", "PNF"), ("PNFA", "PNFA"), ("PFG", "PFG")], max_length=12)),
                ("nombre", models.CharField(max_length=180, unique=True)),
                ("nivel", models.CharField(blank=True, max_length=30)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={"ordering": ["categoria", "nombre"]},
        ),
        migrations.CreateModel(
            name="Dependencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=180, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cedula", models.CharField(max_length=12, unique=True, validators=[RegexValidator("^[VE]-?\\d{5,10}$", "Use V/E seguido de 5 a 10 dígitos.")])),
                ("genero", models.CharField(blank=True, max_length=20)),
                ("telefono", models.CharField(max_length=20)),
                ("tipo_estudiante", models.CharField(choices=[("PNF", "Estudiante PNF"), ("PNFA", "Estudiante PNFA"), ("PFG", "Estudiante PFG"), ("DOCENTE", "Docente"), ("ADMIN", "Personal Administrativo")], max_length=10)),
                ("programa_detalle", models.CharField(blank=True, max_length=200)),
                ("nivel_pnfa", models.CharField(blank=True, max_length=30)),
                ("rol", models.CharField(choices=[("student", "Estudiante"), ("teacher", "Docente"), ("nucleus_admin", "Administrador de núcleo"), ("staff", "Personal administrativo"), ("superadmin", "Superadministrador")], default="student", max_length=20)),
                ("estado", models.CharField(choices=[("pendiente_verificacion", "Pendiente de verificación"), ("activo", "Activo"), ("suspendido", "Suspendido")], default="pendiente_verificacion", max_length=30)),
                ("verificado", models.DateTimeField(blank=True, null=True)),
                ("dependencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="lms.dependencia")),
                ("nucleo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="perfiles", to="lms.nucleo")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("codigo", models.CharField(max_length=30, unique=True)),
                ("descripcion", models.TextField(blank=True)),
                ("periodo", models.CharField(blank=True, max_length=80)),
                ("clave_matricula", models.CharField(blank=True, max_length=32)),
                ("publicado", models.BooleanField(default=False)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("docente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cursos_docente", to=settings.AUTH_USER_MODEL)),
                ("nucleo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cursos", to="lms.nucleo")),
                ("programa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="lms.programa")),
            ],
        ),
        migrations.CreateModel(
            name="Section",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("contenido", models.TextField(blank=True)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("curso", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="secciones", to="lms.course")),
            ],
            options={"ordering": ["orden"]},
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("tipo", models.CharField(choices=[("file", "Archivo"), ("link", "Enlace"), ("video", "Video"), ("page", "Página")], max_length=12)),
                ("archivo", models.FileField(blank=True, upload_to="recursos/%Y/%m/")),
                ("url", models.URLField(blank=True)),
                ("contenido", models.TextField(blank=True)),
                ("seccion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recursos", to="lms.section")),
            ],
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("tipo", models.CharField(choices=[("Tarea", "Tarea"), ("Taller", "Taller"), ("Foro", "Foro"), ("Cuestionario", "Cuestionario"), ("Wiki", "Wiki"), ("Glosario", "Glosario"), ("Encuesta", "Encuesta"), ("Clase", "Clase")], max_length=24)),
                ("instrucciones", models.TextField(blank=True)),
                ("fecha_limite", models.DateTimeField(blank=True, null=True)),
                ("puntos", models.DecimalField(decimal_places=2, default=100, max_digits=7)),
                ("publicado", models.BooleanField(default=False)),
                ("curso", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actividades", to="lms.course")),
            ],
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("texto", models.TextField(blank=True)),
                ("archivo", models.FileField(blank=True, upload_to="entregas/%Y/%m/")),
                ("entregada", models.DateTimeField(default=django.utils.timezone.now)),
                ("actividad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entregas", to="lms.activity")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Grade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("puntos", models.DecimalField(decimal_places=2, max_digits=7)),
                ("retroalimentacion", models.TextField(blank=True)),
                ("docente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("entrega", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="nota", to="lms.submission")),
            ],
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("activo", models.BooleanField(default=True)),
                ("curso", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matriculas", to="lms.course")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matriculas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("curso", "estudiante"), name="uq_curso_estudiante")]},
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("cuerpo", models.TextField()),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("autor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("nucleo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="lms.nucleo")),
            ],
        ),
        migrations.CreateModel(
            name="CalendarEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("descripcion", models.TextField(blank=True)),
                ("inicio", models.DateTimeField()),
                ("creado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("nucleo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="lms.nucleo")),
                ("programa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="lms.programa")),
            ],
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asunto", models.CharField(max_length=180)),
                ("cuerpo", models.TextField()),
                ("leido", models.DateTimeField(blank=True, null=True)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("destinatario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recibidos", to=settings.AUTH_USER_MODEL)),
                ("remitente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enviados", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("cuerpo", models.TextField(blank=True)),
                ("leida", models.BooleanField(default=False)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accion", models.CharField(max_length=120)),
                ("detalle", models.CharField(blank=True, max_length=250)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
