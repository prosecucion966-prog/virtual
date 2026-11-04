from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from lms.curriculum_import import import_workbook


class Command(BaseCommand):
    help = "Importa de forma idempotente las unidades curriculares desde el libro Excel UNES."

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=str, help="Ruta al archivo .xlsx de las mallas.")

    def handle(self, *args, **options):
        path = Path(options["archivo"])
        if not path.is_file() or path.suffix.lower() != ".xlsx":
            raise CommandError("Indica una ruta válida a un archivo .xlsx.")
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
            try:
                result = import_workbook(workbook)
            finally:
                workbook.close()
        except Exception as exc:
            raise CommandError(f"No se pudo importar el libro: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            f"Importación finalizada: {result['created']} creadas, "
            f"{result['updated']} actualizadas y {result['skipped']} omitidas."
        ))
        for sheet, counts in result["by_sheet"].items():
            self.stdout.write(
                f"{sheet}: {counts['unidades']} filas, "
                f"{counts['creadas']} nuevas, {counts['actualizadas']} actualizadas"
            )
        for warning in result["warnings"]:
            self.stderr.write(self.style.WARNING(warning))
