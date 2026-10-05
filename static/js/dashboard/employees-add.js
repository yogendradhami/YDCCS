(function () {
    "use strict";

    const form = document.getElementById("employeeCreateForm");
    if (!form) return;

    const photoInput = document.getElementById("id_image");
    const photoDrop = document.getElementById("employeePhotoDrop");
    const photoImage = document.getElementById("employeePhotoImage");
    const photoPreview = document.getElementById("employeePhotoPreview");
    const photoPlaceholder = document.getElementById("employeePhotoPlaceholder");
    const photoFilename = document.getElementById("employeePhotoFilename");
    const photoError = document.getElementById("employee-photo-error");
    const removePhotoButton = document.getElementById("removeEmployeePhoto");
    const accessRadios = [...form.querySelectorAll('input[name="access_mode"]')];
    const accessPanels = [...form.querySelectorAll("[data-access-panel]")];
    const nameInput = document.getElementById("id_full_name");
    const roleInput = document.getElementById("id_role");
    const activeInput = document.getElementById("id_active");
    const loginEmailInput = document.getElementById("id_login_email");
    const usernameInput = document.getElementById("id_username");
    const existingUserSelect = document.getElementById("id_existing_user");
    const existingUserSearch = document.getElementById("employeeUserSearch");
    const saveButton = document.getElementById("saveEmployeeButton");
    let dirty = false;
    let submitting = false;
    let previewUrl = null;

    function selectedAccessMode() {
        return accessRadios.find((radio) => radio.checked)?.value || "none";
    }

    function updateAccessMode() {
        const mode = selectedAccessMode();
        accessPanels.forEach((panel) => {
            panel.hidden = panel.dataset.accessPanel !== mode;
        });

        const loginEmail = document.getElementById("id_login_email");
        const password1 = document.getElementById("id_password1");
        const password2 = document.getElementById("id_password2");
        const existingUser = document.getElementById("id_existing_user");
        if (loginEmail) loginEmail.required = mode === "create";
        if (password1) password1.required = mode === "create";
        if (password2) password2.required = mode === "create";
        if (existingUser) existingUser.required = mode === "link";

        const portal = document.getElementById("summaryPortal");
        const loginRow = document.querySelector('[data-summary-row="login"]');
        const login = document.getElementById("summaryLogin");
        if (portal) {
            const enabled = mode !== "none";
            portal.textContent = enabled ? "Enabled" : "Not enabled";
            portal.classList.toggle("is-enabled", enabled);
        }
        if (loginRow && login) {
            loginRow.hidden = mode === "none";
            if (mode === "create") {
                const email = loginEmail?.value || "";
                login.textContent = email || "Enter login email";
                login.href = email ? `mailto:${email}` : "mailto:";
            } else if (mode === "link") {
                const selected = existingUser?.selectedOptions[0];
                const email = selected?.textContent.match(/\(([^()]*)\)\s*$/)?.[1] || "";
                login.textContent = selected?.value ? (email || selected.textContent) : "Select an account";
                login.href = email ? `mailto:${email}` : "mailto:";
            } else {
                login.textContent = "Not set";
                login.href = "mailto:";
            }
        }
    }

    function displayPhoto(file) {
        photoError.textContent = "";
        if (!file) return;
        const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
        if (!allowedTypes.includes(file.type)) {
            photoInput.value = "";
            photoError.textContent = "Use a JPEG, PNG, or WebP image.";
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            photoInput.value = "";
            photoError.textContent = "Choose an image smaller than 5 MB.";
            return;
        }

        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(file);
        photoImage.src = previewUrl;
        photoPreview.hidden = false;
        photoPlaceholder.hidden = true;
        photoFilename.textContent = file.name;
        removePhotoButton.hidden = false;
    }

    if (photoInput && photoDrop) {
        photoInput.addEventListener("change", () => displayPhoto(photoInput.files[0]));
        ["dragenter", "dragover"].forEach((eventName) => {
            photoDrop.addEventListener(eventName, (event) => {
                event.preventDefault();
                photoDrop.classList.add("is-dragover");
            });
        });
        ["dragleave", "drop"].forEach((eventName) => {
            photoDrop.addEventListener(eventName, (event) => {
                event.preventDefault();
                photoDrop.classList.remove("is-dragover");
            });
        });
        photoDrop.addEventListener("drop", (event) => {
            const file = event.dataTransfer.files[0];
            if (!file) return;
            const transfer = new DataTransfer();
            transfer.items.add(file);
            photoInput.files = transfer.files;
            displayPhoto(file);
        });
        removePhotoButton.addEventListener("click", () => {
            photoInput.value = "";
            photoPreview.hidden = true;
            photoPlaceholder.hidden = false;
            photoFilename.textContent = "JPG, PNG or WebP · up to 5 MB";
            removePhotoButton.hidden = true;
            photoError.textContent = "";
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        });
    }

    accessRadios.forEach((radio) => radio.addEventListener("change", updateAccessMode));
    [nameInput, roleInput, activeInput, loginEmailInput, existingUserSelect].forEach((field) => {
        field?.addEventListener("input", updateSummary);
        field?.addEventListener("change", updateSummary);
    });

    function updateSummary() {
        const name = nameInput?.value.trim();
        const role = roleInput?.selectedOptions[0]?.textContent;
        const status = activeInput?.checked ? "Active" : "Inactive";
        const nameSummary = document.getElementById("summaryName");
        const roleSummary = document.getElementById("summaryRole");
        const statusSummary = document.getElementById("summaryStatus");
        if (nameSummary) nameSummary.textContent = name || "New employee";
        if (roleSummary) roleSummary.textContent = role || "Cleaner";
        if (statusSummary) statusSummary.textContent = status;
        updateAccessMode();
    }

    if (existingUserSearch && existingUserSelect) {
        existingUserSearch.addEventListener("input", () => {
            const query = existingUserSearch.value.trim().toLocaleLowerCase();
            [...existingUserSelect.options].forEach((option, index) => {
                if (index === 0) return;
                option.hidden = !option.textContent.toLocaleLowerCase().includes(query);
            });
        });
    }

    function securePassword(length) {
        const groups = [
            "ABCDEFGHJKLMNPQRSTUVWXYZ",
            "abcdefghijkmnopqrstuvwxyz",
            "23456789",
            "!@#$%&*+-=?",
        ];
        const all = groups.join("");
        const bytes = new Uint32Array(length);
        crypto.getRandomValues(bytes);
        const chars = groups.map((group, index) => group[bytes[index] % group.length]);
        for (let index = groups.length; index < length; index += 1) {
            chars.push(all[bytes[index] % all.length]);
        }
        for (let index = chars.length - 1; index > 0; index -= 1) {
            const swap = bytes[index] % (index + 1);
            [chars[index], chars[swap]] = [chars[swap], chars[index]];
        }
        return chars.join("");
    }

    document.getElementById("generateEmployeePassword")?.addEventListener("click", () => {
        const password = securePassword(20);
        const password1 = document.getElementById("id_password1");
        const password2 = document.getElementById("id_password2");
        password1.value = password;
        password2.value = password;
        password1.type = "text";
        password2.type = "text";
        document.querySelectorAll("[data-password-toggle]").forEach((button) => {
            button.textContent = "Hide";
            button.setAttribute("aria-pressed", "true");
        });
        password1.focus();
    });

    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.passwordToggle);
            const showing = input.type === "text";
            input.type = showing ? "password" : "text";
            button.textContent = showing ? "Show" : "Hide";
            button.setAttribute("aria-pressed", String(!showing));
            button.setAttribute("aria-label", `${showing ? "Show" : "Hide"} ${input.id === "id_password1" ? "temporary password" : "password confirmation"}`);
        });
    });

    form.addEventListener("input", () => { dirty = true; });
    form.addEventListener("change", () => { dirty = true; });
    window.addEventListener("beforeunload", (event) => {
        if (dirty && !submitting) {
            event.preventDefault();
            event.returnValue = "";
        }
    });

    form.addEventListener("submit", () => {
        submitting = true;
        if (!saveButton) return;
        saveButton.disabled = true;
        saveButton.querySelector(".employee-submit-label").hidden = true;
        saveButton.querySelector(".employee-submit-loading").hidden = false;
    });

    updateSummary();
})();