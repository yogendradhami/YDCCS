/* =========================================================
   YD COMMERCIAL CLEANING
   CASE STUDIES — FILTER INTERACTION
   ========================================================= */

(function () {
    "use strict";

    function initCaseStudies() {
        const filters = document.querySelectorAll(".cs-filter");
        const projects = document.querySelectorAll(".cs-project");

        if (!filters.length || !projects.length) {
            return;
        }

        filters.forEach(function (filter) {
            filter.addEventListener("click", function () {

                const selectedCategory = filter.dataset.filter;

                /*
                 * Update active button
                 */
                filters.forEach(function (button) {
                    const isActive = button === filter;

                    button.classList.toggle(
                        "is-active",
                        isActive
                    );

                    button.setAttribute(
                        "aria-pressed",
                        isActive ? "true" : "false"
                    );
                });

                /*
                 * Filter projects
                 */
                projects.forEach(function (project) {

                    const projectCategory =
                        project.dataset.category;

                    const shouldShow =
                        selectedCategory === "all" ||
                        projectCategory === selectedCategory;

                    project.classList.toggle(
                        "is-hidden",
                        !shouldShow
                    );
                });
            });
        });
    }


    /*
     * Smooth anchor scrolling
     *
     * Only applies to anchors that point to an element
     * on the current page.
     */
    function initSmoothScrolling() {

        const links = document.querySelectorAll(
            'a[href^="#"]'
        );

        links.forEach(function (link) {

            link.addEventListener("click", function (event) {

                const targetId =
                    link.getAttribute("href");

                if (
                    !targetId ||
                    targetId === "#" ||
                    targetId.length < 2
                ) {
                    return;
                }

                const target =
                    document.querySelector(targetId);

                if (!target) {
                    return;
                }

                event.preventDefault();

                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            });
        });
    }


    /*
     * Small reveal animation using IntersectionObserver.
     *
     * It only activates when the browser supports it and
     * the user has not requested reduced motion.
     */
    function initRevealAnimation() {

        if (
            !("IntersectionObserver" in window) ||
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches
        ) {
            return;
        }

        const revealItems = document.querySelectorAll(
            ".cs-project, " +
            ".cs-method-cards article, " +
            ".cs-industry-card, " +
            ".cs-testimonial, " +
            ".cs-transformation-card"
        );

        if (!revealItems.length) {
            return;
        }

        revealItems.forEach(function (item) {
            item.classList.add("cs-reveal-ready");
        });

        const observer =
            new IntersectionObserver(
                function (entries, observerInstance) {

                    entries.forEach(function (entry) {

                        if (!entry.isIntersecting) {
                            return;
                        }

                        entry.target.classList.add(
                            "cs-reveal-visible"
                        );

                        observerInstance.unobserve(
                            entry.target
                        );
                    });
                },
                {
                    threshold: 0.08,
                    rootMargin: "0px 0px -50px 0px"
                }
            );

        revealItems.forEach(function (item) {
            observer.observe(item);
        });
    }


    /*
     * Initialise everything after the DOM is ready.
     */
    function init() {
        initCaseStudies();
        initSmoothScrolling();
        initRevealAnimation();
    }


    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }

})();