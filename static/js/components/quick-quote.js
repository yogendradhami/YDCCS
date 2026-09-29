document.addEventListener("DOMContentLoaded", function () {
	var recaptchaScriptPromise;

	function getCookie(name) {
		var cookies = document.cookie ? document.cookie.split(";") : [];
		for (var i = 0; i < cookies.length; i += 1) {
			var cookie = cookies[i].trim();
			if (cookie.indexOf(name + "=") === 0) {
				return decodeURIComponent(cookie.slice(name.length + 1));
			}
		}
		return "";
	}

	function loadRecaptcha(siteKey) {
		if (window.grecaptcha) return Promise.resolve();
		if (!recaptchaScriptPromise) {
			recaptchaScriptPromise = new Promise(function (resolve, reject) {
				var script = document.querySelector('script[src*="recaptcha/api.js"]');
				if (!script) {
					script = document.createElement("script");
					script.src = "https://www.google.com/recaptcha/api.js?render=" + encodeURIComponent(siteKey);
					script.async = true;
					script.defer = true;
					document.head.appendChild(script);
				}
				script.addEventListener("load", resolve, { once: true });
				script.addEventListener("error", reject, { once: true });
				if (window.grecaptcha) resolve();
			});
		}
		return recaptchaScriptPromise;
	}

	function getRecaptchaToken(siteKey) {
		if (!siteKey) return Promise.resolve("");
		if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
			return Promise.resolve("localhost-test-token");
		}
		return loadRecaptcha(siteKey).then(function () {
			return new Promise(function (resolve, reject) {
				window.grecaptcha.ready(function () {
					window.grecaptcha.execute(siteKey, { action: "quick_quote_submit" })
						.then(resolve)
						.catch(reject);
				});
			});
		});
	}

	document.querySelectorAll(".yd-quick-quote__form").forEach(function (form) {
		var button = form.querySelector('button[type="submit"]');
		var submitLabel = form.querySelector("[data-submit-label]");
		var feedback = form.querySelector(".yd-quick-quote__feedback");
		var defaultLabel = submitLabel ? submitLabel.textContent : "Get My Free Quote";

		function showFeedback(message, status) {
			if (!feedback) return;
			feedback.textContent = message;
			feedback.dataset.status = status;
			feedback.hidden = !message;
		}

		function showErrors(errors) {
			form.querySelectorAll("[data-error-for]").forEach(function (target) {
				target.textContent = "";
			});
			form.querySelectorAll("[aria-invalid='true']").forEach(function (field) {
				field.removeAttribute("aria-invalid");
			});

			Object.keys(errors || {}).forEach(function (name) {
				var field = form.elements.namedItem(name);
				var target = form.querySelector('[data-error-for="' + name + '"]');
				var messages = errors[name].map(function (error) {
					return error.message;
				}).join(" ");
				if (target) target.textContent = messages;
				if (field && field.setAttribute) field.setAttribute("aria-invalid", "true");
			});
		}

		form.addEventListener("input", function (event) {
			var name = event.target.name;
			var target = name && form.querySelector('[data-error-for="' + name + '"]');
			if (target) target.textContent = "";
			if (event.target.hasAttribute("aria-invalid")) {
				event.target.removeAttribute("aria-invalid");
			}
		});

		form.addEventListener("submit", async function (event) {
			if (!window.fetch || form.dataset.submitting === "true") return;
			event.preventDefault();
			form.dataset.submitting = "true";
			if (button) button.disabled = true;
			if (submitLabel) submitLabel.textContent = "Sending request...";
			showFeedback("Sending request...", "sending");
			showErrors({});

			try {
				var token = await getRecaptchaToken(form.dataset.recaptchaSiteKey || "");
				var tokenField = form.querySelector('[name="g_recaptcha_response"]');
				if (tokenField && token) tokenField.value = token;

				var response = await fetch(form.action || window.location.href, {
					method: "POST",
					body: new FormData(form),
					credentials: "same-origin",
					headers: {
						"Accept": "application/json",
						"X-Requested-With": "XMLHttpRequest",
						"X-CSRFToken": getCookie("csrftoken")
					}
				});
				var result = await response.json();
				showErrors(result.errors || {});
				showFeedback(result.message || "We couldn't complete your request right now. Please try again or contact us directly.", result.success ? "success" : "error");
				if (result.success) form.reset();
			} catch (error) {
				showFeedback("We couldn't complete your request right now. Please try again or contact us directly.", "error");
			} finally {
				form.dataset.submitting = "false";
				if (button) button.disabled = false;
				if (submitLabel) submitLabel.textContent = defaultLabel;
			}
		});
	});
});