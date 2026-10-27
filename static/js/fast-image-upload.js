/*
 * YD Commercial Cleaning Services
 * Browser-side image optimization for employee job uploads.
 */
(function () {
    "use strict";

    const MAX_DIMENSION = 2560;
    const COMPRESS_FROM_BYTES = 900 * 1024;
    const JPEG_QUALITY = 0.82;
    const SUPPORTED_IMAGE = /\.(jpe?g|png|webp)$/i;

    function formatBytes(bytes) {
        const size = Number(bytes);
        if (!Number.isFinite(size) || size <= 0) return "0 B";
        if (size < 1024 * 1024) {
            return `${Math.round(size / 1024)} KB`;
        }
        return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    }

    function createImageElement(file) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            const objectUrl = URL.createObjectURL(file);

            image.onload = () => {
                URL.revokeObjectURL(objectUrl);
                resolve({
                    source: image,
                    width: image.naturalWidth,
                    height: image.naturalHeight,
                    close() {},
                });
            };
            image.onerror = () => {
                URL.revokeObjectURL(objectUrl);
                reject(new Error("The browser could not decode this image."));
            };
            image.src = objectUrl;
        });
    }

    async function decodeImage(file) {
        if (typeof createImageBitmap !== "function") {
            return createImageElement(file);
        }

        try {
            const bitmap = await createImageBitmap(file, {
                imageOrientation: "from-image",
            });
            return {
                source: bitmap,
                width: bitmap.width,
                height: bitmap.height,
                close: () => bitmap.close(),
            };
        } catch (_) {
            try {
                const bitmap = await createImageBitmap(file);
                return {
                    source: bitmap,
                    width: bitmap.width,
                    height: bitmap.height,
                    close: () => bitmap.close(),
                };
            } catch (_) {
                return createImageElement(file);
            }
        }
    }

    async function prepareImage(file) {
        if (
            !file ||
            file.size < COMPRESS_FROM_BYTES ||
            !SUPPORTED_IMAGE.test(file.name || "")
        ) {
            return file;
        }

        let image;
        try {
            image = await decodeImage(file);
            const scale = Math.min(
                1,
                MAX_DIMENSION / Math.max(image.width, image.height)
            );
            const width = Math.max(1, Math.round(image.width * scale));
            const height = Math.max(1, Math.round(image.height * scale));
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;

            const context = canvas.getContext("2d");
            if (!context) return file;

            context.fillStyle = "#ffffff";
            context.fillRect(0, 0, width, height);
            context.drawImage(image.source, 0, 0, width, height);

            const blob = await new Promise((resolve) => {
                canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY);
            });
            if (!blob || blob.size >= file.size) return file;

            const stem = file.name.replace(/\.[^.]+$/, "") || "photo";
            return new File([blob], `${stem}.jpg`, {
                type: "image/jpeg",
                lastModified: file.lastModified || Date.now(),
            });
        } catch (error) {
            console.warn("Image optimization skipped; using original file.", error);
            return file;
        } finally {
            if (image && typeof image.close === "function") {
                image.close();
            }
        }
    }

    async function prepareFiles(files, onProgress) {
        const prepared = [];
        for (let index = 0; index < files.length; index += 1) {
            const file = await prepareImage(files[index]);
            prepared.push(file);
            if (typeof onProgress === "function") {
                onProgress(index + 1, files.length, file);
            }
        }
        return prepared;
    }

    window.YDImageUpload = Object.freeze({
        prepareImage,
        prepareFiles,
        formatBytes,
    });
})();
