from django.conf import settings
from django.db import models


class FAQQuestion(models.Model):
	"""Publicly submitted FAQ question. Staff can answer and publish it."""

	name = models.CharField(max_length=120)
	email = models.EmailField()
	question = models.TextField()
	page_key = models.CharField(
		max_length=100,
		blank=True,
		help_text="Optional key to associate the question with a page/service/suburb",
	)

	answer = models.TextField(blank=True)
	answered_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
	)
	answered_at = models.DateTimeField(null=True, blank=True)

	is_published = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"FAQ #{self.id} - {self.question[:60]}"
