from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer, MarketingSubscriber
from dashboard.models import CampaignLog

from .models import Review


class ReputationDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            username="reviews-admin",
            email="reviews-admin@example.com",
            password="test-password",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_review_list_displays_actual_review_fields_and_filters(self):
        Review.objects.create(
            customer_name="Alex Example",
            suburb="Richmond",
            rating=5,
            review_text="Excellent cleaning.",
            featured=True,
        )

        response = self.client.get(reverse("review_list"), {"q": "Richmond"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Example")
        self.assertContains(response, "Excellent cleaning.")
        self.assertContains(response, "Featured on site")

    def test_review_delete_confirmation_is_get_and_deletion_is_post(self):
        review = Review.objects.create(
            customer_name="Alex Example",
            rating=4,
            review_text="Very good.",
        )

        confirmation = self.client.get(reverse("delete_review", args=[review.pk]))

        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.assertContains(confirmation, "Remove this review?")

        response = self.client.post(reverse("delete_review", args=[review.pk]))

        self.assertRedirects(response, reverse("review_list"))
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_campaign_history_delete_confirmation_is_get_and_deletion_is_post(self):
        campaign = CampaignLog.objects.create(
            sent_by=self.admin,
            campaign_type="vip",
            title="VIP test send",
            recipients_count=3,
        )

        confirmation = self.client.get(
            reverse("delete_campaign_history", args=[campaign.pk])
        )

        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(CampaignLog.objects.filter(pk=campaign.pk).exists())
        self.assertContains(confirmation, "Delete this campaign record?")

        response = self.client.post(
            reverse("delete_campaign_history", args=[campaign.pk])
        )

        self.assertRedirects(response, reverse("campaign_center"))
        self.assertFalse(CampaignLog.objects.filter(pk=campaign.pk).exists())

    def test_newsletter_subscriber_delete_confirmation_is_get_and_deletion_is_post(self):
        subscriber = MarketingSubscriber.objects.create(
            email="customer@example.com",
            consent_given=True,
            is_active=True,
            source="test",
        )

        confirmation = self.client.get(
            reverse("delete_newsletter_subscriber", args=[subscriber.pk])
        )

        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(MarketingSubscriber.objects.filter(pk=subscriber.pk).exists())
        self.assertContains(confirmation, "Remove this subscriber?")

        response = self.client.post(
            reverse("delete_newsletter_subscriber", args=[subscriber.pk])
        )

        self.assertRedirects(response, reverse("campaign_center"))
        self.assertFalse(MarketingSubscriber.objects.filter(pk=subscriber.pk).exists())

    def test_promotional_preview_only_includes_active_consenting_customers(self):
        Customer.objects.create(
            full_name="Consenting Customer",
            email="CONSENTING@example.com",
            phone="0400000000",
            total_revenue=1500,
        )
        Customer.objects.create(
            full_name="Unconsented Customer",
            email="unconsented@example.com",
            phone="0400000001",
            total_revenue=2000,
        )
        MarketingSubscriber.objects.create(
            email="consenting@example.com",
            consent_given=True,
            is_active=True,
            source="test",
        )
        MarketingSubscriber.objects.create(
            email="unconsented@example.com",
            consent_given=False,
            is_active=True,
            source="test",
        )

        response = self.client.get(reverse("campaign_preview", args=["vip"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["recipient_count"], 1)
        self.assertEqual(
            [customer.full_name for customer in response.context["recipients"]],
            ["Consenting Customer"],
        )

    def test_campaign_center_and_performance_pages_render(self):
        campaign_center = self.client.get(reverse("campaign_center"))
        performance = self.client.get(reverse("campaign_performance"))
        review_requests = self.client.get(reverse("review_requests"))
        analytics = self.client.get(reverse("review_analytics"))

        self.assertEqual(campaign_center.status_code, 200)
        self.assertContains(campaign_center, "Choose an audience")
        self.assertEqual(performance.status_code, 200)
        self.assertContains(performance, "Campaign history")
        self.assertEqual(review_requests.status_code, 200)
        self.assertContains(review_requests, "Request history and actions")
        self.assertEqual(analytics.status_code, 200)
        self.assertContains(analytics, "Request coverage")

    def test_linked_edit_and_detail_pages_render(self):
        review = Review.objects.create(
            customer_name="Alex Example",
            rating=5,
            review_text="Excellent cleaning.",
        )
        campaign = CampaignLog.objects.create(
            sent_by=self.admin,
            campaign_type="review",
            title="Review follow-up",
            recipients_count=2,
        )
        subscriber = MarketingSubscriber.objects.create(
            email="subscriber@example.com",
            consent_given=True,
            is_active=True,
            source="test",
        )

        pages = (
            reverse("edit_review", args=[review.pk]),
            reverse("campaign_history_detail", args=[campaign.pk]),
            reverse("edit_campaign_history", args=[campaign.pk]),
            reverse("newsletter_subscriber_detail", args=[subscriber.pk]),
            reverse("edit_newsletter_subscriber", args=[subscriber.pk]),
        )

        for path in pages:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
