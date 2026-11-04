import re
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .models import Profile,Nucleo,Programa,Dependencia,Course,Enrollment,Announcement,AuditLog,UnidadCurricular,TeachingAssignment
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
class RegisterForm(forms.Form):
 cedula=forms.CharField(label="Cédula de identidad",widget=forms.TextInput(attrs={"class":"form-control","placeholder":"V-12345678"}))
 apellidos=forms.CharField(label="Apellidos",widget=forms.TextInput(attrs={"class":"form-control"}))
 nombres=forms.CharField(label="Nombres",widget=forms.TextInput(attrs={"class":"form-control"}))
 correo=forms.EmailField(label="Correo electrónico",widget=forms.EmailInput(attrs={"class":"form-control"}))
 telefono=forms.CharField(label="Teléfono",widget=forms.TextInput(attrs={"class":"form-control","placeholder":"+584121234567"}))
 genero=forms.ChoiceField(label="Género",choices=[("F","Femenino"),("M","Masculino"),("O","Otro"),("N","Prefiero no indicar")],widget=forms.Select(attrs={"class":"form-select"}))
 tipo=forms.ChoiceField(label="Perfil",choices=Profile.TYPES,widget=forms.Select(attrs={"class":"form-select","id":"tipo"}))
 programa=forms.CharField(label="Carrera, área o dependencia",widget=forms.Select(attrs={"class":"form-select","id":"programa"}))
 nivel=forms.ChoiceField(label="Nivel PNFA",required=False,choices=[("","Seleccione"),("Especialista","Especialista"),("Maestría","Maestría"),("Doctorado","Doctorado")],widget=forms.Select(attrs={"class":"form-select","id":"nivel"}))
 nucleo=forms.ModelChoiceField(label="Núcleo",queryset=Nucleo.objects.filter(activo=True),empty_label="Seleccione núcleo",widget=forms.Select(attrs={"class":"form-select"}))
 password=forms.CharField(label="Contraseña",widget=forms.PasswordInput(attrs={"class":"form-control"}))
 confirm=forms.CharField(label="Confirmar contraseña",widget=forms.PasswordInput(attrs={"class":"form-control"}))
 website=forms.CharField(required=False,widget=forms.TextInput(attrs={"class":"honeypot","tabindex":"-1","autocomplete":"off"}))
 def clean_correo(self):
  v=self.cleaned_data["correo"].strip().lower()
  if User.objects.filter(email__iexact=v).exists(): raise forms.ValidationError("Este correo ya está registrado.")
  return v
 def clean_cedula(self):
  v=self.cleaned_data["cedula"].strip().upper().replace(" ","")
  if not re.fullmatch(r"[VE]-?\d{5,10}",v): raise forms.ValidationError("Use V/E seguido de 5 a 10 dígitos.")
  v=v[0]+"-"+v[1:].lstrip("-")
  if Profile.objects.filter(cedula=v).exists(): raise forms.ValidationError("Cédula ya registrada.")
  return v
 def clean(self):
  d=super().clean()
  if d.get("password")!=d.get("confirm"): self.add_error("confirm","Las contraseñas no coinciden.")
  if d.get("password"):
   try: validate_password(d["password"])
   except forms.ValidationError as e: self.add_error("password",e)
  t,p,n=d.get("tipo"),d.get("programa"),d.get("nivel")
  if t=="PNFA" and n: d["programa"]=f"{n} en Seguridad Ciudadana"
  if t=="PNF" and not Programa.objects.filter(categoria="PNF",nombre=p).exists(): self.add_error("programa","Carrera PNF no válida.")
  if t=="PFG" and not Programa.objects.filter(categoria="PFG",nombre=p).exists(): self.add_error("programa","Programa PFG no válido.")
  if t=="PNFA" and not n: self.add_error("nivel","Seleccione nivel.")
  if t=="ADMIN" and not Dependencia.objects.filter(nombre=p).exists(): self.add_error("programa","Seleccione una dependencia.")
  if t=="DOCENTE" and not Programa.objects.filter(nombre=p).exists(): self.add_error("programa","Seleccione un área académica válida.")
  if d.get("website"): self.add_error("website","Solicitud no válida.")
  phone=re.sub(r"[\s()-]","",d.get("telefono",""))
  if phone and not re.fullmatch(r"(?:\+?58)?0?(?:2\d{2}|4\d{2})\d{7}",phone): self.add_error("telefono","Introduzca un teléfono venezolano válido.")
  return d
