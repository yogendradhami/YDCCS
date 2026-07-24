from django.db import migrations


def consolidate_job_photo_gallery_items(apps, schema_editor):
    GalleryItem = apps.get_model("gallery", "GalleryItem")
    JobPhoto = apps.get_model("bookings", "JobPhoto")

    booking_ids = JobPhoto.objects.values_list("booking_id", flat=True).distinct()
    for booking_id in booking_ids:
        photos = JobPhoto.objects.filter(booking_id=booking_id).order_by("uploaded_at")
        if not photos.exists():
            continue

        booking = photos.first().booking
        latest_before = photos.filter(photo_type="before").order_by("-uploaded_at").first()
        latest_after = photos.filter(photo_type="after").order_by("-uploaded_at").first()
        target_photo = latest_after or latest_before or photos.first()

        gallery_items = list(
            GalleryItem.objects.filter(
                source="job_photo",
                job_photo__booking_id=booking_id,
            )
        )

        GalleryItem.objects.filter(
            source="job_photo",
            job_photo__booking_id=booking_id,
        ).update(job_photo=None)

        if not gallery_items:
            gallery_item = GalleryItem.objects.create(
                title=f"{booking.customer.full_name} - {booking.service_type}",
                service_type=booking.service_type,
                suburb=booking.suburb_postcode.split()[-1] if booking.suburb_postcode else "",
                source="job_photo",
                featured=True,
                job_photo=target_photo,
            )
        else:
            gallery_item = gallery_items[0]
            gallery_item.title = f"{booking.customer.full_name} - {booking.service_type}"
            gallery_item.service_type = booking.service_type
            gallery_item.suburb = booking.suburb_postcode.split()[-1] if booking.suburb_postcode else ""
            gallery_item.featured = True
            gallery_item.job_photo = target_photo

        gallery_item.before_image = latest_before.image if latest_before else None
        gallery_item.after_image = latest_after.image if latest_after else None
        gallery_item.image = None
        gallery_item.save()

        GalleryItem.objects.filter(
            source="job_photo",
            job_photo__booking_id=booking_id,
        ).exclude(pk=gallery_item.pk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0002_auto_gallery_unified"),
        ("bookings", "0003_jobphoto"),
    ]

    operations = [
        migrations.RunPython(consolidate_job_photo_gallery_items, migrations.RunPython.noop),
    ]
