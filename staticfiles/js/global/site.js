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

    const siteSearchData = [
        { title: "Home", url: "/" },
        { title: "About Us", url: "/about/" },
        { title: "Pricing", url: "/pricing/" },
        { title: "Team", url: "/team/" },
        { title: "Gallery", url: "/gallery/" },
        { title: "Contact", url: "/contact/" },
        { title: "Services", url: "/services/" },
        { title: "House Cleaning", url: "/services/house-cleaning-adelaide/" },
        { title: "Commercial Cleaning", url: "/services/commercial-cleaning-adelaide/" },
        { title: "Office Cleaning", url: "/services/office-cleaning/" },
        { title: "Spring Cleaning", url: "/services/spring-cleaning/" },
        { title: "Oven Cleaning", url: "/services/oven-cleaning/" },
        { title: "Bathroom Cleaning", url: "/services/bathroom-cleaning/" },
        { title: "Bond Cleaning", url: "/services/bond-cleaning/" },
        { title: "Exit Cleaning", url: "/services/exit-cleaning/" },
        { title: "Carpet Cleaning", url: "/services/carpet-cleaning/" },
        { title: "Window Cleaning", url: "/services/window-cleaning-adelaide/" },
        { title: "Post Construction Cleaning", url: "/services/post-construction-cleaning-adelaide/" },
        { title: "End of Lease Cleaning", url: "/services/end-of-lease-cleaning-adelaide/" },
        { title: "Resources", url: "/resources/" },
        { title: "Blog", url: "/blog/" },
        { title: "Customer Portal", url: "/portal/login/" },
        { title: "Employee Portal", url: "/employee/login/" }
    ];

    const closeMenu = function () {
        if (publicMenu) {
            publicMenu.classList.remove("active");
        }
        if (menuButton) {
            menuButton.setAttribute("aria-expanded", "false");
        }
    };

    const closeSearch = function () {
        if (searchBox) {
            searchBox.classList.remove("active");
        }
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

        const matchingCount = links.filter(function (link) {
            return window.getComputedStyle(link).display !== "none";
        }).length;

        if (!matchingCount && query) {
            const fallback = document.createElement("a");
            fallback.href = "/";
            fallback.textContent = "No exact matches found. Try a broader keyword.";
            fallback.style.display = "block";
            searchResults.appendChild(fallback);
        }
    };

    if (offerBanner && offerClose) {
        const bannerDismissed = localStorage.getItem("yd_offer_banner_dismissed");
        if (bannerDismissed === "true") {
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
            if (!publicMenu.contains(event.target) && !menuButton.contains(event.target)) {
                closeMenu();
            }
        });
    }

    if (searchButton && searchBox) {
        searchButton.addEventListener("click", function () {
            const shouldOpen = !searchBox.classList.contains("active");
            searchBox.classList.toggle("active", shouldOpen);
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
            closeMenu();
            closeSearch();
        }
    });

    if (searchInput && searchResults) {
        searchInput.addEventListener("input", function () {
            refreshSearchResults(searchInput.value);
        });
    }

    document.querySelectorAll(".yd-dropdown-parent, .yd-mega-parent").forEach(function (parentItem) {
        const trigger = parentItem.querySelector("a");
        if (!trigger || window.innerWidth > 1000) {
            return;
        }

        trigger.addEventListener("click", function (event) {
            const submenu = parentItem.querySelector(".yd-dropdown-menu, .yd-mega-menu");
            if (!submenu) {
                return;
            }

            const isOpen = parentItem.classList.toggle("js-open");
            event.preventDefault();
            submenu.style.display = isOpen ? "block" : "none";
        });
    });

    if (notificationBell) {
        notificationBell.addEventListener("click", function () {
            fetch("/notifications/mark-read/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && notificationCount) {
                    notificationCount.textContent = "0";
                    notificationCount.style.display = "none";

                    document.querySelectorAll(".notification-dropdown a.unread").forEach(function (item) {
                        item.classList.remove("unread");
                    });
                }
            });
        });
    }

    // Handle Services mega menu click on mobile/desktop
    const servicesLink = document.querySelector(".yd-mega-parent > a");
    if (servicesLink) {
        servicesLink.addEventListener("click", function (e) {
            // On mobile/tablet (width <= 1000px), toggle the menu on first click, navigate on second click
            if (window.innerWidth <= 1000) {
                const parent = servicesLink.parentElement;
                const isOpen = parent.classList.contains("js-open");

                if (!isOpen) {
                    e.preventDefault();
                    parent.classList.add("js-open");
                    const menu = parent.querySelector(".yd-mega-menu");
                    if (menu) menu.style.display = "block";
                } else {
                    window.location.href = servicesLink.href;
                }
            } else {
                // On desktop, clicking immediately navigates to the services page
                window.location.href = servicesLink.href;
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
        slideWidth = slides[0].getBoundingClientRect().width + 24;
        track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
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
