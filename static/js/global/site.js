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

    initReviewCarousel();
});

function initReviewCarousel() {
    const carousel = document.querySelector('[data-review-carousel]');
    if (!carousel) {
        return;
    }

    const track = carousel.querySelector('.home-review-carousel-track');
    const slides = Array.from(track.querySelectorAll('.home-review-slide'));
    const prevButton = carousel.parentElement.querySelector('.carousel-control.prev');
    const nextButton = carousel.parentElement.querySelector('.carousel-control.next');

    if (!track || slides.length === 0 || !prevButton || !nextButton) {
        return;
    }

    let currentIndex = 0;
    let slideWidth = slides[0].getBoundingClientRect().width + 24;
    let autoPlay;
    const dotsContainer = carousel.parentElement.querySelector('.carousel-dots');
    let dots = [];
    let touchStartX = 0;
    let touchEndX = 0;
    let isDragging = false;

    function updateButtons() {
        prevButton.disabled = currentIndex === 0;
        nextButton.disabled = currentIndex >= slides.length - 1;
    }

    function renderDots() {
        if (!dotsContainer) {
            return;
        }
        dotsContainer.innerHTML = '';
        dots = slides.map((slide, index) => {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'carousel-dot';
            dot.setAttribute('aria-label', `Go to review ${index + 1}`);
            dot.addEventListener('click', function () {
                goTo(index);
                startAutoPlay();
            });
            dotsContainer.appendChild(dot);
            return dot;
        });
        updateDots();
    }

    function updateDots() {
        if (!dots.length) {
            return;
        }
        dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === currentIndex);
        });
    }

    function refreshDimensions() {
        const visibleWidth = carousel.clientWidth || slides[0].getBoundingClientRect().width;
        slideWidth = visibleWidth + 24;
        track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        if (window.innerWidth <= 980) {
            slides.forEach((slide) => {
                slide.style.width = `${carousel.clientWidth}px`;
                slide.style.minWidth = `${carousel.clientWidth}px`;
                slide.style.flexBasis = `${carousel.clientWidth}px`;
            });
        } else {
            slides.forEach((slide) => {
                slide.style.width = '';
                slide.style.minWidth = '';
                slide.style.flexBasis = '';
            });
        }
    }

    function goTo(index) {
        currentIndex = Math.max(0, Math.min(index, slides.length - 1));
        track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        updateButtons();
        updateDots();
    }

    function startAutoPlay() {
        if (autoPlay) {
            clearInterval(autoPlay);
        }
        autoPlay = setInterval(function () {
            const nextIndex = currentIndex >= slides.length - 1 ? 0 : currentIndex + 1;
            goTo(nextIndex);
        }, 6500);
    }

    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;

        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                goTo(currentIndex + 1);
            } else {
                goTo(currentIndex - 1);
            }
            startAutoPlay();
        }
    }

    prevButton.addEventListener('click', function () {
        goTo(currentIndex - 1);
    });

    nextButton.addEventListener('click', function () {
        goTo(currentIndex + 1);
    });

    carousel.addEventListener('touchstart', function (e) {
        touchStartX = e.changedTouches[0].screenX;
        isDragging = true;
        if (autoPlay) {
            clearInterval(autoPlay);
        }
    }, false);

    carousel.addEventListener('touchend', function (e) {
        touchEndX = e.changedTouches[0].screenX;
        isDragging = false;
        handleSwipe();
    }, false);

    carousel.addEventListener('mouseenter', function () {
        if (autoPlay) {
            clearInterval(autoPlay);
        }
    });

    carousel.addEventListener('mouseleave', startAutoPlay);
    window.addEventListener('resize', refreshDimensions);

    renderDots();
    refreshDimensions();
    updateButtons();
    startAutoPlay();
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
