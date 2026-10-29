import json
import logging
import time
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse
from django.urls import path, reverse

from .models import FAQQuestion, TestimonialVideo
from .testimonial_uploads import (
    TESTIMONIAL_UPLOAD_SESSION_KEY,
    cleanup_testimonial_upload,
    create_testimonial_upload,
    validate_testimonial_video_file,
    verify_testimonial_upload_receipt,
)

logger = logging.getLogger(__name__)


class TestimonialVideoAdminForm(forms.ModelForm):
    video_upload_nonce = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
    )

    class Meta:
        model = TestimonialVideo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video"].required = False
        self.fields["video"].widget.attrs["accept"] = (
            "video/mp4,video/quicktime,video/webm,video/x-m4v,"
            "video/x-msvideo,video/x-matroska,video/mpeg,video/ogg,.3gp"
        )

    def clean_video(self):
        video = self.cleaned_data.get("video")
        if not isinstance(video, UploadedFile):
            return video
        try:
            validate_testimonial_video_file(video)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return video

    def clean(self):
        cleaned_data = super().clean()
        nonce = cleaned_data.get("video_upload_nonce", "")
        upload_batch = getattr(self, "_upload_batches", {}).get(nonce)
        valid_batch = bool(
            nonce
            and upload_batch
            and upload_batch.get("user_id") == getattr(self, "_upload_user_id", None)
            and upload_batch.get("item_id") == getattr(self, "_upload_item_id", None)
            and upload_batch.get("expires_at", 0) > int(time.time())
            and upload_batch.get("finalized")
            and upload_batch.get("verified")
        )
        video = cleaned_data.get("video")
        if isinstance(video, UploadedFile) and nonce:
            self.add_error("video", "Use either direct upload or the file input, not both.")
        elif nonce and not valid_batch:
            self.add_error("video", "The uploaded video could not be verified. Upload it again.")
        elif not video and not valid_batch:
            self.add_error("video", "Choose a video to upload.")
        return cleaned_data

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if isinstance(thumbnail, UploadedFile) and thumbnail.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Video thumbnails must be 10 MB or smaller.")
        return thumbnail


@admin.register(FAQQuestion)
class FAQQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "name",
        "email",
        "is_published",
        "created_at",
    )

    list_filter = (
        "is_published",
        "created_at",
    )

    search_fields = (
        "question",
        "answer",
        "name",
        "email",
    )

    readonly_fields = (
        "created_at",
        "answered_at",
    )


