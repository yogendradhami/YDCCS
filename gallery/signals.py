# Gallery signals to auto-sync images from other sources
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from bookings.models import JobPhoto
from .models import GalleryItem


@receiver(post_save, sender=JobPhoto)
def auto_add_job_photo_to_gallery(sender, instance, created, **kwargs):
    """
    Automatically add job photos to gallery when uploaded
    Links the JobPhoto to GalleryItem for unified display
    """
    if created and instance.photo_type in ['before', 'after']:
        # Check if gallery item already exists for this job
        existing = GalleryItem.objects.filter(job_photo=instance).first()

        if not existing:
            booking = instance.booking
            service_type = booking.service_type
            suburb_value = booking.suburb_postcode or ""

            # Create or update gallery item
            gallery_item, created_new = GalleryItem.objects.get_or_create(
                job_photo=instance,
                defaults={
                    'title': booking.customer.gallery_display_name if booking.customer else f"{booking.customer.full_name} - {service_type}",
                    'service_type': service_type,
                    'suburb': suburb_value,
                    'image': instance.image,
                    'source': 'job_photo',
                    'featured': True,
                }
            )

            # Update existing if needed
            if not created_new:
                gallery_item.title = booking.customer.gallery_display_name if booking.customer else f"{booking.customer.full_name} - {service_type}"
                gallery_item.service_type = service_type
                gallery_item.suburb = suburb_value
                gallery_item.image = instance.image
                gallery_item.save()


@receiver(post_delete, sender=JobPhoto)
def remove_job_photo_from_gallery(sender, instance, **kwargs):
    """
    Remove gallery item when job photo is deleted
    """
    try:
        gallery_item = GalleryItem.objects.get(job_photo=instance)
        gallery_item.delete()
    except GalleryItem.DoesNotExist:
        pass
