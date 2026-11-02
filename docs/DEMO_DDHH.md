# Carga de demostración — Derechos Humanos UNES

## Requisitos

- Aplicación Django 5.2 y migraciones existentes aplicadas.
- Acceso a la base de datos configurada en `DATABASE_URL`.
- Catálogos de núcleos y programas existentes son reutilizados cuando coinciden.
- Definir una clave temporal para las cuentas ficticias. No se incluye una contraseña por defecto ni se imprime en consola.

## Configuración

Linux/macOS:

```bash
export DEMO_DDHH_PASSWORD='Defina-Una-Clave-Temporal-Segura'
export DEMO_DDHH_MEETING_URL='https://meet.jit.si/NombreDeSalaPrivada'
python manage.py cargar_demo_ddhh
```

PowerShell:

```powershell
$env:DEMO_DDHH_PASSWORD = 'Defina-Una-Clave-Temporal-Segura'
$env:DEMO_DDHH_MEETING_URL = 'https://meet.jit.si/NombreDeSalaPrivada'
python manage.py cargar_demo_ddhh
```

La variable `DEMO_DDHH_PASSWORD` se aplica a las 13 cuentas ficticias (docente y doce estudiantes). Usa una clave temporal, compártela únicamente con el equipo de demostración y cámbiala/elimina las cuentas al finalizar. No reutilices contraseñas institucionales. La sala es opcional; solo se acepta URL HTTPS de Google Meet o Jitsi.

## Idempotencia y limpieza

Ejecutar nuevamente `python manage.py cargar_demo_ddhh` actualiza el curso identificado por `DDHH-DEMO-2026`, reconstruye su contenido, reinicia las matrículas y reemplaza las entregas/notas simuladas. Las cuentas quedan marcadas por el grupo `DEMO_DDHH_FIXTURES`. Si un correo ya existe y no pertenece a ese grupo, el comando aborta en lugar de apropiarse de una cuenta preexistente.

Para borrar:

```bash
python manage.py cargar_demo_ddhh --borrar
```

La opción elimina el curso demo y sus relaciones en cascada y las cuentas pertenecientes al grupo de fixtures. No elimina los núcleos ni los programas de catálogo. Ejecuta la limpieza solo en el entorno de demostración: no uses esta opción en una base con registros reales mezclados.

## Contenido creado

- Docente ficticia Carmen Elena Rondón Palacios, `docente.ddhh@demo.unes.local`, perfil activo/verificado, rol docente y núcleo Caracas.
- Doce estudiantes ficticios PFG Derecho; nueve en Caracas y tres distribuidos entre Maracay, Valencia y Barquisimeto.
- Curso publicado con clave de matrícula `DDHH-DEMO-2026`, trayecto III, 3 UC y 16 semanas.
- Cinco unidades, recursos bibliográficos, actividades de aprendizaje y materiales audiovisuales marcados para selección/verificación.
- Cinco bancos preliminares de diez preguntas (50 preguntas en total), 50 reactivos objetivos adicionales disponibles para revisión del banco de examen y tres preguntas de desarrollo.
- Dos foros con rúbricas, dos tareas con rúbricas, taller sincrónico, parcial, final, glosario de 30 términos y encuesta.
- Entregas, participaciones, mensajes y notas sintéticas para mostrar el flujo de actividad. Todo se identifica como dato ficticio de demostración.

## Límites que deben conocerse antes de la presentación

El esquema actual solo cuenta con `Activity`, `Submission`, `Grade`, `Resource`, `Section` y `Message`. No implementa un motor de cuestionarios, opciones de respuesta persistidas, intentos numerados, temporizador, aleatorización, corrección automática, hilos de foro, rúbricas evaluables, wiki colaborativa versionada ni captura de respuestas de encuesta. Por ello, el comando registra estos componentes como actividades e instrucciones y simula entregas/notas con los modelos existentes. No habilita por sí mismo esas capacidades interactivas.

El libro ponderado se conserva en el JSON de datos y se incorpora como recurso descriptivo del aula: Cuestionarios 20%, Foros 10%, Tareas 20%, Taller 10%, Parcial 15%, Final 25%. La nota aprobatoria indicada es 10/20. El sistema actual no calcula automáticamente esta ponderación. La regla propuesta de redondeo es redondear solo la nota final a un decimal; debe prevalecer la normativa académica institucional.

## Archivos

- `lms/management/commands/cargar_demo_ddhh.py`: comando de gestión.
- `lms/data/demo_ddhh.json`: contenidos, fuentes, preguntas, rúbricas, glosario y cohorte ficticia.
- `VERIFICAR.md`: lista de comprobación de cada fuente y de cada pregunta para validación docente-jurídica.

## Capturas sugeridas para la demostración

1. Panel docente mostrando el curso Derechos Humanos y los indicadores de matrículas.
2. Detalle del aula con las cinco unidades y lecturas enlazadas.
3. Unidad 1 con lectura DUDH, actividad y recurso de referencia.
4. Listado de actividades con cinco cuestionarios, dos foros, dos tareas, taller, parcial y final.
5. Entregas ficticias con mezcla de calificadas y pendientes.
6. Libro de notas o listado administrativo de entregas, aclarando que los datos son sintéticos y no hay ponderación automática.
7. Listado de estudiantes y distribución por núcleo.
8. Taller sincrónico con la URL configurada, ocultando cualquier información de acceso sensible.

No se deben capturar contraseñas, tokens, claves privadas ni datos personales reales.