@admin.register(TestimonialVideo)
class TestimonialVideoAdmin(admin.ModelAdmin):
    form = TestimonialVideoAdminForm
    change_form_template = "admin/core/testimonialvideo/change_form.html"
    list_display = (
        "title",
        "active",
        "created_at",
    )

    list_filter = (
        "active",
    )

    search_fields = (
        "title",
        "description",
    )

    class Media:
        js = ("js/admin/testimonial-video-upload.js",)

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        session_batches = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {})
        return type(
            "RequestBoundTestimonialVideoAdminForm",
            (form_class,),
            {
                "_upload_batches": session_batches,
                "_upload_user_id": request.user.pk,
                "_upload_item_id": obj.pk if obj else None,
            },
        )

    def render_change_form(self, request, context, *args, **kwargs):
        form = context["adminform"].form
        nonce_widget = form.fields["video_upload_nonce"].widget
        nonce_widget.attrs.update(
            {
                "data-upload-url": reverse(
                    "admin:core_testimonialvideo_upload_batch"
                ),
                "data-cloud-name": settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                "data-item-id": str(form.instance.pk or ""),
            }
        )
        return super().render_change_form(request, context, *args, **kwargs)

    def get_urls(self):
        custom_urls = [
            path(
                "upload-batch/",
                self.admin_site.admin_view(self.upload_batch_view),
                name="core_testimonialvideo_upload_batch",
            ),
        ]
        return custom_urls + super().get_urls()

    def _authorized_upload_item(self, request, raw_item_id):
        if raw_item_id in (None, ""):
            if not self.has_add_permission(request):
                raise PermissionDenied
            return None
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            raise ValueError("The testimonial video identifier is invalid.")
        if item_id <= 0:
            raise ValueError("The testimonial video identifier is invalid.")
        item = self.get_object(request, str(item_id))
        if item is None:
            raise ValueError("The testimonial video no longer exists.")
        if not self.has_change_permission(request, item):
            raise PermissionDenied
        return item

    def _get_upload_batch(self, request, nonce, item):
        batch = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {}).get(nonce)
        item_id = item.pk if item else None
        if (
            not batch
            or batch.get("user_id") != request.user.pk
            or batch.get("item_id") != item_id
            or batch.get("expires_at", 0) <= int(time.time())
        ):
            return None
        return batch

    def _cleanup_expired_uploads(self, request):
        batches = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {})
        now = int(time.time())
        for nonce, batch in list(batches.items()):
            if batch.get("expires_at", 0) <= now:
                if cleanup_testimonial_upload(batch):
                    batches.pop(nonce, None)
        if batches or TESTIMONIAL_UPLOAD_SESSION_KEY in request.session:
            request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches

    def upload_batch_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "POST is required."}, status=405)

        self._cleanup_expired_uploads(request)
        action = request.POST.get("action", "")
        batches = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {})

        if action == "sign":
            try:
                item = self._authorized_upload_item(
                    request,
                    request.POST.get("item_id"),
                )
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
            nonce, batch, upload = create_testimonial_upload(
                user_id=request.user.pk,
                item_id=item.pk if item else None,
            )
            batches[nonce] = batch
            request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
            return JsonResponse(
                {
                    "nonce": nonce,
                    "cloud_name": settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                    "upload": upload,
                    "chunk_size": 6 * 1024 * 1024,
                }
            )

        nonce = request.POST.get("nonce", "")
        batch = batches.get(nonce)
        if action == "cancel":
            if batch:
                try:
                    item = self._authorized_upload_item(
                        request,
                        request.POST.get("item_id"),
                    )
                except ValueError as exc:
                    return JsonResponse({"error": str(exc)}, status=400)
                item_id = item.pk if item else None
                if (
                    batch.get("user_id") != request.user.pk
                    or batch.get("item_id") != item_id
                ):
                    return JsonResponse(
                        {"error": "This upload batch is unavailable."},
                        status=400,
                    )
                if not cleanup_testimonial_upload(batch):
                    return JsonResponse(
                        {"error": "The video could not be safely cleaned up; retry cancellation."},
                        status=502,
                    )
                batches.pop(nonce, None)
            request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
            return JsonResponse({"cancelled": True})

        if action != "finalize":
            return JsonResponse({"error": "Unsupported upload action."}, status=400)

        batch = None
        try:
            item = self._authorized_upload_item(
                request,
                request.POST.get("item_id"),
            )
            batch = self._get_upload_batch(request, nonce, item)
            if not batch or batch.get("finalized"):
                raise ValueError("The upload batch expired or is unavailable.")
            receipt = json.loads(request.POST.get("receipt", ""))
            verified = verify_testimonial_upload_receipt(batch, receipt)
        except PermissionDenied:
            raise
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            if batch and cleanup_testimonial_upload(batch):
                batches.pop(nonce, None)
                request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
            return JsonResponse({"error": str(exc)}, status=400)
        except Exception:
            logger.exception("Could not verify testimonial video upload batch.")
            return JsonResponse(
                {"error": "Cloudinary could not verify the video. Retry or cancel the upload."},
                status=502,
            )

        batch["verified"] = verified
        batch["finalized"] = True
        batches[nonce] = batch
        request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
        return JsonResponse({"finalized": True})

    def save_model(self, request, obj, form, change):
        nonce = form.cleaned_data.get("video_upload_nonce", "")
        if nonce:
            batch = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {}).get(nonce)
            if (
                not batch
                or batch.get("user_id") != request.user.pk
                or batch.get("item_id") != (obj.pk if change else None)
                or not batch.get("finalized")
                or not batch.get("verified")
            ):
                raise PermissionDenied("The testimonial video upload is no longer valid.")
            obj.video = batch["verified"]["public_id"]
        super().save_model(request, obj, form, change)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        self._cleanup_expired_uploads(request)
        nonce = request.POST.get("video_upload_nonce", "") if request.method == "POST" else ""
        try:
            response = super().changeform_view(
                request,
                object_id=object_id,
                form_url=form_url,
                extra_context=extra_context,
            )
        except Exception:
            if nonce:
                batches = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {})
                batch = batches.get(nonce)
                if batch and cleanup_testimonial_upload(batch):
                    batches.pop(nonce, None)
                    request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
            raise

        if nonce and response.status_code in {301, 302}:
            batches = request.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {})
            batches.pop(nonce, None)
            request.session[TESTIMONIAL_UPLOAD_SESSION_KEY] = batches
        return response

    def changelist_view(self, request, extra_context=None):
        self._cleanup_expired_uploads(request)
        return super().changelist_view(request, extra_context=extra_context)
