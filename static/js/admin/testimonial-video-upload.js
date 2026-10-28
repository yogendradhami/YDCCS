(function () {
    "use strict";

    const form = document.getElementById("testimonialvideo_form") ||
        document.querySelector("#content form");
    const fileInput = document.getElementById("id_video");
    const nonceInput = document.getElementById("id_video_upload_nonce");
    const progress = document.getElementById("testimonial-video-progress");
    const status = document.getElementById("testimonial-video-status");
    const retryButton = document.getElementById("testimonial-video-retry");
    const cancelButton = document.getElementById("testimonial-video-cancel");
    const preview = document.getElementById("testimonial-video-preview");
    if (!form || !fileInput || !nonceInput || !progress || !status || !retryButton || !cancelButton || !preview) return;

    const MAX_FILE_BYTES = 100 * 1024 * 1024;
    const ALLOWED_VIDEO = /\.(mp4|mov|m4v|webm|avi|mkv|mpeg|mpg|ogv|3gp)$/i;
    const CHUNK_THRESHOLD = 20 * 1024 * 1024;
    const uploadUrl = nonceInput.dataset.uploadUrl;
    const cloudName = nonceInput.dataset.cloudName;
    const itemId = nonceInput.dataset.itemId || "";
    let activeRequest = null;
    let activeFetch = null;
    let uploading = false;
    let cancelling = false;
    let saving = false;
    let retryFile = null;
    let previewUrl = null;

    function setStatus(message, isError) {
        status.textContent = message;
        status.classList.toggle("errornote", Boolean(isError));
        status.classList.toggle("success", !isError && Boolean(message));
    }

    function csrfToken() {
        const input = form.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function formatBytes(bytes) {
        if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function renderPreview(file, staged = false) {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = null;
        preview.replaceChildren();
        if (file) {
            const video = document.createElement("video");
            previewUrl = URL.createObjectURL(file);
            video.className = "media-preview-video";
            video.src = previewUrl;
            video.controls = true;
            video.preload = "metadata";
            video.setAttribute("aria-label", `Preview of ${file.name}`);
            preview.appendChild(video);
        } else if (staged) {
            const label = document.createElement("span");
            label.textContent = "Verified video staged";
            preview.appendChild(label);
        }
        if (file || staged) {
            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "media-preview-remove";
            removeButton.textContent = "×";
            removeButton.setAttribute("aria-label", "Remove selected video");
            removeButton.addEventListener("click", removeVideoSelection);
            preview.appendChild(removeButton);
            preview.hidden = false;
        } else {
            preview.hidden = true;
        }
    }

    async function postAction(action, values, controller) {
        const body = new URLSearchParams({
            csrfmiddlewaretoken: csrfToken(),
            action,
            item_id: itemId,
            ...values,
        });
        const response = await fetch(uploadUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
            body,
            signal: controller ? controller.signal : undefined,
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "The video upload request failed.");
        return payload;
    }

    function sendChunk(file, upload, start, end, uniqueUploadId, useChunks) {
        return new Promise((resolve, reject) => {
            const request = new XMLHttpRequest();
            activeRequest = request;
            request.open(
                "POST",
                `https://api.cloudinary.com/v1_1/${encodeURIComponent(cloudName)}/video/upload`
            );
            if (useChunks) {
                request.setRequestHeader("Content-Range", `bytes ${start}-${end - 1}/${file.size}`);
                request.setRequestHeader("X-Unique-Upload-Id", uniqueUploadId);
            }
            request.upload.onprogress = (event) => {
                if (!event.lengthComputable) return;
                const loaded = Math.min(end - start, event.loaded);
                const percentage = Math.floor(((start + loaded) / file.size) * 100);
                progress.value = percentage;
                setStatus(`Uploading ${file.name} - ${formatBytes(start + loaded)} of ${formatBytes(file.size)} - ${percentage}%`);
            };
            request.onload = () => {
                activeRequest = null;
                let result;
                try {
                    result = JSON.parse(request.responseText);
                } catch (_error) {
                    reject(new Error("Cloudinary returned an unreadable response."));
                    return;
                }
                if (request.status < 200 || request.status >= 300) {
                    const error = new Error(
                        result.error && result.error.message
                            ? result.error.message
                            : "Cloudinary could not upload this video."
                    );
                    error.retryable = request.status === 408 || request.status === 429 || request.status >= 500;
                    reject(error);
                    return;
                }
                resolve(result);
            };
            request.onerror = () => {
                activeRequest = null;
                const error = new Error("Network interruption while uploading to Cloudinary.");
                error.retryable = true;
                reject(error);
            };
            request.onabort = () => {
                activeRequest = null;
                reject(new Error("Video upload cancelled."));
            };

            const body = new FormData();
            const chunk = useChunks ? file.slice(start, end) : file;
            body.append("file", chunk, file.name);
            body.append("public_id", upload.public_id);
            body.append("timestamp", String(upload.timestamp));
            body.append("allowed_formats", upload.allowed_formats);
            body.append("api_key", upload.api_key);
            body.append("signature", upload.signature);
            body.append("overwrite", upload.overwrite);
            request.send(body);
        });
    }

    async function sendChunkWithRetry(file, upload, start, end, uploadId, useChunks) {
        for (let attempt = 0; attempt < 3; attempt += 1) {
            if (cancelling) throw new Error("Video upload cancelled.");
            try {
                return await sendChunk(file, upload, start, end, uploadId, useChunks);
            } catch (error) {
                if (!error.retryable || cancelling || attempt === 2) throw error;
                await new Promise((resolve) => window.setTimeout(resolve, 600 * (attempt + 1)));
            }
        }
        throw new Error("Cloudinary could not complete this video upload.");
    }

    async function uploadVideo(file, upload, chunkSize) {
        const useChunks = file.size > CHUNK_THRESHOLD;
        const uploadId = window.crypto && window.crypto.randomUUID
            ? window.crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const step = useChunks ? chunkSize : file.size;
        let receipt;
        for (let start = 0; start < file.size; start += step) {
            if (cancelling) throw new Error("Video upload cancelled.");
            const end = Math.min(file.size, start + step);
            receipt = await sendChunkWithRetry(file, upload, start, end, uploadId, useChunks);
        }
        return receipt;
    }

    async function cancelUpload() {
        cancelling = true;
        if (activeRequest) activeRequest.abort();
        if (activeFetch) activeFetch.abort();
        cancelButton.disabled = true;
        setStatus("Cancelling and cleaning up the staged video...");

        const nonce = nonceInput.value;
        if (nonce) {
            try {
                await postAction("cancel", { nonce });
                nonceInput.value = "";
                fileInput.disabled = false;
                setStatus("Upload cancelled. You can choose another video.");
            } catch (_error) {
                setStatus("Cancellation could not be confirmed. Retry cancellation before starting another upload.", true);
                cancelButton.disabled = false;
                cancelling = false;
                return;
            }
        } else {
            setStatus("Upload cancelled.");
        }
        progress.hidden = true;
        retryButton.hidden = true;
        cancelButton.hidden = true;
        uploading = false;
    }

    async function removeVideoSelection() {
        if (uploading || nonceInput.value) {
            await cancelUpload();
            if (nonceInput.value) return;
        }
        fileInput.value = "";
        fileInput.disabled = false;
        retryFile = null;
        progress.hidden = true;
        retryButton.hidden = true;
        cancelButton.hidden = true;
        cancelButton.disabled = false;
        renderPreview(null);
        setStatus("Video removed. You can choose another video.");
    }

    async function startUpload(file) {
        if (!ALLOWED_VIDEO.test(file.name)) {
            setStatus("Choose a supported video file: MP4, MOV, M4V, WebM, AVI, MKV, MPEG, MPG, OGV or 3GP.", true);
            return;
        }
        if (!file.size || file.size > MAX_FILE_BYTES) {
            setStatus("Testimonial videos must be 100 MB or smaller.", true);
            return;
        }

        retryFile = file;
        renderPreview(file);
        uploading = true;
        cancelling = false;
        retryButton.hidden = true;
        progress.hidden = false;
        progress.value = 0;
        cancelButton.hidden = false;
        cancelButton.disabled = false;
        setStatus(`Preparing ${file.name} (${formatBytes(file.size)}) for direct upload...`);

        let nonce = "";
        try {
            activeFetch = new AbortController();
            const signed = await postAction("sign", {}, activeFetch);
            activeFetch = null;
            nonce = signed.nonce;
            nonceInput.value = nonce;
            if (cancelling) {
                await postAction("cancel", { nonce });
                nonceInput.value = "";
                fileInput.disabled = false;
                progress.hidden = true;
                cancelButton.hidden = true;
                cancelButton.disabled = false;
                uploading = false;
                setStatus("Upload cancelled.");
                return;
            }

            const receipt = await uploadVideo(
                file,
                signed.upload,
                signed.chunk_size
            );
            if (cancelling) throw new Error("Video upload cancelled.");
            setStatus("Verifying the uploaded video with Cloudinary...");
            await postAction("finalize", {
                nonce,
                receipt: JSON.stringify({
                    public_id: receipt.public_id,
                    version: receipt.version,
                    signature: receipt.signature,
                }),
            });
            fileInput.value = "";
            fileInput.disabled = true;
            progress.value = 100;
            setStatus(`${file.name} (${formatBytes(file.size)}) uploaded and verified. Save this form to attach it.`);
            retryFile = null;
            retryButton.hidden = true;
            cancelButton.textContent = "Cancel staged video";
            cancelButton.disabled = false;
            uploading = false;
        } catch (error) {
            if (nonce) {
                try {
                    await postAction("cancel", { nonce });
                    nonceInput.value = "";
                } catch (_cleanupError) {
                    setStatus("Upload failed and cleanup could not be confirmed. Retry cancellation before uploading again.", true);
                }
            }
            fileInput.disabled = false;
            progress.hidden = true;
            cancelButton.hidden = !nonceInput.value;
            cancelButton.textContent = "Retry cancellation";
            retryButton.hidden = Boolean(nonceInput.value) || cancelling;
            uploading = false;
            if (!cancelling) {
                setStatus(`${error.message || "Video upload failed."} The selected file is still available; retry when ready.`, true);
            }
        } finally {
            activeFetch = null;
            activeRequest = null;
        }
    }

    fileInput.accept = "video/mp4,video/quicktime,video/webm,video/x-m4v,video/x-msvideo,video/x-matroska,video/mpeg,video/ogg,.3gp";
    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        if (nonceInput.value) {
            setStatus("Cancel the currently staged video before choosing a replacement.", true);
            return;
        }
        startUpload(file);
    });

    cancelButton.addEventListener("click", cancelUpload);
    retryButton.addEventListener("click", () => {
        if (retryFile && !nonceInput.value) startUpload(retryFile);
    });
    form.addEventListener("submit", (event) => {
        if (uploading || cancelling) {
            event.preventDefault();
            setStatus("Wait for the upload to finish or cancel it before saving.", true);
            return;
        }
        if (saving) {
            event.preventDefault();
            return;
        }
        saving = true;
        form.querySelectorAll('input[type="submit"], button[type="submit"]').forEach((button) => {
            button.disabled = true;
        });
    });

    if (nonceInput.value) {
        fileInput.disabled = true;
        renderPreview(null, true);
        progress.hidden = false;
        progress.value = 100;
        cancelButton.hidden = false;
        cancelButton.textContent = "Cancel staged video";
        retryButton.hidden = true;
        setStatus("A verified video is staged. Save this form to attach it, or cancel it before choosing a replacement.");
    }
})();
