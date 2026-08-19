from django.test import TestCase, Client, override_settings
from django.core import mail
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from dashboard.models import CareerApplication


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CareerEmailTests(TestCase):
	def setUp(self):
		self.client = Client()

	def test_application_submission_sends_email(self):
		data = {
			"full_name": "Test Applicant",
			"email": "applicant@example.com",
			"phone": "0412345678",
			"position": "residential_cleaner",
			"years_cleaning_experience": "1",
			"cover_letter": "I am interested.",
			"consent": "on",
		}
		resume = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fakepdf", content_type="application/pdf")

		response = self.client.post(reverse("careers"), data={**data}, files={"resume": resume})
		self.assertEqual(response.status_code, 302)

		# One email should be sent (confirmation)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("Application Received", mail.outbox[0].subject)

		app = CareerApplication.objects.filter(email="applicant@example.com").first()
		self.assertIsNotNone(app)

	def test_admin_update_sends_email(self):
		app = CareerApplication.objects.create(full_name="Jane Doe", email="jane@example.com")

		User = get_user_model()
		admin = User.objects.create_user("admin", "admin@example.com", "pass")
		admin.is_staff = True
		admin.save()

		self.client.force_login(admin)

		url = reverse("career_detail", args=[app.id])
		response = self.client.post(url, {"status": "reviewing", "admin_notes": "Please review CV."})
		self.assertEqual(response.status_code, 302)

		# One email should be sent
		self.assertGreaterEqual(len(mail.outbox), 1)
		last = mail.outbox[-1]
		self.assertIn("Application Update", last.subject)
		app.refresh_from_db()
		self.assertEqual(app.status, "reviewing")