@ratelimit(key="ip",rate="5/h",method="POST",block=True)
def register(request):
 form=RegisterForm(request.POST or None)
 if request.method=="POST" and form.is_valid():
  d=form.cleaned_data
  u=User(username=d["correo"],email=d["correo"],first_name=d["nombres"],last_name=d["apellidos"],is_active=False)
  u.set_password(d["password"]); u.save()
  role={"PNF":"student","PNFA":"student","PFG":"student","DOCENTE":"teacher","ADMIN":"staff"}[d["tipo"]]
  Profile.objects.create(user=u,cedula=d["cedula"],genero=d["genero"],telefono=d["telefono"],tipo_estudiante=d["tipo"],programa_detalle=d["programa"],nivel_pnfa=d.get("nivel",""),nucleo=d["nucleo"],rol=role,dependencia=Dependencia.objects.filter(nombre=d["programa"]).first() if d["tipo"]=="ADMIN" else None)
  token=signing.TimestampSigner(salt="unes-email").sign(str(u.pk))
  url=request.build_absolute_uri(reverse("verify_email",args=[token]))
  try:
   send_mail("Verifica tu correo · Aula Virtual UNES",f"Activa tu cuenta en las próximas 24 horas: {url}",settings.DEFAULT_FROM_EMAIL,[u.email])
   sent=True
  except Exception: sent=False
  return render(request,"registration/registered.html",{"email":u.email,"sent":sent})
 return render(request,"registration/register.html",{"form":form})
def verify_email(request,token):
 try:
  uid=signing.TimestampSigner(salt="unes-email").unsign(token,max_age=86400)
  u=User.objects.get(pk=int(uid),is_active=False); u.is_active=True; u.save(update_fields=["is_active"])
  p=u.profile; p.estado="activo"; p.verificado=timezone.now(); p.save()
  messages.success(request,"Correo verificado. Ya puedes ingresar.")
  return redirect("login")
 except Exception: return render(request,"registration/verify_error.html",status=400)
@ratelimit(key="ip",rate="10/m",method="POST",block=True)
def login_view(request):
 error=None
 if request.method=="POST":
  identifier=request.POST.get("email","").strip(); password=request.POST.get("password","")
  account=User.objects.filter(email__iexact=identifier).first() if "@" in identifier else User.objects.filter(username__iexact=identifier).first()
  user=authenticate(request,username=account.username if account else identifier,password=password)
  if user and user.is_active and hasattr(user,"profile") and user.profile.estado=="activo":
   login(request,user); return redirect("dashboard")
  error="Credenciales incorrectas o cuenta pendiente de verificación."
 return render(request,"registration/login.html",{"error":error})
@login_required
def logout_view(request):
 if request.method=="POST": logout(request)
 return redirect("home")
def home(request): return render(request,"home.html")
@login_required
def dashboard(request):
 p=getattr(request.user,"profile",None)
 if not p: raise PermissionDenied
 if p.rol in ("superadmin","nucleus_admin"):
  users=Profile.objects.filter(nucleo=p.nucleo) if p.rol=="nucleus_admin" else Profile.objects.all()
  cs=Course.objects.filter(nucleo=p.nucleo) if p.rol=="nucleus_admin" else Course.objects.all()
  stats={"Usuarios":users.count(),"Estudiantes":users.filter(rol="student").count(),"Cursos":cs.count()}
 elif p.rol=="teacher":
  cs=Course.objects.filter(docente=request.user); stats={"Cursos":cs.count(),"Matrículas":Enrollment.objects.filter(curso__in=cs).count()}
 else:
  cs=Course.objects.filter(matriculas__estudiante=request.user,matriculas__activo=True); stats={"Mis cursos":cs.count()}
 ann=Announcement.objects.filter(nucleo__isnull=True)|Announcement.objects.filter(nucleo=p.nucleo)
 return render(request,"dashboard.html",{"profile":p,"courses":cs.distinct(),"stats":stats,"announcements":ann.order_by("-creado")[:5]})
@login_required
def courses(request):
 p=getattr(request.user,"profile",None); qs=Course.objects.filter(publicado=True)
 if p and p.rol=="student": qs=qs.filter(programa__nombre=p.programa_detalle,nucleo=p.nucleo)
 if p and p.rol=="nucleus_admin": qs=qs.filter(nucleo=p.nucleo)
 return render(request,"courses.html",{"courses":qs.select_related("nucleo","programa","docente")})


# --- Gestión de aulas y contenidos académicos ---
from .models import Section, Resource, Activity
from django.urls import reverse
from django.core.exceptions import PermissionDenied

