# Generated for administrative curriculum management.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnidadCurricular",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=40)),
                ("nombre", models.CharField(max_length=180)),
                ("version_malla", models.CharField(choices=[("UNICA", "Malla única"), ("ANTERIOR", "Malla anterior"), ("VIGENTE", "Malla vigente")], default="VIGENTE", max_length=20)),
                ("trayecto", models.CharField(blank=True, max_length=40)),
                ("semestre", models.CharField(blank=True, max_length=40)),
                ("unidades_credito", models.PositiveSmallIntegerField(default=0)),
                ("horas_semanales", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("duracion_semanas", models.PositiveSmallIntegerField(default=16)),
                ("modalidad", models.CharField(choices=[("presencial", "Presencial"), ("virtual", "Virtual"), ("mixta", "Mixta")], default="mixta", max_length=12)),
                ("descripcion", models.TextField(blank=True)),
                ("activa", models.BooleanField(default=True)),
                ("creada", models.DateTimeField(auto_now_add=True)),
                ("programa", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="unidades_curriculares", to="lms.programa")),
            ],
            options={"ordering": ["programa__nombre", "trayecto", "nombre"]},
        ),
        migrations.AddConstraint(
            model_name="unidadcurricular",
            constraint=models.UniqueConstraint(fields=("programa", "codigo", "version_malla"), name="uq_uc_programa_codigo_version"),
        ),
        migrations.AddField(
            model_name="course",
            name="unidad_curricular",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="aulas", to="lms.unidadcurricular"),
        ),
    ]
