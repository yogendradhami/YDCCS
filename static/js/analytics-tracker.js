(function () {


"use strict";

const TRACK_URL = "/analytics/track/";
const SEARCH_URL = "/analytics/track/search/";

/*
 * Do not track internal/admin/analytics pages.
 */
const EXCLUDED_PATHS = [
    "/analytics/",
    "/admin/"
];

function shouldTrack() {
    const path = window.location.pathname;

    return !EXCLUDED_PATHS.some(function (excludedPath) {
        return path.startsWith(excludedPath);
    });
}

if (!shouldTrack()) {
    return;
}

function getPageUrl() {
    return window.location.pathname + window.location.search;
}

function cleanText(value, maxLength) {
    return String(value || "")
        .trim()
        .replace(/\s+/g, " ")
        .substring(0, maxLength || 200);
}

function sendEvent(eventType, element, metadata) {

    const payload = {
        event_type: eventType,
        page_url: getPageUrl(),
        element: cleanText(element, 500),
        metadata: metadata || {}
    };

    fetch(TRACK_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
        keepalive: true
    }).catch(function () {
        // Analytics must never break the website.
    });
}

/*
 * =========================================================
 * SEARCH TRACKING
 * =========================================================
 */

function sendSearch(query) {

    query = cleanText(query, 500);

    if (!query) {
        return;
    }

    fetch(SEARCH_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "same-origin",
        body: JSON.stringify({
            query: query,
            page_url: getPageUrl()
        }),
        keepalive: true
    }).catch(function () {
        // Analytics must never interrupt normal search.
    });
}

/*
 * Find a search input anywhere on the page.
 */
function getSearchInput(container) {

    if (!container || !container.querySelector) {
        return null;
    }

    return container.querySelector(
        'input[type="search"], ' +
        'input[name="q"], ' +
        'input[name="query"], ' +
        'input[name="search"], ' +
        'input[id*="search" i], ' +
        'input[class*="search" i]'
    );
}

/*
 * Track search forms.
 *
 * This works with normal HTML forms and also catches
 * search forms that do not have a specific form ID/name.
 */
function trackSearchForms() {

    document.addEventListener("submit", function (event) {

        const form = event.target;

        if (!form || form.tagName !== "FORM") {
            return;
        }

        const searchInput = getSearchInput(form);

        if (!searchInput) {
            return;
        }

        const query = searchInput.value;

        if (query) {
            sendSearch(query);
        }
    });

    /*
     * Also detect search buttons that may be handled
     * by JavaScript instead of normal form submission.
     */
    document.addEventListener("click", function (event) {

        const target = event.target.closest(
            'button, input[type="submit"], [type="submit"], ' +
            '[data-search], [data-search-submit], ' +
            '.search-button, .search-submit'
        );

        if (!target) {
            return;
        }

        const container =
            target.closest("form") ||
            target.closest(
                ".search, .search-box, .search-container, " +
                ".site-search, .header-search, .search-wrapper"
            ) ||
            target.parentElement;

        const searchInput = getSearchInput(container);

        if (!searchInput) {
            return;
        }

        const query = searchInput.value;

        if (query) {
            sendSearch(query);
        }
    });

    /*
     * Support search fields using Enter even when the
     * surrounding implementation prevents normal submit.
     */
    document.addEventListener("keydown", function (event) {

        if (event.key !== "Enter") {
            return;
        }

        const input = event.target;

        if (!input || !input.matches) {
            return;
        }

        if (
            !input.matches(
                'input[type="search"], ' +
                'input[name="q"], ' +
                'input[name="query"], ' +
                'input[name="search"], ' +
                'input[id*="search" i], ' +
                'input[class*="search" i]'
            )
        ) {
            return;
        }

        const query = input.value;

        if (query) {
            sendSearch(query);
        }
    });
}

/*
 * =========================================================
 * PAGE VIEW
 * =========================================================
 */

function trackPageView() {

    sendEvent("PAGE_VIEW", "", {
        title: document.title.substring(0, 300)
    });
}

/*
 * =========================================================
 * CLICK TRACKING
 * =========================================================
 */

