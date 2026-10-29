import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import TestimonialVideo
from dashboard.decorators import admin_required
from .forms import TestimonialVideoEditForm, TestimonialVideoUploadForm


logger = logging.getLogger(__name__)


@login_required
@admin_required
def testimonial_video_list(request):
    videos = TestimonialVideo.objects.all()
    return render(
        request,
        "dashboard/testimonials/testimonial_video_list.html",
        {
            "videos": videos,
            "total_count": videos.count(),
            "active_count": videos.filter(active=True).count(),
            "inactive_count": videos.filter(active=False).count(),
        },
    )


@login_required
@admin_required
def add_testimonial_videos(request):
    if request.method == "POST":
        form = TestimonialVideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            saved_assets = []
            try:
                with transaction.atomic():
                    for video_file in form.cleaned_data["videos"]:
                        title = Path(video_file.name).stem.strip()[:255]
                        testimonial = TestimonialVideo(
                            title=title or "Customer testimonial",
                            description=form.cleaned_data["description"],
                            active=form.cleaned_data["active"],
                        )
                        testimonial.video.save(video_file.name, video_file, save=False)
                        saved_assets.append(
                            (testimonial.video.storage, testimonial.video.name)
                        )
                        testimonial.save()
            except Exception:
                logger.exception("Could not save dashboard testimonial videos.")
                for storage, name in saved_assets:
                    try:
                        if not storage.delete(name):
                            logger.error(
                                "Could not clean up failed testimonial upload %s.",
                                name,
                            )
                    except Exception:
                        logger.exception(
                            "Could not clean up failed testimonial upload %s.",
                            name,
                        )
                form.add_error(
                    None,
                    "The videos could not be saved. Please try uploading them again.",
                )
            else:
                messages.success(
                    request,
                    f"{len(saved_assets)} testimonial video(s) uploaded successfully.",
                )
                return redirect("testimonial_video_list")
    else:
        form = TestimonialVideoUploadForm()

    return render(
        request,
        "dashboard/testimonials/testimonial_video_form.html",
        {
            "form": form,
            "page_title": "Add testimonial videos",
            "is_editing": False,
        },
    )


@login_required
@admin_required
def edit_testimonial_video(request, video_id):
    testimonial = get_object_or_404(TestimonialVideo, pk=video_id)
    if request.method == "POST":
        form = TestimonialVideoEditForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            updated_testimonial = form.save(commit=False)
            replacement = form.cleaned_data["replacement_video"]
            replacement_name = None
            try:
                if replacement:
                    updated_testimonial.video.save(
                        replacement.name,
                        replacement,
                        save=False,
                    )
                    replacement_name = updated_testimonial.video.name
                updated_testimonial.save()
            except Exception:
                logger.exception(
                    "Could not update testimonial video %s.",
                    testimonial.pk,
                )
                if replacement_name:
                    try:
                        if not updated_testimonial.video.storage.delete(replacement_name):
                            logger.error(
                                "Could not clean up failed testimonial replacement %s.",
                                replacement_name,
                            )
                    except Exception:
                        logger.exception(
                            "Could not clean up failed testimonial replacement %s.",
                            replacement_name,
                        )
                testimonial.refresh_from_db()
                form.instance = testimonial
                form.add_error(
                    None,
                    "The testimonial could not be updated. Please try again.",
                )
            else:
                messages.success(request, "Testimonial updated successfully.")
                return redirect("testimonial_video_list")
    else:
        form = TestimonialVideoEditForm(instance=testimonial)

    return render(
        request,
        "dashboard/testimonials/testimonial_video_form.html",
        {
            "form": form,
            "page_title": "Edit testimonial",
            "is_editing": True,
            "testimonial": testimonial,
        },
    )


@login_required
@admin_required
@require_POST
def delete_testimonial_video(request, video_id):
    testimonial = get_object_or_404(TestimonialVideo, pk=video_id)
    testimonial.delete()
    messages.success(request, "Testimonial video deleted successfully.")
    return redirect("testimonial_video_list")
