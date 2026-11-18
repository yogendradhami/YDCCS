from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0005_reconcile_paid_invoice_bookings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("sent", "Sent"),
                    ("pending", "Pending payment"),
                    ("paid", "Paid"),
                    ("overdue", "Overdue"),
                    ("cancelled", "Cancelled"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="stripe_checkout_idempotency_key",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_method",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_confirmation_email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=100)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-received_at"]},
        ),
    ]
