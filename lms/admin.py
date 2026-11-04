from django.contrib import admin
from .models import *
admin.site.site_header="Administración · Aula Virtual UNES"
admin.site.site_title="Aula Virtual UNES"
admin.site.register([Nucleo,Programa,Dependencia,Profile,Course,Enrollment,Section,Resource,Activity,Submission,Grade,Announcement,CalendarEvent,Message,Notification,AuditLog,UnidadCurricular,TeachingAssignment])
