from django.apps import AppConfig
class LmsConfig(AppConfig):
 default_auto_field="django.db.models.BigAutoField"
 name="lms"
 verbose_name="Aula Virtual UNES"
 def ready(self):
  from . import signals
