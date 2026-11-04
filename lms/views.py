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
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .models import Profile,Nucleo,Programa,Dependencia,Course,Enrollment,Announcement
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
            forms.models.Q(user__last_name__icontains=query) |
            forms.models.Q(user__email__icontains=query) |
            forms.models.Q(cedula__icontains=query)
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
            messages.success(request, f"Cuenta activada: {profile.user.email}")
        elif action == "suspend":
            if profile.user_id == request.user.id:
                messages.error(request, "No puedes suspender tu propia cuenta desde este panel.")
            else:
                profile.estado = "suspendido"
                profile.user.is_active = False
                profile.user.save(update_fields=["is_active"])
                profile.save(update_fields=["estado"])
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
        messages.success(request, f"Núcleo creado: {obj.nombre}")
        return redirect("admin_dashboard")
    return render(request, "lms/form.html", {"form": form, "heading": "Crear núcleo", "back_url": reverse("admin_dashboard")})

@login_required
def admin_programa_create(request):
    _require_superadmin(request)
    form = AdminProgramaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
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
        messages.success(request, "Anuncio publicado correctamente.")
        return redirect("admin_dashboard")
    return render(request, "lms/form.html", {"form": form, "heading": "Publicar anuncio institucional", "back_url": reverse("admin_dashboard")})