def _academic_profile(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        raise PermissionDenied
    return profile

def _can_manage_all(profile, user):
    return user.is_superuser or profile.rol in ("superadmin", "nucleus_admin")

def _get_managed_course(request, pk):
    profile = _academic_profile(request)
    course = get_object_or_404(Course, pk=pk)
    if profile.rol == "nucleus_admin" and course.nucleo_id != profile.nucleo_id:
        raise PermissionDenied
    if not _can_manage_all(profile, request.user) and not (
        profile.rol == "teacher" and course.docente_id == request.user.id
    ):
        raise PermissionDenied
    return course

class ManagedCourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("titulo", "codigo", "descripcion", "programa", "nucleo", "docente", "periodo", "publicado")
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "programa": forms.Select(attrs={"class": "form-select"}),
            "nucleo": forms.Select(attrs={"class": "form-select"}),
            "docente": forms.Select(attrs={"class": "form-select"}),
            "periodo": forms.TextInput(attrs={"class": "form-control"}),
            "publicado": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
    def __init__(self, *args, **kwargs):
        profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)
        self.fields["docente"].queryset = User.objects.filter(profile__rol="teacher", is_active=True).order_by("last_name", "first_name")
        if profile and profile.rol == "nucleus_admin":
            self.fields["nucleo"].queryset = Nucleo.objects.filter(pk=profile.nucleo_id)
            self.fields["nucleo"].initial = profile.nucleo_id

class ManagedSectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ("titulo", "contenido", "orden")
        widgets = {"titulo": forms.TextInput(attrs={"class":"form-control"}), "contenido": forms.Textarea(attrs={"class":"form-control","rows":4}), "orden": forms.NumberInput(attrs={"class":"form-control"})}

class ManagedResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ("titulo", "tipo", "url", "contenido", "archivo")
        widgets = {"titulo": forms.TextInput(attrs={"class":"form-control"}), "tipo": forms.Select(attrs={"class":"form-select"}), "url": forms.URLInput(attrs={"class":"form-control","placeholder":"https://"}), "contenido": forms.Textarea(attrs={"class":"form-control","rows":4}), "archivo": forms.ClearableFileInput(attrs={"class":"form-control"})}

class ManagedActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ("titulo", "tipo", "instrucciones", "fecha_limite", "puntos", "publicado")
        widgets = {"titulo": forms.TextInput(attrs={"class":"form-control"}), "tipo": forms.Select(attrs={"class":"form-select"}), "instrucciones": forms.Textarea(attrs={"class":"form-control","rows":4}), "fecha_limite": forms.DateTimeInput(attrs={"class":"form-control","type":"datetime-local"}), "puntos": forms.NumberInput(attrs={"class":"form-control","step":"0.01"}), "publicado": forms.CheckboxInput(attrs={"class":"form-check-input"})}

@login_required
def manage_courses(request):
    profile = _academic_profile(request)
    if profile.rol not in ("superadmin", "nucleus_admin", "teacher") and not request.user.is_superuser:
        raise PermissionDenied
    courses_qs = Course.objects.select_related("nucleo", "programa", "docente")
    if profile.rol == "teacher" and not request.user.is_superuser:
        courses_qs = courses_qs.filter(docente=request.user)
    if profile.rol == "nucleus_admin":
        courses_qs = courses_qs.filter(nucleo=profile.nucleo)
    return render(request, "lms/manage_courses.html", {"courses": courses_qs})

@login_required
def course_create(request):
    profile = _academic_profile(request)
    if not _can_manage_all(profile, request.user):
        raise PermissionDenied
    form = ManagedCourseForm(request.POST or None, profile=profile)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        AuditLog.objects.create(actor=request.user, accion="Creación de aula", detalle=f"{course.codigo} · {course.titulo}"[:250])
        messages.success(request, "Aula creada correctamente.")
        return redirect("manage_course_detail", pk=course.pk)
    return render(request, "lms/form.html", {"form": form, "heading": "Crear aula virtual", "back_url": reverse("manage_courses")})

@login_required
def manage_course_detail(request, pk):
    course = _get_managed_course(request, pk)
    return render(request, "lms/manage_course_detail.html", {"course": course})

@login_required
def section_create(request, pk):
    course = _get_managed_course(request, pk)
    form = ManagedSectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        section = form.save(commit=False); section.curso = course; section.save()
        messages.success(request, "Unidad o tema agregado.")
        return redirect("manage_course_detail", pk=course.pk)
    return render(request, "lms/form.html", {"form": form, "heading": "Agregar unidad o tema", "back_url": reverse("manage_course_detail", args=[course.pk])})

@login_required
def resource_create(request, pk, section_id):
    course = _get_managed_course(request, pk)
    section = get_object_or_404(Section, pk=section_id, curso=course)
    form = ManagedResourceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        resource = form.save(commit=False); resource.seccion = section; resource.save()
        messages.success(request, "Material agregado a la unidad.")
        return redirect("manage_course_detail", pk=course.pk)
    return render(request, "lms/form.html", {"form": form, "heading": "Agregar material o recurso", "back_url": reverse("manage_course_detail", args=[course.pk])})

