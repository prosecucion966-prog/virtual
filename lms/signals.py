from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Nucleo,Programa,Dependencia
NUCLEOS=["Altos Mirandinos","Amazonas","Anzoátegui","Apure","Aragua","Barinas","Barlovento","Bello Monte","Bolivar","Carabobo","Caracas","Carupano","Carmen de Uria","Cojedes San Carlos","Cojedes Tinaquillo","Delta Amacuro","El Cafetal","Eje Metropolitano","El Junquito","El Llanito","Falcon","Guarenas Guatire","Guárico","Inteligencia Y Contrainteligencia","La Guaira","La Guajira","Lara","Mérida","Monagas","Nueva Esparta","Portuguesa","Puerto Ordaz","San Pedro","Sucre","Táchira","Trujillo","Valles Del Tuy","Yaracuy","Zulia"]
PNF=["Servicio de Policía","Ciencias de Fuego y Seguridad Contra Incendios","Investigación Penal","Servicios Penitenciarios","Protección Civil y Administración de Desastres","Criminalística","Seguridad de la Nación","Emergencia Prehospitalarias"]
PFG=["Derecho","Criminología","Ingeniería Estructural en Seguridad y Protección Contra Incendios"]
DEPS=["Rectorado","Dirección de Atención al Ciudadano","Auditoria Interna","Consultoria Juridica","Dirección General de Facultades","Facultad de Servicio Policial","Facultad de Investigación Penal y Criminalistica","Facultad de Servicios Penitenciarios","Facultad de Ciencias del Fuego","Facultad de Protección Civil","Secretaría General","Vicerrectorado Administrativo","Vicerrectorado de Creación Intelectual y Vinculación Social","Vicerrectorado de Desarrollo Académico","Instituto de Altos Estudios","Decanato del Núcleo","Coordinación de Control de Estudio","Coordinación Administrativa","Coordinación de Desarrollo Académico","Coordinación de Creación Intelectual y Vinculación Social"]
@receiver(post_migrate)
def seed_catalogs(sender,**kwargs):
 if sender.name!="lms": return
 for name in NUCLEOS: Nucleo.objects.get_or_create(nombre=name)
 for name in PNF: Programa.objects.get_or_create(nombre=name,defaults={"categoria":"PNF"})
 for name in PFG: Programa.objects.get_or_create(nombre=name,defaults={"categoria":"PFG"})\n Programa.objects.get_or_create(nombre="Seguridad Ciudadana",defaults={"categoria":"PNFA"})
 for nivel in ["Especialista","Maestría","Doctorado"]:
  Programa.objects.get_or_create(nombre=f"{nivel} en Seguridad Ciudadana",defaults={"categoria":"PNFA","nivel":nivel})
 for name in DEPS: Dependencia.objects.get_or_create(nombre=name)
