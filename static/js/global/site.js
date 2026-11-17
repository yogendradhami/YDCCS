document.addEventListener("DOMContentLoaded", function () {
    const menuButton = document.getElementById("publicMenuButton");
    const publicMenu = document.getElementById("publicMenu");
    const searchButton = document.getElementById("publicSearchButton");
    const searchBox = document.getElementById("siteSearchBox");
    const searchInput = document.getElementById("siteSearchInput");
    const searchResults = document.getElementById("siteSearchResults");
    const notificationBell = document.getElementById("notificationBell");
    const notificationCount = document.getElementById("notificationCount");
    const offerBanner = document.getElementById("offerBanner");
    const offerClose = document.querySelector(".promo-close");

    const closeMenu = function () {
        if (publicMenu) {
            publicMenu.classList.remove("active");
        }
        document.querySelectorAll(".yd-mega-parent, .yd-dropdown-parent").forEach(function (item) {
            item.classList.remove("active");
            const trigger = item.querySelector("a.yd-menu-trigger");
            if (trigger) {
                trigger.setAttribute("aria-expanded", "false");
            }
        });
        if (menuButton) {
            menuButton.setAttribute("aria-expanded", "false");
        }
    };

    const closeSearch = function () {
        if (searchBox) {
            searchBox.classList.remove("active");
            searchBox.setAttribute("aria-hidden", "true");
        }
        if (searchButton) {
            searchButton.setAttribute("aria-expanded", "false");
        }
    };

    const closeAllMenus = function () {
        closeMenu();
        closeSearch();
    };

    const refreshSearchResults = function (keyword) {
        if (!searchResults) {
            return;
        }

        const query = (keyword || "").trim().toLowerCase();
        const links = Array.from(searchResults.querySelectorAll("a"));

        if (!links.length) {
            return;
        }

        links.forEach(function (link) {
            const text = (link.textContent || "").toLowerCase();
            const url = (link.getAttribute("href") || "").toLowerCase();
            const matches = !query || text.includes(query) || url.includes(query);
            link.style.display = matches ? "block" : "none";
        });

        if (query) {
            const visible = links.filter(function (link) {
                return window.getComputedStyle(link).display !== "none";
            });

            if (!visible.length) {
                const fallback = document.createElement("a");
                fallback.href = "/";
                fallback.textContent = "No exact matches found. Try a broader keyword.";
                fallback.style.display = "block";
                fallback.className = "site-search-empty";
                const existingEmpty = searchResults.querySelector(".site-search-empty");
                if (!existingEmpty) {
                    searchResults.appendChild(fallback);
                }
            } else {
                const emptyItem = searchResults.querySelector(".site-search-empty");
                if (emptyItem) {
                    emptyItem.remove();
                }
            }
        } else {
            const emptyItem = searchResults.querySelector(".site-search-empty");
            if (emptyItem) {
                emptyItem.remove();
            }
        }
    };

    if (offerBanner && offerClose) {
        if (localStorage.getItem("yd_offer_banner_dismissed") === "true") {
            offerBanner.style.display = "none";
        }

        offerClose.addEventListener("click", function () {
            offerBanner.style.display = "none";
            localStorage.setItem("yd_offer_banner_dismissed", "true");
        });
    }

    if (menuButton && publicMenu) {
        menuButton.addEventListener("click", function () {
            const isOpen = publicMenu.classList.toggle("active");
            menuButton.setAttribute("aria-expanded", isOpen.toString());
            closeSearch();
        });

        document.addEventListener("click", function (event) {
            const target = event.target;
            const insideMenu = publicMenu.contains(target);
            const insideButton = menuButton.contains(target);
            if (!insideMenu && !insideButton) {
                closeMenu();
            }
        });
    }

    if (searchButton && searchBox) {
        searchButton.addEventListener("click", function () {
            const shouldOpen = !searchBox.classList.contains("active");
            searchBox.classList.toggle("active", shouldOpen);
            searchBox.setAttribute("aria-hidden", shouldOpen ? "false" : "true");
            searchButton.setAttribute("aria-expanded", shouldOpen.toString());
            closeMenu();

            if (shouldOpen && searchInput) {
                searchInput.value = "";
                refreshSearchResults("");
                setTimeout(function () {
                    searchInput.focus();
                }, 20);
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeAllMenus();
        }
    });

    if (searchInput && searchResults) {
        searchInput.addEventListener("input", function () {
            refreshSearchResults(searchInput.value);
        });
    }

    document.querySelectorAll(".yd-dropdown-parent, .yd-mega-parent").forEach(function (parentItem) {
        const trigger = parentItem.querySelector("a.yd-menu-trigger");
        if (!trigger) {
            return;
        }

        trigger.setAttribute("aria-expanded", "false");

        if (window.innerWidth <= 1000) {
            trigger.addEventListener("click", function (event) {
                const href = trigger.getAttribute("href");
                const menu = parentItem.querySelector(".yd-dropdown-menu, .yd-mega-menu");
                if (!menu) {
                    return;
                }

                if (href === "#") {
                    event.preventDefault();
                }

                const isOpen = parentItem.classList.contains("active");
                document.querySelectorAll(".yd-mega-parent, .yd-dropdown-parent").forEach(function (other) {
                    if (other !== parentItem) {
                        other.classList.remove("active");
                        const otherTrigger = other.querySelector("a.yd-menu-trigger");
                        if (otherTrigger) {
                            otherTrigger.setAttribute("aria-expanded", "false");
                        }
                    }
                });

                parentItem.classList.toggle("active", !isOpen);
                trigger.setAttribute("aria-expanded", String(!isOpen));
            });
        } else {
            trigger.addEventListener("mouseenter", function () {
                parentItem.classList.add("active");
                trigger.setAttribute("aria-expanded", "true");
            });

            parentItem.addEventListener("mouseleave", function () {
                parentItem.classList.remove("active");
                trigger.setAttribute("aria-expanded", "false");
            });

            parentItem.addEventListener("focusin", function () {
                parentItem.classList.add("active");
                trigger.setAttribute("aria-expanded", "true");
            });

            parentItem.addEventListener("focusout", function (event) {
                const nextFocus = event.relatedTarget;
                if (nextFocus && parentItem.contains(nextFocus)) {
                    return;
                }
                parentItem.classList.remove("active");
                trigger.setAttribute("aria-expanded", "false");
            });
        }
    });

    document.addEventListener("click", function (event) {
        const clickTarget = event.target;
        const clickedInsideDropdown = clickTarget.closest(".yd-mega-parent") || clickTarget.closest(".yd-dropdown-parent");
        if (!clickedInsideDropdown) {
            document.querySelectorAll(".yd-mega-parent, .yd-dropdown-parent").forEach(function (item) {
                item.classList.remove("active");
                const trigger = item.querySelector("a.yd-menu-trigger");
                if (trigger) {
                    trigger.setAttribute("aria-expanded", "false");
                }
            });
        }
    });

    if (notificationBell) {
        notificationBell.addEventListener("click", function () {
            const box = notificationBell.closest(".portal-notification-box");
            if (box) {
                box.classList.toggle("active");
                notificationBell.setAttribute("aria-expanded", box.classList.contains("active") ? "true" : "false");
            }

            if (typeof getCookie === "function") {
                fetch("/notifications/mark-read/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest"
                    }
                })
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    if (data.success && notificationCount) {
                        notificationCount.textContent = "0";
                        notificationCount.style.display = "none";
                        document.querySelectorAll(".notification-dropdown a.unread").forEach(function (item) {
                            item.classList.remove("unread");
                        });
                    }
                });
            }
        });
    }

    document.querySelectorAll("[data-review-carousel]").forEach(initReviewCarousel);
});

