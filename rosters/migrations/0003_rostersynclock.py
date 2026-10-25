from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0004_jobphoto_customer_signature_and_more"),
        ("rosters", "0002_roster_google_calendar_event_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="RosterSyncLock",
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
                ("touched_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roster_sync_lock",
                        to="bookings.booking",
                    ),
                ),
            ],
        ),
    ]
