from django.db import migrations, models


def backfill_closed_at(apps, schema_editor):
    Conversation = apps.get_model("support", "LiveChatConversation")
    Conversation.objects.filter(
        status="closed",
        closed_at__isnull=True,
    ).update(closed_at=models.F("updated_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0007_alter_livechatconversation_intent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="livechatconversation",
            name="closed_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="livechatconversation",
            name="legal_hold",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.CreateModel(
            name="LiveChatRateLimitBucket",
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
                ("key", models.CharField(max_length=64, unique=True)),
                ("window_started_at", models.DateTimeField(db_index=True)),
                ("count", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.RunPython(backfill_closed_at, migrations.RunPython.noop),
    ]
