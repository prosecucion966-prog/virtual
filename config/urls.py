from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from lms import views
urlpatterns=[
 path("admin/",admin.site.urls), path("",views.home,name="home"),
 path("registro/",views.register,name="register"),path("verificar/<str:token>/",views.verify_email,name="verify_email"),
 path("ingresar/",views.login_view,name="login"),path("salir/",views.logout_view,name="logout"),
 path("panel/",views.dashboard,name="dashboard"),path("cursos/",views.courses,name="courses"),
 path("gestion/aulas/",views.manage_courses,name="manage_courses"),
 path("gestion/aulas/nueva/",views.course_create,name="course_create"),
 path("gestion/aulas/<int:pk>/editar/",views.course_edit,name="course_edit"),
 path("gestion/aulas/<int:pk>/",views.manage_course_detail,name="manage_course_detail"),
 path("gestion/aulas/<int:pk>/unidades/nueva/",views.section_create,name="section_create"),
 path("gestion/aulas/<int:pk>/unidades/<int:section_id>/recursos/nuevo/",views.resource_create,name="resource_create"),
 path("gestion/aulas/<int:pk>/actividades/nueva/",views.activity_create,name="activity_create"),
 path("administracion/",views.admin_dashboard,name="admin_dashboard"),
 path("administracion/usuarios/",views.admin_users,name="admin_users"),
 path("administracion/docentes/nuevo/",views.admin_docente_create,name="admin_docente_create"),
 path("administracion/unidades-curriculares/",views.admin_unidades_curriculares,name="admin_unidades_curriculares"),
 path("administracion/unidades-curriculares/nueva/",views.admin_unidad_curricular_create,name="admin_unidad_curricular_create"),
 path("administracion/mallas/importar/",views.admin_importar_mallas,name="admin_importar_mallas"),
 path("administracion/nucleos/nuevo/",views.admin_nucleo_create,name="admin_nucleo_create"),
 path("administracion/programas/nuevo/",views.admin_programa_create,name="admin_programa_create"),
 path("administracion/anuncios/nuevo/",views.admin_announcement_create,name="admin_announcement_create"),
 path("administracion/anuncios/",views.admin_announcements,name="admin_announcements"),
 path("administracion/auditoria/",views.admin_audit,name="admin_audit"),
 path("recuperar/",auth_views.PasswordResetView.as_view(template_name="registration/reset.html"),name="password_reset"),
 path("recuperar/enviado/",auth_views.PasswordResetDoneView.as_view(template_name="registration/reset_done.html"),name="password_reset_done"),
 path("restablecer/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="registration/reset_confirm.html"),name="password_reset_confirm"),
 path("restablecer/completado/",auth_views.PasswordResetCompleteView.as_view(template_name="registration/reset_complete.html"),name="password_reset_complete"),
]
