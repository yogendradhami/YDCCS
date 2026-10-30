(() => {
    const conversations = document.querySelectorAll("[data-live-conversation]");

    conversations.forEach((conversation) => {
        const side = conversation.dataset.side;
        const endpoint = conversation.dataset.conversationUrl;
        const card = conversation.closest(
            side === "dashboard"
                ? ".damage-report-card"
                : ".damage-report-history-card",
        );
        const form = card?.querySelector(
            side === "dashboard"
                ? ".damage-report-reply-form"
                : ".employee-damage-report-reply-form",
        );
        const textarea = form?.querySelector("textarea");
        const feedback = form?.querySelector("[data-chat-feedback]");
        const presence = conversation.querySelector(
            "[data-conversation-presence]",
        );
        const knownReplies = new Set(
            Array.from(conversation.querySelectorAll("[data-reply-id]"))
                .map((reply) => reply.dataset.replyId),
        );
        const csrfToken = form?.querySelector(
            'input[name="csrfmiddlewaretoken"]',
        )?.value;
        let typingTimeout;
        let lastTypingState = false;
        let pollTimer;
        let isSending = false;
        let isInView = false;

        const setFeedback = (message, isError = false) => {
            if (!feedback) return;
            feedback.textContent = message;
            feedback.classList.toggle("is-error", isError);
        };

        const createReply = (reply) => {
            const article = document.createElement("article");
            const roleClass = `is-${reply.role}`;
            article.className = side === "dashboard"
                ? `damage-report-reply ${roleClass}`
                : roleClass;
            article.dataset.replyId = String(reply.id);

            const meta = document.createElement("div");
            meta.className = side === "dashboard"
                ? "damage-reply-meta"
                : "employee-damage-reply-meta";
            const author = document.createElement("strong");
            author.textContent = reply.author_name;
            const role = document.createElement("span");
            role.textContent = reply.role_label;
            const time = document.createElement("time");
            time.dateTime = reply.timestamp_iso;
            time.textContent = reply.timestamp;
            meta.append(author, role, time);

            const message = document.createElement("p");
            message.textContent = reply.message;
            article.append(meta, message);
            return article;
        };

        const updatePresence = (activeUsers) => {
            if (!presence) return;
            if (!activeUsers.length) {
                presence.textContent = "Waiting for the other person to join the conversation.";
                presence.classList.remove("is-active", "is-typing");
                return;
            }
            const writers = activeUsers
                .filter((user) => user.is_typing)
                .map((user) => user.name);
            const attendees = activeUsers
                .filter((user) => !user.is_typing)
                .map((user) => user.name);
            const messages = [];
            if (writers.length) {
                messages.push(
                    `${writers.join(", ")} ${writers.length === 1 ? "is" : "are"} writing…`,
                );
            }
            if (attendees.length) {
                messages.push(
                    `${attendees.join(", ")} ${attendees.length === 1 ? "is" : "are"} attending this report.`,
                );
            }
            presence.textContent = messages.join(" ");
            presence.classList.toggle("is-active", true);
            presence.classList.toggle("is-typing", writers.length > 0);
        };

        const updateStatus = (data) => {
            const isClosed = data.status === "closed";
            const resolution = card?.querySelector(
                ".damage-case-resolution, .employee-damage-case-resolution",
            );
            if (resolution) resolution.hidden = !isClosed;
            const badge = card?.querySelector(
                ".damage-case-status, .employee-damage-case-status",
            );
            if (badge) {
                badge.classList.toggle("is-closed", isClosed);
                badge.classList.toggle("is-open", !isClosed);
                const indicator = badge.querySelector("i");
                badge.textContent = data.status_label;
                if (indicator) badge.prepend(indicator);
            }
            const statusButton = card?.querySelector(
                ".damage-ticket-close, .damage-ticket-reopen",
            );
            if (statusButton) {
                statusButton.textContent = isClosed
                    ? "Reopen ticket"
                    : "Mark resolved & close ticket";
                statusButton.classList.toggle("damage-ticket-close", !isClosed);
                statusButton.classList.toggle("damage-ticket-reopen", isClosed);
                const explanation = statusButton
                    .closest(".damage-ticket-status-form")
                    ?.querySelector("p");
                if (explanation) {
                    explanation.textContent = isClosed
                        ? "Need to continue the investigation? Reopen this ticket to return it to the active queue."
                        : "Mark this ticket resolved when the issue has been addressed. The employee will see the closed status in their portal.";
                }
            }
        };

        const poll = async (force = false) => {
            window.clearTimeout(pollTimer);
            if (
                force
                || (
                    document.visibilityState === "visible"
                    && isInView
                )
            ) {
                try {
                    const response = await fetch(endpoint, {
                        credentials: "same-origin",
                        headers: { Accept: "application/json" },
                        cache: "no-store",
                    });
                    if (!response.ok) {
                        throw new Error(`Conversation request failed (${response.status}).`);
                    }
                    const data = await response.json();
                    const empty = conversation.querySelector(
                        ".damage-conversation-empty, .damage-report-history-replies > p",
                    );
                    data.replies.forEach((reply) => {
                        const replyId = String(reply.id);
                        if (knownReplies.has(replyId)) return;
                        empty?.remove();
                        conversation.append(createReply(reply));
                        knownReplies.add(replyId);
                    });
                    const count = conversation.querySelector("[data-message-count]");
                    if (count) {
                        const total = knownReplies.size;
                        count.textContent = `${total} update${total === 1 ? "" : "s"}`;
                    }
                    updatePresence(data.presence);
                    updateStatus(data);
                    if (data.replies.length) {
                        conversation.scrollTop = conversation.scrollHeight;
                    }
                    if (feedback?.classList.contains("is-error")) {
                        setFeedback("");
                    }
                } catch (error) {
                    setFeedback("Live updates are reconnecting. Your messages remain saved.", true);
                    console.error("Damage report conversation update failed.", error);
                }
            }
            if (
                document.visibilityState === "visible"
                && isInView
            ) {
                pollTimer = window.setTimeout(poll, 3000);
            }
        };

        const sendTypingState = async (isTyping) => {
            if (!csrfToken || lastTypingState === isTyping) return;
            lastTypingState = isTyping;
            const body = new URLSearchParams({ is_typing: String(isTyping) });
            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-CSRFToken": csrfToken,
                    },
                    body,
                });
                if (!response.ok) {
                    throw new Error(`Presence update failed (${response.status}).`);
                }
            } catch (error) {
                console.error("Damage report typing indicator update failed.", error);
            }
        };

        if (textarea) {
            textarea.addEventListener("input", () => {
                if (textarea.value.trim()) {
                    sendTypingState(true);
                    window.clearTimeout(typingTimeout);
                    typingTimeout = window.setTimeout(
                        () => sendTypingState(false),
                        1400,
                    );
                } else {
                    window.clearTimeout(typingTimeout);
                    sendTypingState(false);
                }
            });
            textarea.addEventListener("blur", () => {
                window.clearTimeout(typingTimeout);
                sendTypingState(false);
            });
        }

        form?.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (isSending || !textarea?.value.trim()) return;
            isSending = true;
            const button = form.querySelector('button[type="submit"]');
            if (button) button.disabled = true;
            setFeedback("Sending…");
            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new FormData(form),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Your message could not be sent.");
                }
                textarea.value = "";
                window.clearTimeout(typingTimeout);
                await sendTypingState(false);
                setFeedback("Message sent.");
                await poll(true);
            } catch (error) {
                setFeedback(error.message || "Your message could not be sent.", true);
            } finally {
                isSending = false;
                if (button) button.disabled = false;
            }
        });

        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                window.clearTimeout(pollTimer);
                poll();
            }
        });
        if ("IntersectionObserver" in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.target !== conversation) return;
                    isInView = entry.isIntersecting;
                    if (isInView && document.visibilityState === "visible") {
                        poll();
                    } else {
                        window.clearTimeout(pollTimer);
                    }
                });
            }, { threshold: 0.1 });
            observer.observe(conversation);
        } else {
            isInView = true;
        }
        poll();
    });
})();
