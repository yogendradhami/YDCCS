# Generated migration for unified gallery model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
        ('gallery', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='galleryitem',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='gallery/uploads/'),
        ),
        migrations.AddField(
            model_name='galleryitem',
            name='source',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin Upload'),
                    ('job_photo', 'Job Photo'),
                    ('customer', 'Customer Upload'),
                    ('employee', 'Employee Upload'),
                    ('booking', 'Booking Form'),
                    ('manual', 'Manual Upload'),
                ],
                default='manual',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='galleryitem',
            name='job_photo',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='gallery_item',
                to='bookings.JobPhoto',
            ),
        ),
        migrations.AddField(
            model_name='galleryitem',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='galleryitem',
            name='before_image',
            field=models.ImageField(blank=True, null=True, upload_to='gallery/before/'),
        ),
        migrations.AlterField(
            model_name='galleryitem',
            name='after_image',
            field=models.ImageField(blank=True, null=True, upload_to='gallery/after/'),
        ),
        migrations.AlterModelOptions(
            name='galleryitem',
            options={'ordering': ['-created_at']},
        ),
    ]
