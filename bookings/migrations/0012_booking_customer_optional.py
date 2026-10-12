from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0011_booking_idempotency_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bookings",
                to="customers.customer",
            ),
        ),
    ]
