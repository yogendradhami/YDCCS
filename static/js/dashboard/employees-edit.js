(function () {
    "use strict";

    const form = document.getElementById("employeeEditForm");

    if (!form) {
        return;
    }


    const photoInput =
        document.getElementById("id_image");

    const photoDrop =
        document.getElementById("employeePhotoDrop");

    const photoImage =
        document.getElementById("employeePhotoImage");

    const photoPreview =
        document.getElementById("employeePhotoPreview");

    const photoPlaceholder =
        document.getElementById("employeePhotoPlaceholder");

    const photoFilename =
        document.getElementById("employeePhotoFilename");

    const photoError =
        document.getElementById("employee-photo-error");

    const removePhotoButton =
        document.getElementById("removeEmployeePhoto");

    const clearPhoto =
        document.getElementById("id_image-clear");

    const saveButton =
        document.getElementById("saveEmployeeButton");

    const nameInput =
        document.getElementById("id_full_name");

    const roleInput =
        document.getElementById("id_role");

    const activeInput =
        document.getElementById("id_active");


    let previewUrl = null;
    let submitting = false;


    /* ==========================================================
       PHOTO PREVIEW
    ========================================================== */

    function selectPhoto(file) {

        if (!file) {
            return;
        }


        photoError.textContent = "";


        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];


        if (!allowedTypes.includes(file.type)) {

            photoInput.value = "";

            photoError.textContent =
                "Use a JPEG, PNG, or WebP image.";

            return;
        }


        if (file.size > 5 * 1024 * 1024) {

            photoInput.value = "";

            photoError.textContent =
                "Choose an image smaller than 5 MB.";

            return;
        }


        if (clearPhoto) {
            clearPhoto.checked = false;
        }


        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }


        previewUrl =
            URL.createObjectURL(file);


        photoImage.src =
            previewUrl;


        photoPreview.hidden =
            false;


        photoPlaceholder.hidden =
            true;


        photoFilename.textContent =
            file.name;


        removePhotoButton.hidden =
            false;


        form.dataset.dirty =
            "true";
    }


    function resetPhotoSelection() {

        photoInput.value = "";


        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }


        previewUrl = null;


        photoPreview.hidden =
            true;


        photoPlaceholder.hidden =
            false;


        photoFilename.textContent =
            "JPG, PNG or WebP · up to 5 MB";


        removePhotoButton.hidden =
            true;


        photoError.textContent = "";
    }


    if (photoInput && photoDrop) {


        photoInput.addEventListener(
            "change",
            function () {

                selectPhoto(
                    photoInput.files[0]
                );

            }
        );


        [
            "dragenter",
            "dragover"
        ].forEach(function (eventName) {

            photoDrop.addEventListener(
                eventName,
                function (event) {

                    event.preventDefault();

                    photoDrop.classList.add(
                        "is-dragover"
                    );

                }
            );

        });


        [
            "dragleave",
            "drop"
        ].forEach(function (eventName) {

            photoDrop.addEventListener(
                eventName,
                function (event) {

                    event.preventDefault();

                    photoDrop.classList.remove(
                        "is-dragover"
                    );

                }
            );

        });


        photoDrop.addEventListener(
            "drop",
            function (event) {

                const file =
                    event.dataTransfer.files[0];


                if (!file) {
                    return;
                }


                const transfer =
                    new DataTransfer();


                transfer.items.add(file);


                photoInput.files =
                    transfer.files;


                selectPhoto(file);

            }
        );


        if (removePhotoButton) {

            removePhotoButton.addEventListener(
                "click",
                resetPhotoSelection
            );

        }

    }


    /* ==========================================================
       REMOVE CURRENT PHOTO
    ========================================================== */

    if (clearPhoto) {

        clearPhoto.addEventListener(
            "change",
            function () {

                if (!clearPhoto.checked) {
                    return;
                }


                resetPhotoSelection();


                photoFilename.textContent =
                    "Current photo will be removed when you save.";

            }
        );

    }


    /* ==========================================================
       LIVE SUMMARY
    ========================================================== */

    function updateSummary() {

        const name =
            nameInput?.value.trim() ||
            "Employee";


        const role =
            roleInput
                ?.selectedOptions[0]
                ?.textContent ||
            "Cleaner";


        const status =
            activeInput?.checked
                ? "Active"
                : "Inactive";


        const nameSummary =
            document.getElementById(
                "summaryName"
            );


        const duplicateNameSummary =
            document.getElementById(
                "summaryNameDuplicate"
            );


        const roleSummary =
            document.getElementById(
                "summaryRole"
            );


        const statusSummary =
            document.getElementById(
                "summaryStatus"
            );


        if (nameSummary) {
            nameSummary.textContent =
                name;
        }


        if (duplicateNameSummary) {
            duplicateNameSummary.textContent =
                name;
        }


        if (roleSummary) {
            roleSummary.textContent =
                role;
        }


        if (statusSummary) {

            statusSummary.textContent =
                status;

            statusSummary.classList.toggle(
                "is-enabled",
                status === "Active"
            );

        }

    }


    [
        nameInput,
        roleInput,
        activeInput
    ].forEach(function (field) {

        if (!field) {
            return;
        }


        field.addEventListener(
            "input",
            updateSummary
        );


        field.addEventListener(
            "change",
            updateSummary
        );

    });


    /* ==========================================================
       DIRTY FORM
    ========================================================== */

    form.addEventListener(
        "input",
        function () {

            form.dataset.dirty =
                "true";

        }
    );


    form.addEventListener(
        "change",
        function () {

            form.dataset.dirty =
                "true";

        }
    );


    window.addEventListener(
        "beforeunload",
        function (event) {

            if (
                !submitting &&
                form.dataset.dirty === "true"
            ) {

                event.preventDefault();

                event.returnValue = "";

            }

        }
    );


    /* ==========================================================
       SAVE STATE
    ========================================================== */

    form.addEventListener(
        "submit",
        function () {

            submitting = true;


            if (!saveButton) {
                return;
            }


            saveButton.disabled =
                true;


            const label =
                saveButton.querySelector(
                    ".employee-submit-label"
                );


            const loading =
                saveButton.querySelector(
                    ".employee-submit-loading"
                );


            if (label) {
                label.hidden = true;
            }


            if (loading) {
                loading.hidden = false;
            }

        }
    );


    /* ==========================================================
       INITIALISE
    ========================================================== */

    updateSummary();

})();