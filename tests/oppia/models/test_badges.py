from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.urls import reverse

from oppia.models import CertificateTemplate
from oppia.test import OppiaTestCase


class BadgesModelTest(OppiaTestCase):
    
    fixtures = ['tests/test_user.json',
                'tests/test_oppia.json',
                'tests/test_quiz.json',
                'tests/test_permissions.json',
                'tests/test_course_permissions.json',
                'default_badges.json']
    url = reverse("admin:oppia_certificatetemplate_add")
    
    def test_certificate_portrait_valid(self):
        count_start = CertificateTemplate.objects.all().count()
        self.client.force_login(self.admin_user)
        with open('./oppia/fixtures/reference_files/certificate_templates/certificate_portrait_valid.png', 'rb') \
                as cert_file:
            self.client.post(self.url, {
                'course': 1,
                'badge': 1,
                'enabled': True,
                'image_file': cert_file,
                'name_x': 0,
                'name_y': 0,
                'course_title_x': 0,
                'course_title_y': 0,
                'date_x': 0,
                'date_y': 0
                })
        count_end = CertificateTemplate.objects.all().count()
        self.assertEqual(count_start+1, count_end)

    def test_certificate_portrait_invalid(self):
        count_start = CertificateTemplate.objects.all().count()
        self.client.force_login(self.admin_user)
        with open('./oppia/fixtures/reference_files/certificate_templates/certificate_portrait_invalid.png', 'rb') \
                as cert_file:
            self.client.post(self.url, {
                'course': 1,
                'badge': 1,
                'enabled': True,
                'image_file': cert_file,
                'name_x': 0,
                'name_y': 0,
                'course_title_x': 0,
                'course_title_y': 0,
                'date_x': 0,
                'date_y': 0
                })
        self.assertRaises(ValidationError)
        count_end = CertificateTemplate.objects.all().count()
        self.assertEqual(count_start, count_end)
        
    def test_certificate_landscape_valid(self):
        count_start = CertificateTemplate.objects.all().count()
        self.client.force_login(self.admin_user)
        with open('./oppia/fixtures/reference_files/certificate_templates/certificate_landscape_valid.png', 'rb') \
                as cert_file:
            self.client.post(self.url, {
                'course': 1,
                'badge': 1,
                'enabled': True,
                'image_file': cert_file,
                'name_x': 0,
                'name_y': 0,
                'course_title_x': 0,
                'course_title_y': 0,
                'date_x': 0,
                'date_y': 0
                })
        count_end = CertificateTemplate.objects.all().count()
        self.assertEqual(count_start+1, count_end)

    def test_certificate_landscape_invalid(self):
        count_start = CertificateTemplate.objects.all().count()
        self.client.force_login(self.admin_user)
        with open('./oppia/fixtures/reference_files/certificate_templates/certificate_landscape_invalid.png', 'rb') \
                as cert_file:
            self.client.post(self.url, {
                'course': 1,
                'badge': 1,
                'enabled': True,
                'image_file': cert_file,
                'name_x': 0,
                'name_y': 0,
                'course_title_x': 0,
                'course_title_y': 0,
                'date_x': 0,
                'date_y': 0
                })
        self.assertRaises(ValidationError)
        count_end = CertificateTemplate.objects.all().count()
        self.assertEqual(count_start, count_end)
