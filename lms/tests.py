from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Course, Nucleo, Profile, Programa, TeachingAssignment, UnidadCurricular


class AdminDocenteAsignacionesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="AdminPass!2026",
        )
        self.client.force_login(self.admin)
        self.nucleo = Nucleo.objects.create(nombre="Núcleo de prueba")
        self.programa = Programa.objects.create(
            categoria="PFG", nombre="Derecho de prueba", nivel="Pregrado",
        )
        self.unidad = UnidadCurricular.objects.create(
            programa=self.programa, codigo="DER-001", nombre="Derecho Constitucional",
            version_malla="VIGENTE", semestre="I", unidades_credito=3,
        )
        self.unidad_dos = UnidadCurricular.objects.create(
            programa=self.programa, codigo="DER-002", nombre="Derecho Civil I",
            version_malla="VIGENTE", semestre="I", unidades_credito=4,
        )

    def test_crear_docente_asigna_materia_y_crea_aula(self):
        response = self.client.post(reverse("admin_docente_create"), {
            "nombres": "Docente", "apellidos": "De Prueba",
            "correo": "docente@example.test", "cedula": "V-12345678",
            "telefono": "04121234567", "nucleo": self.nucleo.pk,
            "unidades": [self.unidad.pk, self.unidad_dos.pk], "periodo": "2026-II",
            "password": "XyZ!9876-Strong", "confirmar_password": "XyZ!9876-Strong",
        })
        self.assertEqual(response.status_code, 302)
        docente = User.objects.get(email="docente@example.test")
        self.assertEqual(docente.profile.rol, "teacher")
        self.assertTrue(docente.is_active)
        self.assertFalse(docente.is_staff)
        self.assertEqual(TeachingAssignment.objects.filter(docente=docente).count(), 2)
        self.assertEqual(Course.objects.filter(docente=docente).count(), 2)
        aula = Course.objects.get(docente=docente, unidad_curricular=self.unidad)
        self.assertEqual(aula.nucleo_id, self.nucleo.pk)
        self.assertEqual(aula.periodo, "2026-II")

    def test_docente_existente_puede_recibir_materia_sin_duplicar(self):
        docente = User.objects.create_user(
            username="docente2@example.test", email="docente2@example.test",
            password="XyZ!9876-Strong", is_active=True,
        )
        Profile.objects.create(
            user=docente, cedula="V-12345679", telefono="04121234567",
            tipo_estudiante="DOCENTE", nucleo=self.nucleo, rol="teacher",
            estado="activo",
        )
        url = reverse("admin_docente_asignar", args=[docente.pk])
        payload = {"unidades": [self.unidad.pk], "periodo": "2026-II"}
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(TeachingAssignment.objects.filter(docente=docente).count(), 1)
        self.assertEqual(Course.objects.filter(docente=docente).count(), 1)