@login_required
def activity_create(request, pk):
    course = _get_managed_course(request, pk)
    form = ManagedActivityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False); activity.curso = course; activity.save()
        messages.success(request, "Actividad creada.")
        return redirect("manage_course_detail", pk=course.pk)
    return render(request, "lms/form.html", {"form": form, "heading": "Crear actividad o evaluación", "back_url": reverse("manage_course_detail", args=[course.pk])})


# --- Centro de control del superadministrador ---
def _require_superadmin(request):
    profile = getattr(request.user, "profile", None)
    if not request.user.is_superuser and (not profile or profile.rol != "superadmin"):
        raise PermissionDenied
    return profile

class AdminNucleoForm(forms.ModelForm):
    class Meta:
        model = Nucleo
        fields = ("nombre", "activo")
        widgets = {"nombre": forms.TextInput(attrs={"class": "form-control"}), "activo": forms.CheckboxInput(attrs={"class": "form-check-input"})}

class AdminProgramaForm(forms.ModelForm):
    class Meta:
        model = Programa
        fields = ("categoria", "nombre", "nivel", "activo")
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "nivel": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class AdminAnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("titulo", "cuerpo", "nucleo")
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "cuerpo": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "nucleo": forms.Select(attrs={"class": "form-select"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nucleo"].required = False
        self.fields["nucleo"].empty_label = "Todos los núcleos"

@login_required
def admin_dashboard(request):
    _require_superadmin(request)
    pending = Profile.objects.filter(estado="pendiente_verificacion").select_related("user", "nucleo").order_by("user__date_joined")[:8]
    context = {
        "users_total": User.objects.count(),
        "users_pending": Profile.objects.filter(estado="pendiente_verificacion").count(),
        "users_active": Profile.objects.filter(estado="activo").count(),
        "courses_total": Course.objects.count(),
        "courses_published": Course.objects.filter(publicado=True).count(),
        "nuclei_total": Nucleo.objects.count(),
        "programs_total": Programa.objects.count(),
        "enrollments_total": Enrollment.objects.filter(activo=True).count(),
        "activities_total": Activity.objects.count(),
        "pending_profiles": pending,
        "recent_courses": Course.objects.select_related("nucleo", "docente").order_by("-creado")[:6],
        "nuclei": Nucleo.objects.order_by("nombre")[:8],
        "programs": Programa.objects.order_by("categoria", "nombre")[:8],
        "can_open_django_admin": request.user.is_staff,
        "stats": [
            ("Usuarios registrados", User.objects.count()),
            ("Cuentas pendientes", Profile.objects.filter(estado="pendiente_verificacion").count()),
            ("Cuentas activas", Profile.objects.filter(estado="activo").count()),
            ("Aulas virtuales", Course.objects.count()),
            ("Aulas publicadas", Course.objects.filter(publicado=True).count()),
            ("Núcleos", Nucleo.objects.count()),
            ("Programas", Programa.objects.count()),
            ("Unidades curriculares", UnidadCurricular.objects.count()),
            ("Docentes activos", Profile.objects.filter(rol="teacher", estado="activo").count()),
            ("Matrículas activas", Enrollment.objects.filter(activo=True).count()),
        ],
    }
    return render(request, "lms/admin_dashboard.html", context)

@login_required
def admin_users(request):
    _require_superadmin(request)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("estado", "").strip()
    profiles = Profile.objects.select_related("user", "nucleo").order_by("-user__date_joined")
    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(cedula__icontains=query)
        )
    if status in ("pendiente_verificacion", "activo", "suspendido"):
        profiles = profiles.filter(estado=status)
    if request.method == "POST":
        profile = get_object_or_404(Profile.objects.select_related("user"), pk=request.POST.get("profile_id"))
        action = request.POST.get("action")
        if action == "activate":
            profile.estado = "activo"
            profile.verificado = profile.verificado or timezone.now()
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])
            profile.save(update_fields=["estado", "verificado"])
            AuditLog.objects.create(actor=request.user, accion="Activación de cuenta", detalle=profile.user.email)
            messages.success(request, f"Cuenta activada: {profile.user.email}")
        elif action == "suspend":
            if profile.user_id == request.user.id:
                messages.error(request, "No puedes suspender tu propia cuenta desde este panel.")
            else:
                profile.estado = "suspendido"
                profile.user.is_active = False
                profile.user.save(update_fields=["is_active"])
                profile.save(update_fields=["estado"])
                AuditLog.objects.create(actor=request.user, accion="Suspensión de cuenta", detalle=profile.user.email)
                messages.success(request, f"Cuenta suspendida: {profile.user.email}")
        elif action == "change_role":
            new_role = request.POST.get("rol", "")
            new_nucleus = request.POST.get("nucleo", "")
            if new_role not in dict(Profile.ROLES):
                messages.error(request, "Rol no válido.")
            elif new_role == "superadmin" and not request.user.is_superuser:
                messages.error(request, "Solo una cuenta superusuario de Django puede otorgar el rol superadministrador.")
            else:
                nucleus = get_object_or_404(Nucleo, pk=new_nucleus)
                profile.rol = new_role
                profile.nucleo = nucleus
                profile.save(update_fields=["rol", "nucleo"])
                AuditLog.objects.create(actor=request.user, accion="Cambio de rol y núcleo", detalle=f"{profile.user.email} · {new_role} · {nucleus.nombre}")
                messages.success(request, f"Rol y núcleo actualizados para {profile.user.email}.")
        else:
            messages.error(request, "Acción no reconocida.")
        return redirect(request.get_full_path() if request.GET else "admin_users")
    return render(request, "lms/admin_users.html", {
        "profiles": profiles[:250], "query": query, "status": status, "total": profiles.count(),
        "roles": Profile.ROLES, "nuclei": Nucleo.objects.filter(activo=True),
    })

