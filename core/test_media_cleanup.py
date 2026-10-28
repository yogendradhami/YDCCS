from unittest.mock import Mock, patch

from django.test import TestCase
from django.db.models.signals import post_delete, post_save, pre_save

from core.media_cleanup import (
    delete_cloudinary_asset_if_unreferenced,
    is_cloudinary_asset_referenced,
    track_cloudinary_file_changes,
)
from gallery.models import GalleryItem


class CloudinaryMediaCleanupTests(TestCase):
    def connect_gallery_cleanup_signals(self):
        with patch("core.media_cleanup._is_cloudinary_storage", return_value=True):
            track_cloudinary_file_changes(GalleryItem)

    def disconnect_gallery_cleanup_signals(self):
        label = GalleryItem._meta.label_lower
        pre_save.disconnect(
            sender=GalleryItem,
            dispatch_uid=f"cloudinary-cleanup-before-save-{label}",
        )
        post_save.disconnect(
            sender=GalleryItem,
            dispatch_uid=f"cloudinary-cleanup-after-save-{label}",
        )
        post_delete.disconnect(
            sender=GalleryItem,
            dispatch_uid=f"cloudinary-cleanup-after-delete-{label}",
        )

    def test_asset_is_not_deleted_while_a_record_references_it(self):
        public_id = "gallery/admin/shared/image"
        GalleryItem.objects.create(
            title="Shared gallery image",
            service_type="House Cleaning",
            source="manual",
            image=public_id,
        )
        storage = Mock()

        with patch(
            "core.media_cleanup._cloudinary_file_fields",
            return_value=[
                (GalleryItem, GalleryItem._meta.get_field("image")),
            ],
        ):
            self.assertTrue(is_cloudinary_asset_referenced(public_id))
            deleted = delete_cloudinary_asset_if_unreferenced(storage, public_id)

        self.assertFalse(deleted)
        storage.delete.assert_not_called()

    def test_unreferenced_asset_is_removed_through_its_cloudinary_storage(self):
        public_id = "gallery/admin/orphan/image"
        storage = Mock()
        storage.delete.return_value = None

        with patch("core.media_cleanup._cloudinary_file_fields", return_value=[]):
            deleted = delete_cloudinary_asset_if_unreferenced(storage, public_id)

        self.assertTrue(deleted)
        storage.delete.assert_called_once_with(public_id)

    def test_cloudinary_storage_deletion_failure_is_reported(self):
        public_id = "gallery/admin/orphan/image"
        storage = Mock()
        storage.delete.side_effect = OSError("Cloudinary unavailable")

        with (
            patch("core.media_cleanup._cloudinary_file_fields", return_value=[]),
            patch("core.media_cleanup.logger.exception") as log_exception,
        ):
            deleted = delete_cloudinary_asset_if_unreferenced(storage, public_id)

        self.assertFalse(deleted)
        storage.delete.assert_called_once_with(public_id)
        log_exception.assert_called_once()

    def test_deleting_a_record_removes_its_unreferenced_file_after_commit(self):
        public_id = "gallery/admin/deleted/image"
        item = GalleryItem.objects.create(
            title="Deleted gallery image",
            service_type="House Cleaning",
            source="manual",
            image=public_id,
        )
        storage = GalleryItem._meta.get_field("image").storage
        self.connect_gallery_cleanup_signals()
        try:
            with (
                patch.object(storage, "delete", return_value=True) as delete,
                patch(
                    "core.media_cleanup._cloudinary_file_fields",
                    return_value=[
                        (GalleryItem, GalleryItem._meta.get_field("image")),
                    ],
                ),
                self.captureOnCommitCallbacks(execute=True),
            ):
                item.delete()
        finally:
            self.disconnect_gallery_cleanup_signals()

        delete.assert_called_once_with(public_id)

    def test_replacing_a_record_file_removes_only_the_old_unreferenced_asset(self):
        old_public_id = "gallery/admin/replaced/old"
        item = GalleryItem.objects.create(
            title="Replaced gallery image",
            service_type="House Cleaning",
            source="manual",
            image=old_public_id,
        )
        storage = GalleryItem._meta.get_field("image").storage
        self.connect_gallery_cleanup_signals()
        try:
            with (
                patch.object(storage, "delete", return_value=True) as delete,
                patch(
                    "core.media_cleanup._cloudinary_file_fields",
                    return_value=[
                        (GalleryItem, GalleryItem._meta.get_field("image")),
                    ],
                ),
                self.captureOnCommitCallbacks(execute=True),
            ):
                item.image = "gallery/admin/replaced/new"
                item.save()
        finally:
            self.disconnect_gallery_cleanup_signals()

        delete.assert_called_once_with(old_public_id)
        item.refresh_from_db()
        self.assertEqual(item.image.name, "gallery/admin/replaced/new")
