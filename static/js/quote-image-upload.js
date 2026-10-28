(function () {
    "use strict";

    const MAX_FILES = 6;
    const MAX_FILE_SIZE = 15 * 1024 * 1024;
    const MAX_TOTAL_SIZE = 60 * 1024 * 1024;
    const ALLOWED_FILE = /\.(avif|bmp|gif|heic|heif|jfif|jpe?g|png|tiff?|webp)$/i;
    const CONCURRENCY = 3;

    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("quoteForm");
        const input = form?.querySelector("[name=property_images]");
        const status = document.getElementById("quoteImageUploadStatus");
        const filesElement = document.getElementById("quoteImageUploadFiles");
        const progress = document.getElementById("quoteImageUploadProgress");
        const retryButton = document.getElementById("quoteImageUploadRetry");
        const cancelButton = document.getElementById("quoteImageUploadCancel");
        const submitButton = form?.querySelector('button[type="submit"]');
        const batchTokenField = form?.querySelector('[name="quote_image_batch_token"]');
        const uploadsField = form?.querySelector('[name="quote_image_uploads"]');

        if (
            !form ||
            !input ||
            !status ||
            !filesElement ||
            !progress ||
            !retryButton ||
            !cancelButton ||
            !submitButton ||
            !batchTokenField ||
            !uploadsField
        ) {
            return;
        }

        let busy = false;
        let cancelled = false;
        let preparedForSubmit = false;
        let submissionPending = false;
        let activeRequests = new Set();
        let previewUrls = [];

        function setStatus(message, isError) {
            status.textContent = message;
            status.classList.toggle("field-error", Boolean(isError));
        }

        function validate(files) {
            const list = Array.from(files || []);
            if (list.length > MAX_FILES) {
                return `Choose no more than ${MAX_FILES} property photos.`;
            }
            if (list.some((file) => file.size > MAX_FILE_SIZE)) {
                return "Each property photo must be 15 MB or smaller.";
            }
            if (list.reduce((total, file) => total + file.size, 0) > MAX_TOTAL_SIZE) {
                return "Property photos must total 60 MB or less.";
            }
            if (list.some((file) => !ALLOWED_FILE.test(file.name || ""))) {
                return "Use a supported raster image format for property photos.";
            }
            return "";
        }

        function renderFiles(files) {
            previewUrls.forEach((url) => URL.revokeObjectURL(url));
            previewUrls = [];
            filesElement.replaceChildren();

            Array.from(files || []).forEach((file, index) => {
                const row = document.createElement("div");
                row.className = "quote-image-upload-file";

                const preview = document.createElement("span");
                preview.className = "media-preview-card";
                const image = document.createElement("img");
                image.alt = `Preview of ${file.name}`;
                image.width = 64;
                image.height = 64;
                image.src = URL.createObjectURL(file);
                previewUrls.push(image.src);
                const removeButton = document.createElement("button");
                removeButton.type = "button";
                removeButton.className = "media-preview-remove";
                removeButton.textContent = "×";
                removeButton.setAttribute("aria-label", `Remove ${file.name}`);
                removeButton.dataset.removeFile = String(index);
                removeButton.disabled = busy || submissionPending || input.disabled;
                preview.append(image, removeButton);

                const details = document.createElement("div");
                const name = document.createElement("span");
                name.textContent = `${file.name} (${window.YDImageUpload.formatBytes(file.size)})`;
                const itemStatus = document.createElement("span");
                itemStatus.dataset.uploadStatus = String(index);
                itemStatus.textContent = "Selected";
                const itemProgress = document.createElement("progress");
                itemProgress.max = 100;
                itemProgress.value = 0;
                itemProgress.dataset.uploadProgress = String(index);

                details.append(name, document.createElement("br"), itemStatus, itemProgress);
                row.append(preview, details);
                filesElement.append(row);
            });
        }

        filesElement.addEventListener("click", (event) => {
            const button = event.target.closest("[data-remove-file]");
            if (!button || busy) return;
            const removeIndex = Number(button.dataset.removeFile);
            const transfer = new DataTransfer();
            Array.from(input.files || []).forEach((file, index) => {
                if (index !== removeIndex) transfer.items.add(file);
            });
            input.files = transfer.files;
            renderFiles(input.files);
            retryButton.hidden = true;
            const error = validate(input.files);
            setStatus(error || "", Boolean(error));
        });

        function updateProgress(index, loaded, total) {
            const itemProgress = filesElement.querySelector(
                `[data-upload-progress="${index}"]`
            );
            const itemStatus = filesElement.querySelector(
                `[data-upload-status="${index}"]`
            );
            if (itemProgress) {
                itemProgress.value = total ? Math.min(100, (loaded / total) * 100) : 0;
            }
            if (itemStatus) {
                itemStatus.textContent = total
                    ? `Uploading ${Math.round((loaded / total) * 100)}%`
                    : "Uploading";
            }
        }

        function updateTotalProgress(loadedByIndex, sizes) {
            const total = sizes.reduce((sum, size) => sum + size, 0);
            const loaded = loadedByIndex.reduce((sum, value) => sum + value, 0);
            progress.hidden = false;
            progress.value = total ? Math.min(100, (loaded / total) * 100) : 0;
        }

        function csrfToken() {
            return form.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
        }

        async function postForm(fields) {
            const body = new FormData();
            Object.entries(fields).forEach(([key, value]) => body.append(key, value));
            const response = await fetch(form.dataset.imageUploadUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": csrfToken() },
                body,
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || "The photo upload request failed.");
            }
            return result;
        }

        async function cancelRemoteBatch(token) {
            if (!token) return "";
            try {
                await postForm({
                    upload_action: "cancel",
                    workflow_key: form.querySelector('[name="workflow_key"]').value,
                    batch_token: token,
                });
                return "";
            } catch (error) {
                return error.message || "The server could not confirm photo cleanup.";
            }
        }

        function uploadFile(file, upload, uploadUrl, index, loadedByIndex, sizes) {
            return new Promise((resolve, reject) => {
                const request = new XMLHttpRequest();
                activeRequests.add(request);
                request.open("POST", uploadUrl);
                request.upload.addEventListener("progress", (event) => {
                    if (!event.lengthComputable) return;
                    loadedByIndex[index] = event.loaded;
                    updateProgress(index, event.loaded, event.total);
                    updateTotalProgress(loadedByIndex, sizes);
                });
                request.addEventListener("load", () => {
                    activeRequests.delete(request);
                    let result;
                    try {
                        result = JSON.parse(request.responseText);
                    } catch (_) {
                        reject(new Error(`${file.name}: Cloudinary returned an unreadable response.`));
                        return;
                    }
                    if (request.status < 200 || request.status >= 300) {
                        reject(
                            new Error(
                                result.error?.message ||
                                    `${file.name}: Cloudinary could not upload this photo.`
                            )
                        );
                        return;
                    }
                    loadedByIndex[index] = sizes[index];
                    updateProgress(index, sizes[index], sizes[index]);
                    updateTotalProgress(loadedByIndex, sizes);
                    const itemStatus = filesElement.querySelector(
                        `[data-upload-status="${index}"]`
                    );
                    if (itemStatus) itemStatus.textContent = "Uploaded";
                    resolve({
                        public_id: result.public_id,
                        version: result.version,
                        signature: result.signature,
                    });
                });
                request.addEventListener("error", () => {
                    activeRequests.delete(request);
                    reject(new Error(`${file.name}: Network error while uploading.`));
                });
                request.addEventListener("abort", () => {
                    activeRequests.delete(request);
                    reject(new Error(`${file.name}: Upload cancelled.`));
                });

                const body = new FormData();
                Object.entries(upload).forEach(([key, value]) => body.append(key, value));
                body.append("file", file);
                request.send(body);
            });
        }

        async function uploadFiles(files, batch, failedState) {
            const uploaded = new Array(files.length);
            const loadedByIndex = files.map(() => 0);
            const sizes = files.map((file) => file.size);
            let nextIndex = 0;

            async function worker() {
                while (!cancelled && !failedState.failed) {
                    const index = nextIndex++;
                    if (index >= files.length) return;
                    try {
                        const upload = batch.uploads[index];
                        const url = `https://api.cloudinary.com/v1_1/${encodeURIComponent(
                            batch.cloud_name
                        )}/image/upload`;
                        uploaded[index] = await uploadFile(
                            files[index],
                            upload,
                            url,
                            index,
                            loadedByIndex,
                            sizes
                        );
                    } catch (error) {
                        failedState.failed = true;
                        activeRequests.forEach((request) => request.abort());
                        failedState.error = error;
                    }
                }
            }

            await Promise.all(
                Array.from({ length: Math.min(CONCURRENCY, files.length) }, worker)
            );
            if (cancelled) throw new Error("Photo uploads were cancelled.");
            if (failedState.error) throw failedState.error;
            return uploaded;
        }

        async function beginUpload() {
            if (busy) return;
            const originalFiles = Array.from(input.files || []);
            const validationError = validate(originalFiles);
            if (validationError) {
                setStatus(validationError, true);
                return;
            }
            if (!originalFiles.length) return;

            busy = true;
            renderFiles(input.files);
            cancelled = false;
            retryButton.hidden = true;
            cancelButton.hidden = false;
            submitButton.setAttribute("aria-disabled", "true");
            setStatus("Preparing property photos…", false);
            let batchToken = "";

            try {
                if (!window.YDImageUpload?.prepareFiles) {
                    throw new Error("Photo optimization is unavailable. Reload the page and retry.");
                }
                const preparedFiles = await window.YDImageUpload.prepareFiles(originalFiles);
                if (cancelled) throw new Error("Photo uploads were cancelled.");
                const preparedError = validate(preparedFiles);
                if (preparedError) throw new Error(preparedError);

                setStatus("Requesting secure upload signatures…", false);
                const batch = await postForm({
                    upload_action: "sign",
                    workflow_key: form.querySelector('[name="workflow_key"]').value,
                    count: String(preparedFiles.length),
                });
                batchToken = batch.batch_token;
                if (
                    !batchToken ||
                    !Array.isArray(batch.uploads) ||
                    batch.uploads.length !== preparedFiles.length
                ) {
                    throw new Error("The server returned an invalid photo upload batch.");
                }
                if (cancelled) throw new Error("Photo uploads were cancelled.");
                setStatus("Uploading property photos…", false);
                const failedState = { failed: false, error: null };
                const receipts = await uploadFiles(
                    preparedFiles,
                    batch,
                    failedState
                );
                if (cancelled) throw new Error("Photo uploads were cancelled.");

                batchTokenField.value = batchToken;
                uploadsField.value = JSON.stringify(receipts);
                input.disabled = true;
                preparedForSubmit = true;
                setStatus("Photos uploaded. Submitting your quote request…", false);
                cancelButton.hidden = true;
                form.requestSubmit(submitButton);
            } catch (error) {
                activeRequests.forEach((request) => request.abort());
                const cleanupError = await cancelRemoteBatch(batchToken);
                batchTokenField.value = "";
                uploadsField.value = "";
                if (!cancelled) {
                    setStatus(
                        `${error.message}${
                            cleanupError
                                ? ` ${cleanupError} Unclaimed photos will expire automatically.`
                                : ""
                        } Your selected photos are still available; use Retry to try again.`,
                        true
                    );
                    retryButton.hidden = false;
                } else {
                    setStatus("Photo upload cancelled. Your selected photos are still available.", false);
                    retryButton.hidden = false;
                }
                progress.hidden = true;
                progress.value = 0;
            } finally {
                busy = false;
                activeRequests = new Set();
                renderFiles(input.files);
                cancelButton.hidden = true;
                submitButton.removeAttribute("aria-disabled");
            }
        }

        input.addEventListener("change", () => {
            renderFiles(input.files);
            retryButton.hidden = true;
            const error = validate(input.files);
            setStatus(error || "", Boolean(error));
        });

        form.addEventListener(
            "submit",
            (event) => {
                if (preparedForSubmit) {
                    preparedForSubmit = false;
                    submissionPending = true;
                    return;
                }
                if (submissionPending) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    return;
                }
                if (!input.files?.length) return;
                event.preventDefault();
                event.stopImmediatePropagation();
                beginUpload();
            },
            true
        );

        retryButton.addEventListener("click", () => form.requestSubmit());
        cancelButton.addEventListener("click", () => {
            if (!busy) return;
            cancelled = true;
            activeRequests.forEach((request) => request.abort());
            setStatus("Cancelling photo uploads…", false);
        });

        renderFiles(input.files);
    });
})();
