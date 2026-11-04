import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lms", "0003_malla_metadata"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TeachingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("periodo", models.CharField(max_length=80)),
                ("activa", models.BooleanField(default=True)),
                ("creada", models.DateTimeField(auto_now_add=True)),
                ("aula", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asignacion_docente", to="lms.course")),
                ("docente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_docentes", to=settings.AUTH_USER_MODEL)),
                ("nucleo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_docentes", to="lms.nucleo")),
                ("unidad_curricular", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_docentes", to="lms.unidadcurricular")),
            ],
            options={
                "ordering": ["docente__last_name", "unidad_curricular__programa__nombre", "unidad_curricular__nombre"],
            },
        ),
        migrations.AddConstraint(
            model_name="teachingassignment",
            constraint=models.UniqueConstraint(fields=("docente", "nucleo", "unidad_curricular", "periodo"), name="uq_docente_nucleo_uc_periodo"),
        ),
    ]
