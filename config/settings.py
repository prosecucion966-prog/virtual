import os
from pathlib import Path
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-local-key-change-me")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true","1","yes")
ALLOWED_HOSTS = [x.strip() for x in os.environ.get("ALLOWED_HOSTS",".vercel.app,localhost,127.0.0.1").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get("CSRF_TRUSTED_ORIGINS","https://*.vercel.app").split(",") if x.strip()]
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","lms"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.debug","django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="config.wsgi.application"
DATABASES={"default":dj_database_url.config(default=os.getenv("DATABASE_URL",f"sqlite:///{BASE_DIR/'db.sqlite3'}"),conn_max_age=0,ssl_require=not DEBUG)}
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator","OPTIONS":{"min_length":10}},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
PASSWORD_HASHERS=["django.contrib.auth.hashers.Argon2PasswordHasher","django.contrib.auth.hashers.PBKDF2PasswordHasher"]
LANGUAGE_CODE="es-ve"; TIME_ZONE="America/Caracas"; USE_I18N=True; USE_TZ=True
STATIC_URL="/static/"; STATIC_ROOT=BASE_DIR/"staticfiles"
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="login"; LOGIN_REDIRECT_URL="dashboard"; LOGOUT_REDIRECT_URL="home"
EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST=os.getenv("EMAIL_HOST",""); EMAIL_PORT=int(os.getenv("EMAIL_PORT","587")); EMAIL_USE_TLS=os.getenv("EMAIL_USE_TLS","True").lower()=="true"
EMAIL_HOST_USER=os.getenv("EMAIL_HOST_USER",""); EMAIL_HOST_PASSWORD=os.getenv("EMAIL_HOST_PASSWORD","")
DEFAULT_FROM_EMAIL=os.getenv("DEFAULT_FROM_EMAIL","Aula Virtual UNES <no-reply@example.com>")
PASSWORD_RESET_TIMEOUT=3600
SESSION_COOKIE_SECURE=not DEBUG; CSRF_COOKIE_SECURE=not DEBUG; SESSION_COOKIE_HTTPONLY=True
SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS="DENY"; SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