@login_required
def admin_nucleo_create(request):
    _require_superadmin(request)
    form = AdminNucleoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        AuditLog.objects.create(actor=request.user, accion="Creación de núcleo", detalle=obj.nombre)
        messages.success(request, f"Núcleo creado: {obj.nombre}")
        return redirect("admin_dashboard")
    return render(request, "lms/form.html", {"form": form, "heading": "Crear núcleo", "back_url": reverse("admin_dashboard")})

@login_required
def admin_programa_create(request):
    _require_superadmin(request)
    form = AdminProgramaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        AuditLog.objects.create(actor=request.user, accion="Creación de programa", detalle=obj.nombre)
        messages.success(request, f"Programa creado: {obj.nombre}")
        return redirect("admin_dashboard")
    return render(request, "lms/form.html", {"form": form, "heading": "Crear programa académico", "back_url": reverse("admin_dashboard")})

@login_required
def admin_announcement_create(request):
    _require_superadmin(request)
    form = AdminAnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        announcement = form.save(commit=False)
        announcement.autor = request.user
        announcement.save()
        AuditLog.objects.create(actor=request.user, accion="Publicación de anuncio", detalle=announcement.titulo[:250])
        messages.success(request, "Anuncio publicado correctamente.")
        return redirect("admin_dashboard")
    return render(request, "lms/form.html", {"form": form, "heading": "Publicar anuncio institucional", "back_url": reverse("admin_dashboard")})


