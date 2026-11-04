from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lms", "0002_unidad_curricular"),
    ]

    operations = [
        migrations.AddField(
            model_name="unidadcurricular",
            name="horas_totales",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unidadcurricular",
            name="datos_malla",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="unidadcurricular",
            name="fuente_malla",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name="unidadcurricular",
            name="trayecto",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AlterField(
            model_name="unidadcurricular",
            name="duracion_semanas",
            field=models.PositiveSmallIntegerField(blank=True, default=None, null=True),
        ),
    ]