function initReviewCarousel(carousel) {
    if (!carousel || carousel.dataset.carouselInitialized === "true") {
        return;
    }

    const viewport = carousel.querySelector(".home-reviews-viewport");
    const track = carousel.querySelector(".home-reviews-track");
    const dotsContainer = carousel.parentElement.querySelector(".review-carousel-dots");
    const prevButton = carousel.querySelector(".review-prev");
    const nextButton = carousel.querySelector(".review-next");

    if (!viewport || !track || !prevButton || !nextButton) {
        return;
    }

    const slides = Array.from(track.querySelectorAll(".home-review-slide"));
    carousel.dataset.carouselInitialized = "true";
    if (!slides.length) {
        prevButton.hidden = true;
        nextButton.hidden = true;
        if (dotsContainer) {
            dotsContainer.hidden = true;
        }
        return;
    }

    let currentIndex = 0;
    let autoplayTimer = null;
    let isHovered = false;
    let isFocused = false;
    let isTouching = false;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const dots = [];

    function currentOffset() {
        return currentIndex === 0 ? 0 : currentIndex * viewport.clientWidth;
    }

    function isPaused() {
        return isHovered || isFocused || isTouching ||
            document.visibilityState === "hidden" || reducedMotion.matches;
    }

    function update() {
        const offset = currentOffset();
        track.style.transform = `translate3d(${offset === 0 ? 0 : -offset}px, 0, 0)`;
        viewport.style.height = `${slides[currentIndex].offsetHeight}px`;

        slides.forEach(function (slide, index) {
            const isActive = index === currentIndex;
            slide.setAttribute("aria-hidden", String(!isActive));
            slide.classList.toggle("is-active", isActive);
        });

        dots.forEach(function (dot, index) {
            const isActive = index === currentIndex;
            dot.classList.toggle("active", isActive);
            if (isActive) {
                dot.setAttribute("aria-current", "true");
            } else {
                dot.removeAttribute("aria-current");
            }
        });
    }

    function show(index) {
        currentIndex = (index + slides.length) % slides.length;
        update();
    }

    function stopAutoplay() {
        if (autoplayTimer !== null) {
            window.clearTimeout(autoplayTimer);
            autoplayTimer = null;
        }
    }

    function scheduleAutoplay() {
        stopAutoplay();
        if (slides.length < 2 || isPaused()) {
            return;
        }
        autoplayTimer = window.setTimeout(function () {
            autoplayTimer = null;
            show(currentIndex + 1);
            scheduleAutoplay();
        }, 5000);
    }

    function restartAutoplay() {
        stopAutoplay();
        scheduleAutoplay();
    }

    slides.forEach(function (_slide, index) {
        if (!dotsContainer) {
            return;
        }
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "review-carousel-dot";
        dot.setAttribute("aria-label", `Go to review ${index + 1}`);
        dot.addEventListener("click", function () {
            show(index);
            restartAutoplay();
        });
        dotsContainer.appendChild(dot);
        dots.push(dot);
    });

    prevButton.disabled = slides.length < 2;
    nextButton.disabled = slides.length < 2;
    prevButton.addEventListener("click", function () {
        show(currentIndex - 1);
        restartAutoplay();
    });
    nextButton.addEventListener("click", function () {
        show(currentIndex + 1);
        restartAutoplay();
    });

    viewport.addEventListener("mouseenter", function () {
        isHovered = true;
        stopAutoplay();
    });
    viewport.addEventListener("mouseleave", function () {
        isHovered = false;
        scheduleAutoplay();
    });
    carousel.addEventListener("focusin", function () {
        isFocused = true;
        stopAutoplay();
    });
    carousel.addEventListener("focusout", function (event) {
        if (!carousel.contains(event.relatedTarget)) {
            isFocused = false;
            scheduleAutoplay();
        }
    });
    carousel.addEventListener("keydown", function (event) {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            show(currentIndex - 1);
            restartAutoplay();
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            show(currentIndex + 1);
            restartAutoplay();
        }
    });

    let touchStartX = null;
    viewport.addEventListener("touchstart", function (event) {
        touchStartX = event.changedTouches[0].clientX;
        isTouching = true;
        stopAutoplay();
    }, { passive: true });
    viewport.addEventListener("touchend", function (event) {
        if (touchStartX !== null) {
            const distance = touchStartX - event.changedTouches[0].clientX;
            if (Math.abs(distance) > 50) {
                show(currentIndex + (distance > 0 ? 1 : -1));
            }
        }
        touchStartX = null;
        isTouching = false;
        scheduleAutoplay();
    }, { passive: true });
    viewport.addEventListener("touchcancel", function () {
        touchStartX = null;
        isTouching = false;
        scheduleAutoplay();
    }, { passive: true });

    document.addEventListener("visibilitychange", scheduleAutoplay);
    reducedMotion.addEventListener("change", scheduleAutoplay);
    window.addEventListener("resize", update);

    update();
    scheduleAutoplay();
}

function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");

        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}
