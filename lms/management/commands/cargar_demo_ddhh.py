import json
import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from lms.models import (
    Activity, Announcement, CalendarEvent, Course, Enrollment, Grade, Message, Nucleo,
    Profile, Programa, Resource, Section, Submission,
)

DEMO_GROUP = "DEMO_DDHH_FIXTURES"
TEACHER_EMAIL = "docente.ddhh@demo.unes.local"
TEACHER_CEDULA = "V-00000001"
COURSE_CODE = "DDHH-DEMO-2026"
NUCLEI = ("Caracas", "Maracay", "Valencia", "Barquisimeto")


class Command(BaseCommand):
    help = "Carga un curso demostrativo de Derechos Humanos con datos ficticios."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Elimina exclusivamente los datos marcados de esta demo.")

    def handle(self, *args, **options):
        if options["borrar"]:
            self.delete_demo()
            return
        password = os.environ.get("DEMO_DDHH_PASSWORD", "").strip()
        if len(password) < 10:
            raise CommandError("Define DEMO_DDHH_PASSWORD en el entorno con al menos 10 caracteres. No se usa una clave por defecto.")
        data_path = Path(__file__).resolve().parents[2] / "data" / "demo_ddhh.json"
        if not data_path.exists():
            raise CommandError(f"No se encontró el archivo de datos: {data_path}")
        data = json.loads(data_path.read_text(encoding="utf-8"))
        with transaction.atomic():
            group, _ = Group.objects.get_or_create(name=DEMO_GROUP)
            nuclei = {name: Nucleo.objects.get_or_create(nombre=name, defaults={"activo": True})[0] for name in NUCLEI}
            program = Programa.objects.filter(nombre="Derecho", categoria="PFG").first()
            if not program:
                name = "Derecho" if not Programa.objects.filter(nombre="Derecho").exists() else "Derecho (Demo PFG)"
                program, _ = Programa.objects.get_or_create(nombre=name, defaults={"categoria": "PFG", "nivel": "Pregrado", "activo": True})
            teacher = self.get_demo_user(group, TEACHER_EMAIL, TEACHER_CEDULA, "Carmen Elena", "Rondón Palacios", nuclei["Caracas"], "DOCENTE", "teacher", password)
            teacher.profile.programa_detalle = "Perfil ficticio de demostración: abogada, especialista en Derechos Humanos y Seguridad Ciudadana."
            teacher.profile.save(update_fields=["programa_detalle"])
            existing_course = Course.objects.filter(codigo=COURSE_CODE).select_related("docente").first()
            if existing_course and existing_course.docente_id != teacher.id:
                if not existing_course.docente.groups.filter(pk=group.pk).exists():
                    raise CommandError(f"Ya existe el código reservado {COURSE_CODE} asociado a una cuenta que no pertenece a esta demo; no se modificó.")
            course, _ = Course.objects.get_or_create(codigo=COURSE_CODE, defaults={
                "titulo": data["course"]["title"], "docente": teacher, "nucleo": nuclei["Caracas"], "programa": program,
            })
            course.titulo = data["course"]["title"]
            course.docente = teacher
            course.nucleo = nuclei["Caracas"]
            course.programa = program
            course.periodo = "Demo 2026 · Trayecto III · 16 semanas"
            course.clave_matricula = data["course"]["enrollment_key"]
            course.descripcion = self.course_description(data["course"])
            course.publicado = True
            course.save()
            # Solo se reinicia el contenido del curso demo; nunca se borran datos de otros cursos.
            course.secciones.all().delete()
            course.actividades.all().delete()
            Enrollment.objects.filter(curso=course).delete()
            students = []
            for first, last, email, cedula, nucleus_name in data["students"]:
                student = self.get_demo_user(group, email, cedula, first, last, nuclei[nucleus_name], "PFG", "student", password)
                Enrollment.objects.get_or_create(curso=course, estudiante=student, defaults={"activo": True})
                students.append(student)
            now = timezone.now()
            sections = {}
            for unit in data["units"]:
                section = Section.objects.create(curso=course, titulo=f"Unidad {unit['number']}. {unit['title']}", orden=unit["number"], contenido=unit["content"])
                sections[unit["number"]] = section
                for resource in unit["resources"]:
                    citation = f"{resource['organism']} ({resource['year']})."
                    if resource.get("url"):
                        Resource.objects.create(seccion=section, titulo=resource["title"], tipo="link", url=resource["url"], contenido=citation)
                    else:
                        Resource.objects.create(seccion=section, titulo=resource["title"], tipo="page", contenido=citation + " URL oficial pendiente de verificación; consultar VERIFICAR.md.")
                av = unit["audiovisual"]
                Resource.objects.create(seccion=section, titulo=av["title"], tipo="page", contenido=f"{av['organism']} · fecha por confirmar. Recurso audiovisual pendiente de selección y verificación; no se publica enlace inventado.")
                Resource.objects.create(seccion=section, titulo="Actividad de aprendizaje", tipo="page", contenido=unit["activity"])
            activities = {}
            def add_activity(key, title, kind, week, instructions, points=20):
                obj = Activity.objects.create(curso=course, titulo=title, tipo=kind, instrucciones=instructions, fecha_limite=now + timedelta(weeks=week), puntos=Decimal(str(points)), publicado=True)
                activities[key] = obj
                return obj
            for i, unit in enumerate(data["units"], start=1):
                quiz_questions = data["quizzes"][i - 1]["questions"]
                question_text = []
                for number, question in enumerate(quiz_questions, start=1):
                    question_text.append(f"{number}. {question['question']}")
                    if question.get("options"):
                        question_text.extend(f"   - {option}" for option in question["options"])
                    elif question["type"] == "tf":
                        question_text.append("   - Verdadero / Falso")
                    elif question["type"] == "fill":
                        question_text.append("   - Complete la oración.")
                quiz_instructions = (
                    "Cuestionario de demostración · 10 preguntas · tiempo previsto: 30 minutos · "
                    "máximo: 2 intentos · calificación: 20 puntos.\n\n"
                    + "\n".join(question_text)
                    + "\n\nNota técnica: el LMS actual no procesa respuestas, intentos, temporizador ni calificación automática. "
                    "Este listado permite revisar los reactivos; las claves y retroalimentaciones preliminares están en el JSON del repositorio "
                    "y requieren validación docente antes de su uso."
                )
                add_activity(f"quiz{i}", f"Cuestionario {i}: {unit['title']}", "Cuestionario", i * 2, quiz_instructions, 20)
            for forum in data["forums"]:
                add_activity("forum" + str(len([k for k in activities if k.startswith("forum")]) + 1), forum["title"], "Foro", forum["week"], forum["instructions"] + "\nRÚBRICA (4 criterios, 1-4 puntos): " + "; ".join(forum["rubric"]) + "\nConversión: puntos/16 × 20.", 20)
            for assignment in data["assignments"]:
                add_activity("task" + str(len([k for k in activities if k.startswith("task")]) + 1), assignment["title"], "Tarea", assignment["week"], assignment["instructions"] + "\nRÚBRICA (4 criterios, 1-4 puntos): " + "; ".join(assignment["rubric"]) + "\nConversión: puntos/16 × 20.", 20)
            meeting = os.environ.get(data["workshop"]["meeting_url_env"], "").strip()
            workshop_text = data["workshop"]["instructions"] + (f"\nSala configurada: {meeting}" if meeting.startswith(("https://meet.google.com/", "https://meet.jit.si/")) else "\nSala sin configurar. Define DEMO_DDHH_MEETING_URL con una URL Jitsi/Google Meet válida.")
            add_activity("workshop", data["workshop"]["title"], "Taller", data["workshop"]["week"], workshop_text, 20)
            exam_items = []
            for number, question in enumerate(data["exam_bank"][:17], start=1):
                exam_items.append(f"{number}. {question['question']}")
                if question.get("options"):
                    exam_items.extend(f"   - {option}" for option in question["options"])
            for number, question in enumerate(data["exam_bank"][-3:], start=18):
                exam_items.append(f"{number}. DESARROLLO: {question['question']}")
                exam_items.append(f"   Rúbrica: {question['rubric']}")
            exam_text = (
                "Examen demostrativo · 20 preguntas (17 objetivas y 3 de desarrollo) · 60 minutos. "
                "Las preguntas de desarrollo requieren corrección manual. El motor actual no implementa "
                "aleatorización, temporizador, persistencia de respuestas ni corrección automática.\n\n"
                + "\n".join(exam_items)
            )
            add_activity("midterm", "Examen parcial · Semana 8", "Cuestionario", 8, exam_text, 20)
            add_activity("final", "Examen final · Semana 16", "Cuestionario", 16, exam_text, 20)
            glossary_text = "\n".join(f"{term}: {definition}" for term, definition in data["glossary"])
            add_activity("glossary", "Glosario colaborativo de derechos humanos", "Wiki", 10, "Glosario inicial de 30 términos. La colaboración simultánea/versionado no está implementada en el modelo actual.\n" + glossary_text, 20)
            survey_text = "\n".join(f"{i+1}. {question}" for i, question in enumerate(data["survey"]["questions"]))
            add_activity("survey", data["survey"]["title"], "Encuesta", 16, "Instrumento de satisfacción de cierre. Las respuestas no se recopilan automáticamente en el modelo actual.\n" + survey_text, 20)
            gradebook = json.dumps(data["course"]["gradebook"], ensure_ascii=False, indent=2)
            Resource.objects.create(seccion=sections[5], titulo="Libro de calificaciones y escala", tipo="page", contenido=gradebook + "\nEscala 1-20; aprobatoria 10. La ponderación es descriptiva: el modelo actual no calcula un libro ponderado.")
            for student_index, student in enumerate(students):
                # Simulación transparente de entregas y participación, no evidencia académica real.
                if student_index % 4 != 3:
                    for task_no in (1, 2):
                        activity = activities[f"task{task_no}"]
                        sub = Submission.objects.create(actividad=activity, estudiante=student, texto=f"ENTREGA FICTICIA DE DEMOSTRACIÓN\nEstudiante: {student.get_full_name()}\nActividad: {activity.titulo}\nAnálisis académico simulado para visualizar el flujo de entrega. No constituye trabajo real ni contiene archivos PDF/DOCX.", entregada=now - timedelta(days=max(1, 35 - student_index * 2)))
                        if student_index not in (2, 6, 10):
                            score = Decimal(str([16, 13, 8, 18, 11, 6, 15, 19, 9][student_index % 9]))
                            Grade.objects.create(entrega=sub, docente=teacher, puntos=score, retroalimentacion="Calificación ficticia para demostración; sustituir por evaluación docente real.")
                for forum_no in (1, 2):
                    if (student_index + forum_no) % 3 != 0:
                        forum_activity = activities[f"forum{forum_no}"]
                        Submission.objects.create(actividad=forum_activity, estudiante=student, texto=f"INTERVENCIÓN FICTICIA DE FORO\n{student.get_full_name()} presenta una postura inicial y solicita contraste de fuentes. Registro generado exclusivamente para demostración.", entregada=now - timedelta(days=12 - student_index))
                # Dos registros de entrega representan intentos simulados; el modelo no almacena número/estado de intento.
                for quiz_no in (1, 2, 3, 4, 5):
                    if (student_index + quiz_no) % 4 != 0:
                        quiz = activities[f"quiz{quiz_no}"]
                        for attempt in range(1, 3 if student_index % 3 == 0 else 2):
                            sub = Submission.objects.create(actividad=quiz, estudiante=student, texto=f"INTENTO FICTICIO {attempt} · cuestionario de demostración. No es un intento procesado por motor automático.", entregada=now - timedelta(days=quiz_no * 7 - attempt))
                            if attempt == 1 or student_index % 3 != 0:
                                Grade.objects.create(entrega=sub, docente=teacher, puntos=Decimal(str([17, 12, 7, 15, 9, 18, 11, 5, 14][student_index % 9])), retroalimentacion="Puntuación sintética de demostración; no representa respuestas verificadas.")
                if student_index < 5:
                    Message.objects.create(remitente=teacher, destinatario=student, asunto="Bienvenida a Derechos Humanos", cuerpo="Mensaje ficticio de demostración. Revise la guía de la Unidad 1 y el calendario del curso.")
            Announcement.objects.update_or_create(titulo="Bienvenida · Derechos Humanos · Demo", nucleo=nuclei["Caracas"], defaults={"cuerpo":"Curso demostrativo con datos personales ficticios. Las entregas y calificaciones son sintéticas y no constituyen registros académicos reales.","autor":teacher})
        self.stdout.write(self.style.SUCCESS(
            f"Demo DDHH cargada. Curso={COURSE_CODE}; docente={TEACHER_EMAIL}; estudiantes={len(students)}; unidades={len(data['units'])}; actividades={len(activities)}."
        ))
        self.stdout.write("Credenciales: usa la clave definida en DEMO_DDHH_PASSWORD. No se imprimen contraseñas.")

    def get_demo_user(self, group, email, cedula, first, last, nucleus, type_code, role, password):
        user = User.objects.filter(username=email).first()
        if user and not user.groups.filter(pk=group.pk).exists():
            raise CommandError(f"El usuario {email} ya existe y no está marcado como cuenta de demo. No se modificó.")
        if user is None:
            user = User(username=email, email=email)
        user.first_name = first
        user.last_name = last
        user.is_active = True
        user.set_password(password)
        user.save()
        profile, created = Profile.objects.get_or_create(user=user, defaults={
            "cedula": cedula, "genero": "N", "telefono": "0000000000",
            "tipo_estudiante": type_code, "programa_detalle": "Derecho (PFG) · Demo",
            "nucleo": nucleus, "rol": role, "estado": "activo", "verificado": timezone.now(),
        })
        if not created and profile.cedula != cedula:
            raise CommandError(f"El perfil asociado a {email} no coincide con la cédula ficticia reservada; se aborta para evitar alterar datos.")
        profile.nucleo = nucleus
        profile.tipo_estudiante = type_code
        profile.programa_detalle = "Derecho (PFG) · Demo"
        profile.rol = role
        profile.estado = "activo"
        profile.verificado = profile.verificado or timezone.now()
        profile.save()
        user.groups.add(group)
        return user

    def course_description(self, course):
        return (
            course["description"] + "\n\nCOMPETENCIAS:\n- " + "\n- ".join(course["competencies"]) +
            "\n\nOBJETIVOS:\n- " + "\n- ".join(course["objectives"]) +
            f"\n\nTrayecto/Semestre: {course['trayectory']} · UC: {course['credits']} · Duración: {course['weeks']} semanas · Modalidad: {course['modality']}." +
            "\nDocente ficticia: Carmen Elena Rondón Palacios, abogada, especialista en Derechos Humanos y Seguridad Ciudadana."
        )

    def delete_demo(self):
        with transaction.atomic():
            group = Group.objects.filter(name=DEMO_GROUP).first()
            course = Course.objects.filter(codigo=COURSE_CODE).first()
            if group is None:
                if course:
                    raise CommandError("Existe el curso demo pero no su grupo de fixtures; se cancela la eliminación por seguridad.")
                self.stdout.write(self.style.SUCCESS("No hay fixtures DDHH que eliminar."))
                return
            users = User.objects.filter(groups=group)
            if course and not course.docente.groups.filter(pk=group.pk).exists():
                raise CommandError("El curso con el código demo no está vinculado a un docente marcado como fixture; se cancela la eliminación por seguridad.")
            other_courses = Course.objects.filter(docente__in=users)
            other_enrollments = Enrollment.objects.filter(estudiante__in=users)
            other_submissions = Submission.objects.filter(estudiante__in=users)
            other_grades = Grade.objects.filter(docente__in=users)
            if course:
                other_courses = other_courses.exclude(pk=course.pk)
                other_enrollments = other_enrollments.exclude(curso=course)
                other_submissions = other_submissions.exclude(actividad__curso=course)
                other_grades = other_grades.exclude(entrega__actividad__curso=course)
            if other_courses.exists():
                raise CommandError("Una cuenta demo está asignada a otro curso. Retira esa relación antes de borrar las cuentas.")
            if other_enrollments.exists():
                raise CommandError("Una cuenta demo está matriculada en otro curso. No se borrarán matrículas ajenas.")
            if other_submissions.exists():
                raise CommandError("Una cuenta demo tiene entregas fuera del curso demo. No se borrarán esos registros.")
            if other_grades.exists():
                raise CommandError("La docente demo tiene calificaciones fuera del curso demo. No se borrarán esos registros.")
            if Announcement.objects.filter(autor__in=users).exclude(titulo="Bienvenida · Derechos Humanos · Demo").exists():
                raise CommandError("Una cuenta demo figura como autora de anuncios ajenos a la demo. No se borrarán esos datos.")
            if Message.objects.filter(remitente__in=users).exclude(destinatario__in=users).exists() or Message.objects.filter(destinatario__in=users).exclude(remitente__in=users).exists():
                raise CommandError("Una cuenta demo tiene mensajes con cuentas ajenas al grupo. No se borrarán esas conversaciones.")
            if CalendarEvent.objects.filter(creado_por__in=users).exists():
                raise CommandError("Una cuenta demo creó eventos de calendario. Revise esos registros antes de eliminarla.")
            count = users.count()
            Announcement.objects.filter(autor__in=users, titulo="Bienvenida · Derechos Humanos · Demo").delete()
            if course:
                course.delete()
                self.stdout.write("Curso y datos académicos relacionados eliminados.")
            users.delete()
            group.delete()
            self.stdout.write(f"{count} cuentas ficticias de demo eliminadas.")
            self.stdout.write(self.style.SUCCESS("Limpieza de demo completada. Núcleos y programas de catálogo no se eliminan."))
