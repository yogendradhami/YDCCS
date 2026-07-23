document.addEventListener("DOMContentLoaded", function () {
    const menuButton = document.getElementById("publicMenuButton");
    const publicMenu = document.getElementById("publicMenu");
    const searchButton = document.getElementById("publicSearchButton");
    const searchBox = document.getElementById("siteSearchBox");
    const searchInput = document.getElementById("siteSearchInput");
    const searchResults = document.getElementById("siteSearchResults");
    const notificationBell = document.getElementById("notificationBell");
    const notificationCount = document.getElementById("notificationCount");

    if (menuButton && publicMenu) {
        menuButton.addEventListener("click", function () {
            const isOpen = publicMenu.classList.toggle("active");
            menuButton.setAttribute("aria-expanded", isOpen.toString());
        });
    }

    if (searchButton && searchBox) {
        searchButton.addEventListener("click", function () {
            searchBox.classList.toggle("active");

            if (searchBox.classList.contains("active")) {
                searchInput.focus();
            }
        });
    }

    if (searchInput && searchResults) {
        searchInput.addEventListener("input", function () {
            const keyword = searchInput.value.toLowerCase();
            const links = searchResults.querySelectorAll("a");

            links.forEach(function (link) {
                link.style.display = link.textContent.toLowerCase().includes(keyword)
                    ? "block"
                    : "none";
            });
        });
    }

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