function trackClicks() {

    document.addEventListener("click", function (event) {

        const target = event.target.closest(
            "a, button, [data-analytics]"
        );

        if (!target) {
            return;
        }

        const href = target.getAttribute("href") || "";

        const analyticsValue =
            target.getAttribute("data-analytics") || "";

        const analyticsName =
            analyticsValue ||
            target.getAttribute("aria-label") ||
            target.getAttribute("title") ||
            target.innerText ||
            "";

        const text = cleanText(analyticsName, 200);

        let eventType = "CLICK";

        /*
         * Phone
         */
        if (href.toLowerCase().startsWith("tel:")) {

            eventType = "PHONE_CLICK";

        }

        /*
         * Email
         */
        else if (href.toLowerCase().startsWith("mailto:")) {

            eventType = "EMAIL_CLICK";

        }

        /*
         * Quote
         */
        else if (
            analyticsValue === "quote" ||
            analyticsValue === "quote-start" ||
            analyticsValue === "quote_start"
        ) {

            eventType = "QUOTE_START";

        }

        /*
         * Booking
         */
        else if (
            analyticsValue === "booking" ||
            analyticsValue === "booking-start" ||
            analyticsValue === "booking_start"
        ) {

            eventType = "BOOKING_START";

        }

        /*
         * CTA
         */
        else if (
            analyticsValue === "cta" ||
            analyticsValue === "cta-click" ||
            analyticsValue === "cta_click"
        ) {

            eventType = "CTA_CLICK";

        }

        /*
         * FAQ
         */
        else if (
            target.matches(
                "details summary, .faq-question, [data-faq]"
            )
        ) {

            eventType = "FAQ_OPEN";

        }

        /*
         * Gallery
         */
        else if (
            target.matches(
                "[data-gallery], .gallery-item, .gallery-image"
            )
        ) {

            eventType = "GALLERY_VIEW";

        }

        /*
         * Downloads
         */
        else if (
            href &&
            /\.(pdf|doc|docx|xls|xlsx|csv|zip)$/i.test(href)
        ) {

            eventType = "DOWNLOAD";

        }

        sendEvent(
            eventType,
            text,
            {
                href: href.substring(0, 500)
            }
        );
    });
}

/*
 * =========================================================
 * FORM DETECTION
 * =========================================================
 */

function getFormType(form) {

    const value = (
        form.getAttribute("data-analytics-form") ||
        form.getAttribute("data-form-type") ||
        form.id ||
        form.name ||
        form.action ||
        form.className ||
        ""
    ).toLowerCase();

    if (
        value.includes("quote") ||
        value.includes("enquiry") ||
        value.includes("inquiry")
    ) {
        return "quote";
    }

    if (
        value.includes("booking") ||
        value.includes("book")
    ) {
        return "booking";
    }

    if (value.includes("contact")) {
        return "contact";
    }

    return null;
}

function trackForms() {

    const startedForms = new WeakSet();

    document.addEventListener("focusin", function (event) {

        const input = event.target;

        if (!input || !input.closest) {
            return;
        }

        const form = input.closest("form");

        if (!form) {
            return;
        }

        const formType = getFormType(form);

        if (!formType || startedForms.has(form)) {
            return;
        }

        startedForms.add(form);

        sendEvent(
            "FORM_START",
            formType,
            {
                form_type: formType,
                form_id: form.id || "",
                action: form.getAttribute("action") || ""
            }
        );
    });

    document.addEventListener("submit", function (event) {

        const form = event.target;

        if (!form || form.tagName !== "FORM") {
            return;
        }

        /*
         * Search forms are handled by trackSearchForms().
         */
        const searchInput = getSearchInput(form);

        if (searchInput) {
            return;
        }

        const formType = getFormType(form);

        if (!formType) {
            return;
        }

        const metadata = {
            form_type: formType,
            form_id: form.id || "",
            action: form.getAttribute("action") || ""
        };

        /*
         * Contact
         */
        if (formType === "contact") {

            sendEvent(
                "FORM_SUBMIT",
                "contact",
                metadata
            );

            return;
        }

        /*
         * Quote
         */
        if (formType === "quote") {

            sendEvent(
                "FORM_SUBMIT",
                "quote",
                metadata
            );

            sendEvent(
                "QUOTE_SUBMIT",
                "quote",
                metadata
            );

            return;
        }

        /*
         * Booking
         */
        if (formType === "booking") {

            sendEvent(
                "FORM_SUBMIT",
                "booking",
                metadata
            );

            sendEvent(
                "BOOKING_COMPLETE",
                "booking",
                metadata
            );
        }
    });
}

/*
 * =========================================================
 * SCROLL DEPTH
 * =========================================================
 */

function trackScrollDepth() {

    const milestones = [25, 50, 75, 90];

    const tracked = {};

    function checkScroll() {

        const documentHeight =
            document.documentElement.scrollHeight -
            window.innerHeight;

        if (documentHeight <= 0) {
            return;
        }

        const percentage = Math.round(
            (window.scrollY / documentHeight) * 100
        );

        milestones.forEach(function (milestone) {

            if (
                percentage >= milestone &&
                !tracked[milestone]
            ) {

                tracked[milestone] = true;

                sendEvent(
                    "SCROLL_DEPTH",
                    milestone + "%",
                    {
                        depth: milestone
                    }
                );
            }
        });
    }

    window.addEventListener(
        "scroll",
        checkScroll,
        {
            passive: true
        }
    );
}

/*
 * =========================================================
 * INITIALISE
 * =========================================================
 */

function initialiseAnalytics() {

    trackPageView();
    trackClicks();
    trackForms();
    trackSearchForms();
    trackScrollDepth();
}

if (document.readyState === "loading") {

    document.addEventListener(
        "DOMContentLoaded",
        initialiseAnalytics
    );

} else {

    initialiseAnalytics();

}


})();
