import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from lms.models import Programa, UnidadCurricular


class Command(BaseCommand):
    help = "Carga de forma idempotente el pensum de Derecho (8 semestres)."

    @transaction.atomic
    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[2] / "data" / "malla_derecho.json"
        with data_path.open(encoding="utf-8") as source:
            data = json.load(source)

        programa = Programa.objects.get(nombre=data["programa"])
        if programa.categoria != data["categoria"]:
            raise ValueError(
                f"El programa Derecho existe con categoría {programa.categoria}; "
                "no se modificó su clasificación."
            )

        roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
        created = updated = 0
        for semester in data["semestres"]:
            numeral = semester["semestre"]
            semester_number = roman.index(numeral) + 1
            for index, name in enumerate(semester["unidades"], start=1):
                code = f"DER-S{semester_number:02d}-{index:02d}"
                defaults = {
                    "nombre": name,
                    "trayecto": f"Semestre {numeral}",
                    "semestre": numeral,
                    "unidades_credito": 0,
                    "horas_semanales": None,
                    "horas_totales": None,
                    "duracion_semanas": None,
                    "version_malla": data["version"],
                    "modalidad": "mixta",
                    "descripcion": "",
                    "datos_malla": {
                        "semestre": numeral,
                        "orden": index,
                        "creditos_no_suministrados": True,
                        "horas_no_suministradas": True,
                        "codigo_generado": True,
                        "fuente": "Pensum Académico: Derecho proporcionado por la institución",
                    },
                    "fuente_malla": "Pensum Académico: Derecho",
                    "activa": True,
                }
                _, was_created = UnidadCurricular.objects.update_or_create(
                    programa=programa,
                    codigo=code,
                    version_malla=data["version"],
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        total = sum(len(item["unidades"]) for item in data["semestres"])
        self.stdout.write(self.style.SUCCESS(
            f"Derecho: {total} unidades curriculares. "
            f"{created} creadas, {updated} actualizadas."
        ))
