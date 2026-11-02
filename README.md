# Aula Virtual UNES

Base funcional del campus virtual institucional de la Universidad Nacional Experimental de la Seguridad.

## Tecnología
- Python 3.12 / Django 5.2
- PostgreSQL administrado en Neon
- Bootstrap 5, plantillas Django y JavaScript
- Despliegue Vercel con función Python y WhiteNoise

## Desarrollo local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations lms\npython manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Producción
Vercel ejecuta las migraciones versionadas y collectstatic durante el build. Las migraciones de modelos deben generarse y confirmarse en Git antes del despliegue. Las variables DATABASE_URL y SECRET_KEY se configuran como secretos del proyecto Vercel. La rama production de Neon se usa para producción y una rama aislada para previews.

Para habilitar verificación de correo y recuperación de contraseña configure EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL en Vercel.

## Funcionalidad base
- Registro institucional con cédula única, correo, teléfono, perfil, programa y núcleo.
- Verificación por correo con token firmado de 24 horas.
- Inicio de sesión con email, recuperación de contraseña y rate limiting.
- Catálogos iniciales de núcleos, PNF, PNFA, PFG y dependencias.
- Perfiles y roles iniciales, cursos, matrículas, secciones, recursos, actividades, entregas, notas, anuncios, calendario, mensajería, notificaciones y auditoría.
- Administración de datos mediante Django Admin.

## Operación
Después del primer despliegue, crear un superusuario con acceso de mantenimiento a Neon y asignar permisos institucionales desde /admin/. No se crea un usuario administrador predeterminado.

La plataforma es una base inicial desplegable. Foros completos, cuestionarios con banco de preguntas, rúbricas, importación masiva, certificados QR y exportaciones avanzadas requieren las siguientes iteraciones. Para archivos académicos persistentes debe conectarse un bucket S3 compatible; el filesystem efímero de funciones serverless no sirve para guardar entregas a largo plazo.