@login_required
def course_edit(request, pk):
    profile = _academic_profile(request)
    if not _can_manage_all(profile, request.user):
        raise PermissionDenied
    course = _get_managed_course(request, pk)
    form = ManagedCourseForm(request.POST or None, instance=course, profile=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        AuditLog.objects.create(actor=request.user, accion="Actualización de aula", detalle=f"{course.codigo} · {course.titulo}"[:250])
        messages.success(request, "Aula actualizada correctamente.")
        return redirect("manage_course_detail", pk=course.pk)
    return render(request, "lms/form.html", {
        "form": form, "heading": f"Editar aula: {course.titulo}",
        "back_url": reverse("manage_course_detail", args=[course.pk]),
    })


@login_required
def admin_audit(request):
    _require_superadmin(request)
    logs = AuditLog.objects.select_related("actor").order_by("-creado")[:200]
    return render(request, "lms/admin_audit.html", {"logs": logs})

@login_required
def admin_announcements(request):
    _require_superadmin(request)
    if request.method == "POST":
        announcement = get_object_or_404(Announcement, pk=request.POST.get("announcement_id"))
        if announcement.autor_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied
        announcement.delete()
        messages.success(request, "Anuncio eliminado.")
        return redirect("admin_announcements")
    items = Announcement.objects.select_related("autor", "nucleo").order_by("-creado")
    return render(request, "lms/admin_announcements.html", {"announcements": items})


# --- Alta administrativa de docentes y unidades curriculares ---
class UnidadCurricularChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        version = obj.get_version_malla_display()
        nivel = obj.semestre or obj.trayecto or "Trayecto no indicado"
        return f"{version} · {nivel} · {obj.nombre}"


class ProgramaUnidadAssignmentForm(forms.Form):
    programa = forms.ModelChoiceField(
        queryset=Programa.objects.filter(activo=True).order_by("categoria", "nombre"),
        label="Programa académico",
        empty_label="Selecciona primero un programa",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_programa"}),
    )
    unidades = UnidadCurricularChoiceField(
        queryset=UnidadCurricular.objects.none(),
        label="Unidades curriculares",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Después de elegir el programa aparecerán únicamente sus unidades curriculares. Puedes marcar varias.",
    )
    periodo = forms.CharField(
        max_length=80, label="Período académico",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "2026-II"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        program_id = self.data.get("programa") if self.is_bound else self.initial.get("programa")
        if program_id:
            self.fields["unidades"].queryset = UnidadCurricular.objects.filter(
                programa_id=program_id, activa=True,
            ).select_related("programa").order_by("semestre", "trayecto", "nombre")


class AdminDocenteForm(ProgramaUnidadAssignmentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            "nombres", "apellidos", "correo", "cedula", "telefono", "nucleo",
            "programa", "unidades", "periodo", "password", "confirmar_password",
        ])

    nombres = forms.CharField(max_length=150, label="Nombres", widget=forms.TextInput(attrs={"class": "form-control"}))
    apellidos = forms.CharField(max_length=150, label="Apellidos", widget=forms.TextInput(attrs={"class": "form-control"}))
    correo = forms.EmailField(label="Correo institucional", widget=forms.EmailInput(attrs={"class": "form-control"}))
    cedula = forms.CharField(max_length=12, label="Cédula", widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "V-12345678"}))
    telefono = forms.CharField(max_length=20, label="Teléfono", widget=forms.TextInput(attrs={"class": "form-control"}))
    nucleo = forms.ModelChoiceField(queryset=Nucleo.objects.filter(activo=True), label="Núcleo", widget=forms.Select(attrs={"class": "form-select"}))
    password = forms.CharField(label="Contraseña temporal", widget=forms.PasswordInput(attrs={"class": "form-control"}))
    confirmar_password = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()
        if User.objects.filter(Q(username__iexact=correo) | Q(email__iexact=correo)).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return correo

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip().upper().replace(" ", "")
        if not re.fullmatch(r"[VE]-?\\d{5,10}", cedula):
            raise forms.ValidationError("Use V/E seguido de 5 a 10 dígitos.")
        cedula = cedula[0] + "-" + cedula[1:].lstrip("-")
        if Profile.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        return cedula

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirmar_password"):
            self.add_error("confirmar_password", "Las contraseñas no coinciden.")
        if data.get("password"):
            try:
                validate_password(data["password"])
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        if not data.get("unidades"):
            self.add_error("unidades", "Selecciona al menos una unidad curricular del programa elegido.")
        return data


class AdminAsignacionesDocenteForm(ProgramaUnidadAssignmentForm):
    pass


def _ensure_assignment_aula(docente, unidad, nucleo, periodo):
    assignment, _ = TeachingAssignment.objects.get_or_create(
        docente=docente, unidad_curricular=unidad, nucleo=nucleo, periodo=periodo,
    )
    if not assignment.activa:
        assignment.activa = True
        assignment.save(update_fields=["activa"])
    if assignment.aula_id:
        return assignment, False
    aula = Course.objects.create(
        titulo=unidad.nombre, codigo=f"ASG-{assignment.pk}",
        descripcion=unidad.descripcion, programa=unidad.programa,
        unidad_curricular=unidad, nucleo=nucleo, docente=docente,
        periodo=periodo, publicado=False,
    )
    assignment.aula = aula
    assignment.save(update_fields=["aula"])
    return assignment, True


