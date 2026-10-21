(function () {
    "use strict";

    const excludedPrefixes = [
        "/admin/",
        "/api/",
        "/dashboard/",
        "/employee/",
        "/security/",
    ];
    const path = window.location.pathname;
    if (excludedPrefixes.some((prefix) => path.startsWith(prefix))) return;
    if (path.startsWith("/portal/") && path !== "/portal/profile/") return;

    const sendCodeUrl = "/security/email/send-code/";
    const verifyCodeUrl = "/security/email/verify-code/";
    let activeForm = null;
    let activeEmails = [];
    let activeEmailIndex = 0;
    let activeEmail = "";
    let activeSubmitter = null;
    let modal = null;

    function csrfToken(form) {
        const field = form && form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (field) return field.value;
        const cookie = document.cookie.split(";").map((item) => item.trim());
        const csrf = cookie.find((item) => item.startsWith("csrftoken="));
        return csrf ? decodeURIComponent(csrf.slice("csrftoken=".length)) : "";
    }

    function getEmails(form) {
        const valuesByName = new Map();
        for (const [name, rawValue] of new FormData(form).entries()) {
            if (name.toLowerCase().includes("email") && typeof rawValue === "string") {
                valuesByName.set(name, rawValue.trim().toLowerCase());
            }
        }
        const verifiedEmail = (form.dataset.verifiedEmail || "").trim().toLowerCase();
        return Array.from(new Set(
            Array.from(valuesByName.values()).filter(
                (email) => email && email !== verifiedEmail
            )
        ));
    }

    function showActiveEmail(message) {
        activeEmail = activeEmails[activeEmailIndex];
        const dialog = getModal();
        dialog.querySelector("#emailVerificationCode").value = "";
        dialog.querySelector("#emailVerificationError").textContent = "";
        dialog.querySelector("#emailVerificationMessage").textContent =
            message || "Send a one-time code to " + activeEmail + " and enter it to continue.";
        dialog.style.display = "flex";
    }

    function getModal() {
        if (modal) return modal;
        modal = document.createElement("div");
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-modal", "true");
        modal.setAttribute("aria-labelledby", "emailVerificationTitle");
        modal.style.cssText = [
            "position:fixed",
            "inset:0",
            "z-index:99999",
            "display:none",
            "align-items:center",
            "justify-content:center",
            "padding:20px",
            "background:rgba(15,23,42,.65)",
        ].join(";");
        modal.innerHTML = `
            <div style="width:min(100%,440px);padding:26px;border-radius:16px;background:#fff;box-shadow:0 24px 70px rgba(15,23,42,.25);font:15px/1.5 system-ui,sans-serif;color:#0f172a">
                <h2 id="emailVerificationTitle" style="margin:0 0 8px;font-size:22px">Verify your email</h2>
                <p id="emailVerificationMessage" style="margin:0 0 18px;color:#475569">We’ll send a one-time code to confirm you can receive email at this address.</p>
                <label for="emailVerificationCode" style="display:block;margin-bottom:6px;font-weight:700">Six-digit code</label>
                <input id="emailVerificationCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6" style="box-sizing:border-box;width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:9px;font:inherit">
                <p id="emailVerificationError" aria-live="polite" style="min-height:22px;margin:8px 0;color:#b91c1c"></p>
                <div style="display:flex;gap:10px;flex-wrap:wrap">
                    <button id="emailVerificationSend" type="button" style="padding:11px 14px;border:0;border-radius:9px;background:#e2e8f0;color:#0f172a;font-weight:700;cursor:pointer">Send code</button>
                    <button id="emailVerificationConfirm" type="button" style="padding:11px 14px;border:0;border-radius:9px;background:#0f766e;color:#fff;font-weight:700;cursor:pointer">Verify and submit</button>
                    <button id="emailVerificationCancel" type="button" style="padding:11px 14px;border:1px solid #cbd5e1;border-radius:9px;background:#fff;color:#334155;font-weight:700;cursor:pointer">Cancel</button>
                </div>
            </div>`;
        document.body.appendChild(modal);

        const sendButton = modal.querySelector("#emailVerificationSend");
        const verifyButton = modal.querySelector("#emailVerificationConfirm");
        const cancelButton = modal.querySelector("#emailVerificationCancel");
        const codeInput = modal.querySelector("#emailVerificationCode");
        const error = modal.querySelector("#emailVerificationError");
        const message = modal.querySelector("#emailVerificationMessage");

        async function post(url, data) {
            const response = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken(activeForm),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify(data),
            });
            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.message || "Verification request failed.");
            }
            return payload;
        }

        sendButton.addEventListener("click", async function () {
            error.textContent = "";
            sendButton.disabled = true;
            try {
                const result = await post(sendCodeUrl, {email: activeEmail});
                message.textContent = result.message;
                codeInput.focus();
            } catch (exception) {
                error.textContent = exception.message;
            } finally {
                sendButton.disabled = false;
            }
        });

        verifyButton.addEventListener("click", async function () {
            error.textContent = "";
            verifyButton.disabled = true;
            try {
                await post(verifyCodeUrl, {
                    email: activeEmail,
                    code: codeInput.value.trim(),
                });
                if (activeEmailIndex + 1 < activeEmails.length) {
                    activeEmailIndex += 1;
                    activeEmail = activeEmails[activeEmailIndex];
                    codeInput.value = "";
                    message.textContent = "Email verified. Sending a code to " + activeEmail + ".";
                    const result = await post(sendCodeUrl, {email: activeEmail});
                    message.textContent = result.message + " Address " + (activeEmailIndex + 1) + " of " + activeEmails.length + ".";
                    codeInput.focus();
                    return;
                }
                activeForm.dataset.verifiedPublicEmails = JSON.stringify(activeEmails);
                const form = activeForm;
                const submitter = activeSubmitter;
                modal.style.display = "none";
                if (form.isConnected) {
                    if (submitter && submitter.form === form) form.requestSubmit(submitter);
                    else form.requestSubmit();
                }
            } catch (exception) {
                error.textContent = exception.message;
            } finally {
                verifyButton.disabled = false;
            }
        });

        cancelButton.addEventListener("click", function () {
            modal.style.display = "none";
            activeForm = null;
            activeEmails = [];
        });
        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                modal.style.display = "none";
                activeForm = null;
                activeEmails = [];
            }
        });
        return modal;
    }

    document.addEventListener(
        "submit",
        function (event) {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) return;

            const emails = getEmails(form);
            if (emails.length) {
                try {
                    const fallbackVerified = JSON.parse(
                        sessionStorage.getItem("ydVerifiedPublicEmails") || "[]"
                    );
                    if (JSON.stringify(fallbackVerified) === JSON.stringify(emails)) {
                        form.dataset.verifiedPublicEmails = JSON.stringify(emails);
                        sessionStorage.removeItem("ydVerifiedPublicEmails");
                    }
                } catch (error) {
                    sessionStorage.removeItem("ydVerifiedPublicEmails");
                }
            }
            if (!emails.length || form.dataset.verifiedPublicEmails === JSON.stringify(emails)) return;

            event.preventDefault();
            event.stopImmediatePropagation();
            activeForm = form;
            activeEmails = emails;
            activeEmailIndex = 0;
            activeEmail = activeEmails[0];
            activeSubmitter = event.submitter || null;
            showActiveEmail();
            getModal().querySelector("#emailVerificationSend").click();
        },
        true
    );
})();
