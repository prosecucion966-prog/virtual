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
