/* =========================================================
   YD COMMERCIAL CLEANING
   ABOUT PAGE
   Testimonial Carousel
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const carousel = document.querySelector(".carousel-track");
    const slides = document.querySelectorAll(".carousel-slide");
    const previousButton = document.querySelector(".carousel-prev");
    const nextButton = document.querySelector(".carousel-next");
    const dots = document.querySelectorAll(".carousel-dots .dot");

    if (!carousel || slides.length === 0) {
        return;
    }

    let currentIndex = 0;
    let autoplayTimer = null;

    const totalSlides = slides.length;


    /* ---------------------------------------------------------
       UPDATE CAROUSEL
       --------------------------------------------------------- */

    function updateCarousel() {

        carousel.style.transform =
            `translateX(-${currentIndex * 100}%)`;

        dots.forEach(function (dot, index) {

            const isActive = index === currentIndex;

            dot.classList.toggle("active", isActive);

            dot.setAttribute(
                "aria-current",
                isActive ? "true" : "false"
            );

        });

    }


    /* ---------------------------------------------------------
       GO TO SLIDE
       --------------------------------------------------------- */

    function goToSlide(index) {

        if (index < 0) {
            currentIndex = totalSlides - 1;
        } else if (index >= totalSlides) {
            currentIndex = 0;
        } else {
            currentIndex = index;
        }

        updateCarousel();
        restartAutoplay();

    }


    /* ---------------------------------------------------------
       NEXT / PREVIOUS
       --------------------------------------------------------- */

    function nextSlide() {
        goToSlide(currentIndex + 1);
    }

    function previousSlide() {
        goToSlide(currentIndex - 1);
    }


    /* ---------------------------------------------------------
       BUTTON EVENTS
       --------------------------------------------------------- */

    if (nextButton) {

        nextButton.addEventListener("click", function () {
            nextSlide();
        });

    }


    if (previousButton) {

        previousButton.addEventListener("click", function () {
            previousSlide();
        });

    }


    /* ---------------------------------------------------------
       DOT EVENTS
       --------------------------------------------------------- */

    dots.forEach(function (dot, index) {

        dot.addEventListener("click", function () {
            goToSlide(index);
        });

    });


    /* ---------------------------------------------------------
       AUTOPLAY
       --------------------------------------------------------- */

    function startAutoplay() {

        stopAutoplay();

        autoplayTimer = setInterval(function () {
            nextSlide();
        }, 8000);

    }


    function stopAutoplay() {

        if (autoplayTimer) {

            clearInterval(autoplayTimer);
            autoplayTimer = null;

        }

    }


    function restartAutoplay() {

        startAutoplay();

    }


    /* ---------------------------------------------------------
       PAUSE WHEN USER HOVERS OVER CAROUSEL
       --------------------------------------------------------- */

    const carouselWrapper =
        document.querySelector(".testimonials-carousel-wrapper");


    if (carouselWrapper) {

        carouselWrapper.addEventListener(
            "mouseenter",
            stopAutoplay
        );

        carouselWrapper.addEventListener(
            "mouseleave",
            startAutoplay
        );

    }


    /* ---------------------------------------------------------
       KEYBOARD NAVIGATION
       --------------------------------------------------------- */

    document.addEventListener("keydown", function (event) {

        if (event.key === "ArrowLeft") {
            previousSlide();
        }

        if (event.key === "ArrowRight") {
            nextSlide();
        }

    });


    /* ---------------------------------------------------------
       INITIALISE
       --------------------------------------------------------- */

    updateCarousel();
    startAutoplay();

});