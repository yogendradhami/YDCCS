(function () {
    "use strict";

    const form = document.getElementById("galleryForm");
    if (!form) return;

    const MAX_FILE_BYTES = 20 * 1024 * 1024;
    const MAX_BATCH_BYTES = 200 * 1024 * 1024;
    const ALLOWED_EXTENSIONS = /\.(jpe?g|png|webp|gif|heic|heif)$/i;
    const nonceInput = document.getElementById("galleryUploadNonce");
    const submitButton = document.getElementById("gallerySubmit");
    const status = document.getElementById("galleryUploadStatus");
    const progressSection = document.getElementById("galleryUploadProgress");
    const progressBar = document.getElementById("galleryBatchProgress");
    const progressSummary = document.getElementById("galleryUploadSummary");
    const progressItems = document.getElementById("galleryUploadItems");
    const cancelButton = document.getElementById("cancelStagedUploads");
    const inputs = Array.from(form.querySelectorAll('input[type="file"]'));
    const activeRequests = new Set();
    const previewUrls = new Map();
    let busy = false;
    let cancelled = false;

    function csrfToken() {
        const input = form.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function formatBytes(bytes) {
        if (window.YDImageUpload) return window.YDImageUpload.formatBytes(bytes);
        return `${Math.round(bytes / 1024)} KB`;
    }

    function fileLabel(slot, index) {
        const labels = {
            image: "Main image",
            before_image: "Before image",
            after_image: "After image",
            additional_images: `Additional image ${index + 1}`,
        };
        return labels[slot] || "Gallery image";
    }

    function currentSelections() {
        const selected = [];
        inputs.forEach((input) => {
            const slot = input.name;
            Array.from(input.files || []).forEach((file) => selected.push({ slot, file }));
        });
        return selected;
    }

    function showFilePreviews() {
        previewUrls.forEach((url) => URL.revokeObjectURL(url));
        previewUrls.clear();

        document.querySelectorAll("[data-preview-for]").forEach((container) => {
            const slot = container.dataset.previewFor;
            const input = inputs.find((candidate) => candidate.name === slot);
            container.replaceChildren();
            if (!input) return;

            Array.from(input.files || []).forEach((file, index) => {
                const card = document.createElement("figure");
                const image = document.createElement("img");
                const caption = document.createElement("figcaption");
                caption.textContent = `${file.name} · ${formatBytes(file.size)}`;
                if (/^image\//i.test(file.type) && !/heic|heif/i.test(file.type)) {
                    const url = URL.createObjectURL(file);
                    previewUrls.set(`${slot}-${index}`, url);
                    image.src = url;
                    image.alt = file.name;
                    card.appendChild(image);
                }
                card.appendChild(caption);
                container.appendChild(card);
            });
        });
    }

    function setStatus(message, isError) {
        status.textContent = message;
        status.classList.toggle("is-error", Boolean(isError));
    }

    function updateOverallProgress(states) {
        const total = states.reduce((sum, state) => sum + state.size, 0);
        const completed = states.reduce((sum, state) => sum + state.loaded, 0);
        const percent = total ? Math.floor((completed / total) * 100) : 0;
        progressBar.value = percent;
        progressSummary.textContent = `${percent}% · ${formatBytes(completed)} of ${formatBytes(total)}`;
    }

    function renderUploadRows(selections, states) {
        progressItems.replaceChildren();
        selections.forEach((selection, index) => {
            const row = document.createElement("div");
            row.className = "gallery-upload-item";
            const label = document.createElement("span");
            label.textContent = fileLabel(selection.slot, index) + ": " + selection.file.name;
            const progress = document.createElement("progress");
            progress.max = 100;
            progress.value = 0;
            progress.setAttribute("aria-label", `Upload progress for ${selection.file.name}`);
            row.append(label, progress);
            progressItems.appendChild(row);
            states[index].progressElement = progress;
        });
    }

    async function postBatch(action, values) {
        const body = new URLSearchParams({
            csrfmiddlewaretoken: csrfToken(),
            upload_action: action,
            ...values,
        });
        const response = await fetch(form.dataset.uploadUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
            body,
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "The gallery upload request failed.");
        }
        return payload;
    }

    function uploadFile(upload, file, state) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            activeRequests.add(xhr);
            xhr.open(
                "POST",
                `https://api.cloudinary.com/v1_1/${encodeURIComponent(
                    window.galleryCloudName
                )}/image/upload`
            );
            xhr.upload.onprogress = (event) => {
                if (!event.lengthComputable) return;
                state.loaded = Math.min(file.size, event.loaded);
                state.progressElement.value = Math.floor((state.loaded / file.size) * 100);
                updateOverallProgress(window.galleryUploadStates);
            };
            xhr.onload = () => {
                activeRequests.delete(xhr);
                let result;
                try {
                    result = JSON.parse(xhr.responseText);
                } catch (_error) {
                    reject(new Error("Cloudinary returned an unreadable upload response."));
                    return;
                }
                if (xhr.status < 200 || xhr.status >= 300) {
                    const error = new Error(result.error && result.error.message
                        ? result.error.message
                        : "Cloudinary could not upload this image.");
                    error.retryable = xhr.status === 408 || xhr.status === 429 || xhr.status >= 500;
                    reject(error);
                    return;
                }
                state.loaded = file.size;
                state.progressElement.value = 100;
                updateOverallProgress(window.galleryUploadStates);
                resolve(result);
            };
            xhr.onerror = () => {
                activeRequests.delete(xhr);
                const error = new Error("Network error while uploading to Cloudinary.");
                error.retryable = true;
                reject(error);
            };
            xhr.onabort = () => {
                activeRequests.delete(xhr);
                reject(new Error("Upload cancelled."));
            };

            const body = new FormData();
            body.append("file", file);
            body.append("api_key", upload.api_key);
            body.append("timestamp", String(upload.timestamp));
            body.append("signature", upload.signature);
            body.append("public_id", upload.public_id);
            body.append("allowed_formats", upload.allowed_formats);
            xhr.send(body);
        });
    }

    async function uploadWithRetry(upload, file, state) {
        for (let attempt = 0; attempt < 3; attempt += 1) {
            if (cancelled) throw new Error("Upload cancelled.");
            try {
                return await uploadFile(upload, file, state);
            } catch (error) {
                if (!error.retryable || cancelled || attempt === 2) throw error;
                state.loaded = 0;
                state.progressElement.value = 0;
                updateOverallProgress(window.galleryUploadStates);
                await new Promise((resolve) => window.setTimeout(resolve, 500 * (attempt + 1)));
            }
        }
        throw new Error("Cloudinary could not upload this image.");
    }

    async function uploadConcurrently(uploads, prepared, states) {
        const receipts = new Array(uploads.length);
        let nextIndex = 0;
        async function worker() {
            while (nextIndex < uploads.length) {
                if (cancelled) throw new Error("Upload cancelled.");
                const index = nextIndex;
                nextIndex += 1;
                receipts[index] = await uploadWithRetry(
                    uploads[index],
                    prepared[index],
                    states[index]
                );
            }
        }
        await Promise.all(
            Array.from({ length: Math.min(3, uploads.length) }, () => worker())
        );
        return receipts;
    }

    async function cancelBatch(nonce) {
        if (!nonce) return true;
        try {
            await postBatch("cancel", {
                nonce,
                item_id: form.dataset.itemId || "",
            });
            return true;
        } catch (_error) {
            setStatus("The staged batch could not be cancelled. Reload and retry before uploading new images.", true);
            return false;
        }
    }

    async function cancelStagedUploads() {
        cancelled = true;
        activeRequests.forEach((request) => request.abort());
        const nonce = nonceInput.value;
        const cancelledSuccessfully = await cancelBatch(nonce);
        if (!cancelledSuccessfully) return;
        nonceInput.value = "";
        const staged = document.querySelector(".gallery-staged-batch");
        if (staged) staged.remove();
        cancelButton.hidden = true;
        setStatus("Staged images cancelled. You can now select a new set of images.");
    }

    inputs.forEach((input) => input.addEventListener("change", showFilePreviews));
    document.querySelectorAll(".gallery-dropzone").forEach((zone) => {
        zone.addEventListener("dragover", (event) => {
            event.preventDefault();
            zone.classList.add("is-dragging");
        });
        zone.addEventListener("dragleave", () => zone.classList.remove("is-dragging"));
        zone.addEventListener("drop", (event) => {
            event.preventDefault();
            zone.classList.remove("is-dragging");
            const input = inputs.find((candidate) => candidate.name === zone.dataset.slot);
            const files = Array.from(event.dataTransfer.files || []);
            if (!input || !files.length) return;
            if (input.name !== "additional_images" && files.length > 1) {
                setStatus("Choose one image for each main, before, or after image slot.", true);
                return;
            }
            const transfer = new DataTransfer();
            if (input.name === "additional_images") {
                Array.from(input.files || []).forEach((file) => transfer.items.add(file));
                files.forEach((file) => transfer.items.add(file));
            } else {
                transfer.items.add(files[0]);
            }
            input.files = transfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });
    });

    if (cancelButton) cancelButton.addEventListener("click", cancelStagedUploads);
    if (nonceInput.value) {
        setStatus("Verified images are staged. Save this form to attach them, or cancel the staged batch before choosing another set.");
    }

    form.addEventListener("submit", async (event) => {
        if (busy) {
            event.preventDefault();
            return;
        }
        const selections = currentSelections();
        if (!selections.length) {
            if (nonceInput.value) {
                busy = true;
                submitButton.disabled = true;
                submitButton.textContent = "Saving and attaching images…";
            }
            return;
        }
        if (nonceInput.value) {
            event.preventDefault();
            setStatus("Cancel the currently staged batch before starting a different image upload.", true);
            return;
        }
        if (!form.reportValidity()) {
            event.preventDefault();
            return;
        }

        const bytes = selections.reduce((sum, selected) => sum + selected.file.size, 0);
        const hasInvalidFile = selections.some((selected) => {
            return !ALLOWED_EXTENSIONS.test(selected.file.name)
                || selected.file.size <= 0
                || selected.file.size > MAX_FILE_BYTES;
        });
        if (hasInvalidFile) {
            event.preventDefault();
            setStatus("Each image must be JPG, PNG, WEBP, GIF, HEIC or HEIF and no larger than 20 MB.", true);
            return;
        }
        if (selections.length > 23 || bytes > MAX_BATCH_BYTES) {
            event.preventDefault();
            setStatus("Choose no more than 23 images and keep the total upload below 200 MB.", true);
            return;
        }
        const includesHeic = selections.some(({ file }) => /\.(heic|heif)$/i.test(file.name));
        if (includesHeic) {
            busy = true;
            submitButton.disabled = true;
            submitButton.textContent = "Converting HEIC images and saving…";
            setStatus("HEIC/HEIF files use the existing secure server-side conversion.");
            return;
        }
        event.preventDefault();

        busy = true;
        cancelled = false;
        submitButton.disabled = true;
        cancelButton.hidden = false;
        cancelButton.textContent = "Cancel upload";
        progressSection.hidden = false;
        setStatus("Preparing images for direct upload…");

        const states = selections.map(({ file }) => ({
            size: file.size,
            loaded: 0,
            progressElement: null,
        }));
        window.galleryUploadStates = states;
        renderUploadRows(selections, states);
        updateOverallProgress(states);

        let nonce = "";
        try {
            const prepared = [];
            for (const selection of selections) {
                prepared.push(
                    window.YDImageUpload
                        ? await window.YDImageUpload.prepareImage(selection.file)
                        : selection.file
                );
            }
            const preparedBytes = prepared.reduce((sum, file) => sum + file.size, 0);
            if (prepared.some((file) => file.size > MAX_FILE_BYTES) || preparedBytes > MAX_BATCH_BYTES) {
                throw new Error("Prepared images exceed the per-image or total upload limit.");
            }

            const slots = selections.map((selected) => selected.slot);
            const signed = await postBatch("sign", {
                slots: JSON.stringify(slots),
                item_id: form.dataset.itemId || "",
            });
            nonce = signed.nonce;
            nonceInput.value = nonce;
            window.galleryCloudName = signed.cloud_name;
            states.forEach((state, index) => {
                state.size = prepared[index].size;
                state.loaded = 0;
            });
            updateOverallProgress(states);
            setStatus("Uploading images directly to Cloudinary…");

            const receipts = await uploadConcurrently(signed.uploads, prepared, states);
            if (cancelled) throw new Error("Upload cancelled.");
            setStatus("Verifying uploaded images securely…");
            await postBatch("finalize", {
                nonce,
                item_id: form.dataset.itemId || "",
                receipts: JSON.stringify(receipts.map((receipt) => ({
                    public_id: receipt.public_id,
                    version: receipt.version,
                    signature: receipt.signature,
                }))),
            });

            inputs.forEach((input) => {
                input.disabled = true;
            });
            cancelButton.hidden = true;
            setStatus("Images verified. Saving the gallery item…");
            HTMLFormElement.prototype.submit.call(form);
        } catch (error) {
            if (nonce) {
                await cancelBatch(nonce);
                nonceInput.value = "";
            }
            submitButton.disabled = false;
            cancelButton.hidden = true;
            busy = false;
            progressSection.hidden = true;
            setStatus(
                `${error.message || "Image upload failed."} Your selected files are still available; correct the issue or retry.`,
                true
            );
        }
    });
})();