class AdminUnidadCurricularForm(forms.ModelForm):
    docente = forms.ModelChoiceField(
        queryset=User.objects.none(), required=False, label="Docente responsable (opcional)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    nucleo = forms.ModelChoiceField(
        queryset=Nucleo.objects.filter(activo=True), required=False, label="Núcleo para crear aula (opcional)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = UnidadCurricular
        fields = ("programa", "codigo", "nombre", "version_malla", "trayecto", "semestre",
                  "unidades_credito", "horas_semanales", "duracion_semanas", "modalidad", "descripcion", "activa")
        widgets = {
            "programa": forms.Select(attrs={"class": "form-select"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "version_malla": forms.Select(attrs={"class": "form-select"}),
            "trayecto": forms.TextInput(attrs={"class": "form-control"}),
            "semestre": forms.TextInput(attrs={"class": "form-control"}),
            "unidades_credito": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "horas_semanales": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "duracion_semanas": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "modalidad": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["programa"].queryset = Programa.objects.filter(activo=True).order_by("categoria", "nombre")
        self.fields["docente"].queryset = User.objects.filter(profile__rol="teacher", profile__estado="activo", is_active=True).order_by("last_name", "first_name")

    def clean(self):
        data = super().clean()
        docente = data.get("docente")
        nucleo = data.get("nucleo")
        if docente and not nucleo:
            self.add_error("nucleo", "Selecciona el núcleo para crear el aula del docente.")
        elif docente and nucleo and docente.profile.nucleo_id != nucleo.pk:
            self.add_error("nucleo", "El núcleo seleccionado debe coincidir con el núcleo asignado al docente.")
        return data


@login_required
def admin_unidades_por_programa(request, programa_id):
    _require_superadmin(request)
    unidades = UnidadCurricular.objects.filter(
        programa_id=programa_id, activa=True,
    ).order_by("semestre", "trayecto", "nombre")
    resultados = []
    for unidad in unidades:
        version = unidad.get_version_malla_display()
        nivel = unidad.semestre or unidad.trayecto or "Trayecto no indicado"
        resultados.append({
            "id": unidad.pk,
            "label": f"{nivel} · {unidad.nombre}",
            "detalle": f"{version} · {unidad.codigo}",
        })
    return JsonResponse({"unidades": resultados})


@login_required
@transaction.atomic
def admin_docente_create(request):
    _require_superadmin(request)
    form = AdminDocenteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user = User(
            username=data["correo"], email=data["correo"],
            first_name=data["nombres"].strip(), last_name=data["apellidos"].strip(),
            is_active=True, is_staff=False, is_superuser=False,
        )
        user.set_password(data["password"])
        user.save()
        Profile.objects.create(
            user=user, cedula=data["cedula"], telefono=data["telefono"],
            tipo_estudiante="DOCENTE", nucleo=data["nucleo"], rol="teacher",
            estado="activo", verificado=timezone.now(),
        )
        aulas_creadas = 0
        for unidad in data["unidades"]:
            _, created = _ensure_assignment_aula(user, unidad, data["nucleo"], data["periodo"])
            aulas_creadas += int(created)
        AuditLog.objects.create(
            actor=request.user, accion="Creación de docente y asignación académica",
            detalle=f"{data['correo']} · {len(data['unidades'])} materias · {aulas_creadas} aulas"[:250],
        )
        messages.success(
            request,
            f"Docente creado y activado. Se asignaron {len(data['unidades'])} materias y se crearon {aulas_creadas} aulas. No se envió correo.",
        )
        return redirect("admin_users")
    return render(request, "lms/form.html", {
        "form": form, "heading": "Crear docente y asignar materias",
        "back_url": reverse("admin_dashboard"),
        "help_text": "Completa los datos del docente, selecciona su núcleo, marca una o varias materias de cualquier programa o malla y define el período. Se creará un aula por cada materia. La operación se guarda completa o no se guarda; no se envía correo.",
    })


@login_required
@transaction.atomic
def admin_docente_asignar(request, user_id):
    _require_superadmin(request)
    docente = get_object_or_404(
        User.objects.select_related("profile__nucleo"),
        pk=user_id, profile__rol="teacher",
    )
    form = AdminAsignacionesDocenteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        created = duplicates = 0
        for unidad in form.cleaned_data["unidades"]:
            _, aula_created = _ensure_assignment_aula(
                docente, unidad, docente.profile.nucleo, form.cleaned_data["periodo"],
            )
            created += int(aula_created)
            duplicates += int(not aula_created)
        AuditLog.objects.create(
            actor=request.user, accion="Asignación de materias a docente",
            detalle=f"{docente.email} · {len(form.cleaned_data['unidades'])} materias · {created} aulas nuevas"[:250],
        )
        messages.success(request, f"Asignación procesada: {created} aulas nuevas; {duplicates} asignaciones existentes se conservaron.")
        return redirect("admin_users")
    return render(request, "lms/form.html", {
        "form": form,
        "heading": f"Asignar materias a {docente.get_full_name() or docente.email}",
        "back_url": reverse("admin_users"),
        "help_text": f"Núcleo del docente: {docente.profile.nucleo.nombre}. Selecciona una o varias unidades curriculares y período. Cada asignación genera un aula independiente; el contenido de aulas existentes se conserva.",
    })


@login_required
@transaction.atomic
def admin_unidad_curricular_create(request):
    _require_superadmin(request)
    form = AdminUnidadCurricularForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        unidad = form.save()
        docente = form.cleaned_data["docente"]
        nucleo = form.cleaned_data["nucleo"]
        aula = None
        if docente and nucleo:
            _, aula_created = _ensure_assignment_aula(
                docente, unidad, nucleo, unidad.semestre or unidad.trayecto or "Por definir",
            )
            aula = Course.objects.filter(
                docente=docente, unidad_curricular=unidad, nucleo=nucleo,
                periodo=unidad.semestre or unidad.trayecto or "Por definir",
            ).first()
        AuditLog.objects.create(actor=request.user, accion="Creación de unidad curricular",
                                detalle=f"{unidad.codigo} · {unidad.nombre} · {unidad.programa.nombre}"[:250])
        if aula:
            AuditLog.objects.create(actor=request.user, accion="Creación de aula por unidad curricular",
                                    detalle=f"{aula.codigo} · {docente.email}"[:250])
            messages.success(request, f"Unidad vinculada a {unidad.programa.nombre}; aula creada y asignada a {docente.email}.")
        elif docente and not nucleo:
            messages.success(request, "Unidad curricular creada y vinculada al programa. Selecciona también el núcleo si deseas crear su aula ahora.")
        else:
            messages.success(request, f"Unidad curricular creada y vinculada a {unidad.programa.nombre}.")
        return redirect("admin_unidades_curriculares")
    return render(request, "lms/form.html", {
        "form": form, "heading": "Crear unidad curricular y vincular a programa",
        "back_url": reverse("admin_dashboard"),
        "help_text": "Selecciona obligatoriamente el programa. Si eliges docente y núcleo, se crea automáticamente el aula virtual correspondiente.",
    })


@login_required
def admin_unidades_curriculares(request):
    _require_superadmin(request)
    query = request.GET.get("q", "").strip()
    unidades = UnidadCurricular.objects.select_related("programa").prefetch_related("aulas").order_by("programa__nombre", "trayecto", "nombre")
    if query:
        unidades = unidades.filter(Q(nombre__icontains=query) | Q(codigo__icontains=query) | Q(programa__nombre__icontains=query))
    return render(request, "lms/admin_unidades_curriculares.html", {"unidades": unidades, "query": query})


@login_required
def admin_importar_mallas(request):
    _require_superadmin(request)
    summary = None
    if request.method == "POST":
        uploaded = request.FILES.get("archivo_mallas")
        if not uploaded:
            messages.error(request, "Selecciona el archivo Excel de las mallas.")
        elif not uploaded.name.lower().endswith(".xlsx"):
            messages.error(request, "El archivo debe tener formato .xlsx.")
        elif uploaded.size > 5 * 1024 * 1024:
            messages.error(request, "El archivo supera el límite de 5 MB.")
        else:
            try:
                from openpyxl import load_workbook
                from .curriculum_import import import_workbook
                workbook = load_workbook(uploaded, read_only=True, data_only=True)
                try:
                    received = {sheet.title.strip().upper() for sheet in workbook.worksheets}
                    if not received.intersection({"POLICIAL VIEJA", "POLICIAL NUEVA", "INV PENAL VIEJA", "CRIMINALÍSTICA VIEJA", "IP Y CRIM NUEVA", "SERV PENIT", "BOMBERIL", "PCAD", "SEG NACION", "EMERGENCIA PREH"}):
                        raise ValueError("El libro no contiene hojas reconocidas de las mallas UNES.")
                    summary = import_workbook(workbook)
                finally:
                    workbook.close()
                AuditLog.objects.create(actor=request.user, accion="Importación de mallas curriculares", detalle=f"{summary['created']} creadas, {summary['updated']} actualizadas")
                messages.success(request, f"Importación finalizada: {summary['created']} unidades creadas y {summary['updated']} actualizadas.")
            except Exception as exc:
                messages.error(request, f"No se pudo procesar el libro: {exc}")
    return render(request, "lms/admin_importar_mallas.html", {"summary": summary})


@login_required
def admin_cargar_malla_criminologia(request):
    _require_superadmin(request)
    if request.method == "POST":
        from django.core.management import call_command
        from io import StringIO
        output = StringIO()
        call_command("cargar_malla_criminologia", stdout=output)
        AuditLog.objects.create(
            actor=request.user,
            accion="Carga de malla de Criminología",
            detalle=output.getvalue().strip()[:250],
        )
        messages.success(request, output.getvalue().strip())
        return redirect("admin_unidades_curriculares")
    return render(request, "lms/admin_cargar_malla_criminologia.html")


@login_required
def admin_cargar_malla_derecho(request):
    _require_superadmin(request)
    if request.method == "POST":
        from django.core.management import call_command
        from io import StringIO
        output = StringIO()
        call_command("cargar_malla_derecho", stdout=output)
        result = output.getvalue().strip()
        AuditLog.objects.create(
            actor=request.user,
            accion="Carga de malla de Derecho",
            detalle=result[:250],
        )
        messages.success(request, result)
        return redirect("admin_unidades_curriculares")
    return render(request, "lms/admin_cargar_malla_derecho.html")
