document.addEventListener("DOMContentLoaded", () => {
    /*
     * ==========================================================
     * RELATED RECORD SWITCHER
     * ==========================================================
     */

    const relatedType = document.querySelector(
        '[data-related-type="true"]'
    );

    const relatedFields = document.querySelectorAll(
        "[data-related-field]"
    );


    function updateRelatedFields() {
        if (!relatedType) {
            return;
        }

        const selectedValue = relatedType.value;


        relatedFields.forEach((wrapper) => {
            const fieldName = wrapper.dataset.relatedField;

            if (fieldName === selectedValue) {
                wrapper.hidden = false;
                wrapper.classList.add("is-visible");
            } else {
                wrapper.hidden = true;
                wrapper.classList.remove("is-visible");

                const select = wrapper.querySelector("select");

                if (select) {
                    select.value = "";
                }
            }
        });
    }


    if (relatedType) {
        relatedType.addEventListener(
            "change",
            updateRelatedFields
        );

        updateRelatedFields();
    }


    /*
     * ==========================================================
     * FILE NAME PREVIEW
     * ==========================================================
     */

    const fileInput = document.querySelector(
        ".cd-form-file"
    );

    const uploadZone = document.querySelector(
        ".cd-upload-zone"
    );

    if (fileInput && uploadZone) {

        fileInput.addEventListener(
            "change",
            () => {

                const file =
                    fileInput.files &&
                    fileInput.files[0];

                if (!file) {
                    return;
                }

                const strong =
                    uploadZone.querySelector(
                        "strong"
                    );

                const span =
                    uploadZone.querySelector(
                        "span"
                    );

                if (strong) {
                    strong.textContent =
                        file.name;
                }

                if (span) {

                    const sizeMB =
                        file.size /
                        (1024 * 1024);

                    span.textContent =
                        `${sizeMB.toFixed(2)} MB selected`;
                }
            }
        );
    }


    /*
     * ==========================================================
     * CONFIRMATION FOR DANGEROUS ACTIONS
     * ==========================================================
     */

    const confirmForms = document.querySelectorAll(
        "form[data-confirm]"
    );


    confirmForms.forEach((form) => {

        form.addEventListener(
            "submit",
            (event) => {

                const message =
                    form.dataset.confirm;

                if (!message) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        message
                    );

                if (!confirmed) {
                    event.preventDefault();
                }
            }
        );
    });


    /*
     * ==========================================================
     * DRAG & DROP
     * ==========================================================
     */

    if (uploadZone && fileInput) {

        [
            "dragenter",
            "dragover",
        ].forEach((eventName) => {

            uploadZone.addEventListener(
                eventName,
                (event) => {

                    event.preventDefault();

                    uploadZone.classList.add(
                        "is-dragging"
                    );
                }
            );
        });


        [
            "dragleave",
            "drop",
        ].forEach((eventName) => {

            uploadZone.addEventListener(
                eventName,
                (event) => {

                    event.preventDefault();

                    uploadZone.classList.remove(
                        "is-dragging"
                    );
                }
            );
        });


        uploadZone.addEventListener(
            "drop",
            (event) => {

                const files =
                    event.dataTransfer.files;

                if (!files || !files.length) {
                    return;
                }

                try {
                    fileInput.files = files;

                    fileInput.dispatchEvent(
                        new Event(
                            "change",
                            {
                                bubbles: true,
                            }
                        )
                    );

                } catch (error) {
                    console.warn(
                        "Unable to assign dropped file.",
                        error
                    );
                }
            }
        );
    }
});