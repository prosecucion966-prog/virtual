import re
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Programa, UnidadCurricular

SHEET_PROGRAMS = {
    "POLICIAL VIEJA": [("Servicio de Policía", "ANTERIOR")],
    "POLICIAL NUEVA": [("Servicio de Policía", "VIGENTE")],
    "INV PENAL VIEJA": [("Investigación Penal", "ANTERIOR")],
    "CRIMINALÍSTICA VIEJA": [("Criminalística", "ANTERIOR")],
    "IP Y CRIM NUEVA": [
        ("Investigación Penal", "VIGENTE"),
        ("Criminalística", "VIGENTE"),
    ],
    "SERV PENIT": [("Servicios Penitenciarios", "ANTERIOR")],
    "BOMBERIL": [("Ciencias de Fuego y Seguridad Contra Incendios", "ANTERIOR")],
    "PCAD": [("Protección Civil y Administración de Desastres", "ANTERIOR")],
    "SEG NACION": [("Seguridad de la Nación", "ANTERIOR")],
    "EMERGENCIA PREH": [("Emergencia Prehospitalarias", "ANTERIOR")],
}


def _clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _number(value):
    if value is None or _clean(value) in ("", "-", "—"):
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else None
    except (TypeError, ValueError):
        return None


def _parse_sheet(ws):
    sheet = ws.title.strip().upper()
    units = []
    current_trayecto = "No especificado"
    is_new_format = sheet in ("POLICIAL NUEVA", "IP Y CRIM NUEVA")

    for row_number, values in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = list(values)
        first = _clean(cells[0] if cells else "")
        nonempty = [_clean(v) for v in cells if _clean(v)]

        if not nonempty:
            continue

        trayecto_cell = next((v for v in nonempty if "TRAYECTO" in v.upper()), "")
        if trayecto_cell:
            current_trayecto = trayecto_cell.title()
            if "INICIAL" in trayecto_cell.upper():
                current_trayecto = "Trayecto de formación inicial"
            continue

        if any("UNIDADES CURRICULARES" in v.upper() for v in nonempty):
            continue
        if first.upper() in ("TOTAL", "TSU", "LICENCIATURA"):
            continue

        if is_new_format:
            if len(cells) < 2:
                continue
            code = first.upper()
            name = _clean(cells[1])
            if not re.fullmatch(r"[A-Z0-9]{5,12}", code) or not name:
                continue
            if sheet == "POLICIAL NUEVA":
                uc = _number(cells[3] if len(cells) > 3 else None)
                weekly = _number(cells[6] if len(cells) > 6 else None)
                total = _number(cells[9] if len(cells) > 9 else None)
                prereq = _clean(cells[13] if len(cells) > 13 else "")
                details = {"horas_semanales": weekly, "horas_totales": total, "prelacion": prereq}
            else:
                uc = _number(cells[2] if len(cells) > 2 else None)
                total = _number(cells[3] if len(cells) > 3 else None)
                hta = _number(cells[4] if len(cells) > 4 else None)
                hti = _number(cells[5] if len(cells) > 5 else None)
                prereq = _clean(cells[6] if len(cells) > 6 else "")
                details = {"horas_totales": total, "hta": hta, "hti": hti, "prelacion": prereq}
            units.append({
                "row": row_number, "code": code, "name": name,
                "trayecto": current_trayecto, "uc": uc, **details,
                "raw": [_clean(v) for v in cells if _clean(v)],
            })
            continue

        # Formato anterior: nombre, UC (cuando existe), horas, acreditables/electivas.
        if not first or first.upper() in ("TOTAL", "UNIDADES CURRICULARES", "UNIDAD CURRICULAR"):
            continue
        if first.upper().startswith(("MALLA CURRICULAR", "TRAYECTO", "PROGRAMA NACIONAL")):
            continue
        if len(cells) < 2:
            continue

        numeric = [_number(v) for v in cells[1:]]
        numeric = [n for n in numeric if n is not None]
        if not numeric:
            continue

        # El trayecto inicial suele tener solo horas; los trayectos regulares tienen UC y horas.
        if len(numeric) == 1:
            uc, total = 0, numeric[0]
        else:
            uc, total = numeric[0], numeric[1]
        accreditation = _clean(cells[3] if len(cells) > 3 else "")
        electives = _clean(cells[4] if len(cells) > 4 else "")
        units.append({
            "row": row_number,
            "code": f"{re.sub(r'[^A-Z0-9]', '', sheet)[:12]}-{row_number:03d}",
            "name": first[:180],
            "trayecto": current_trayecto,
            "uc": uc,
            "horas_totales": total,
            "horas_semanales": None,
            "prelacion": "",
            "unidades_acreditables": accreditation,
            "unidades_electivas": electives,
            "raw": [_clean(v) for v in cells if _clean(v)],
        })
    return units


@transaction.atomic
def import_workbook(workbook):
    summary = {"created": 0, "updated": 0, "skipped": 0, "by_sheet": {}, "warnings": []}
    programs = {p.nombre: p for p in Programa.objects.all()}
    for ws in workbook.worksheets:
        sheet = ws.title.strip().upper()
        mapping = SHEET_PROGRAMS.get(sheet)
        if not mapping:
            summary["warnings"].append(f"Hoja no reconocida: {ws.title}")
            summary["skipped"] += 1
            continue
        parsed = _parse_sheet(ws)
        sheet_created = sheet_updated = 0
        if not parsed:
            summary["warnings"].append(f"No se detectaron unidades en la hoja {ws.title}")
        for program_name, version in mapping:
            program = programs.get(program_name)
            if not program:
                summary["warnings"].append(f"No existe el programa «{program_name}» para la hoja {ws.title}")
                summary["skipped"] += len(parsed)
                continue
            for item in parsed:
                defaults = {
                    "nombre": item["name"],
                    "trayecto": item["trayecto"][:80],
                    "unidades_credito": item.get("uc") or 0,
                    "horas_semanales": item.get("horas_semanales"),
                    "horas_totales": item.get("horas_totales"),
                    "datos_malla": {
                        "fila_excel": item["row"],
                        "codigo_original": item["code"] if is_original_code(item["code"], sheet) else "",
                        "prelacion": item.get("prelacion", ""),
                        "hta": item.get("hta"),
                        "hti": item.get("hti"),
                        "unidades_acreditables": item.get("unidades_acreditables", ""),
                        "unidades_electivas": item.get("unidades_electivas", ""),
                        "fila_original": item["raw"],
                    },
                    "fuente_malla": ws.title[:120],
                    "activa": True,
                }
                obj, created = UnidadCurricular.objects.update_or_create(
                    programa=program, codigo=item["code"][:40], version_malla=version,
                    defaults=defaults,
                )
                if created:
                    sheet_created += 1
                else:
                    sheet_updated += 1
        summary["created"] += sheet_created
        summary["updated"] += sheet_updated
        summary["by_sheet"][ws.title] = {"unidades": len(parsed), "creadas": sheet_created, "actualizadas": sheet_updated}
    return summary


def is_original_code(code, sheet):
    return sheet in ("POLICIAL NUEVA", "IP Y CRIM NUEVA")
