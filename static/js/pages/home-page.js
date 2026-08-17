function getFieldValueByName(name) {
    const fields = document.querySelectorAll(`[name="${name}"]`);
    const field = fields[fields.length - 1];

    if (!field) {
        return 0;
    }

    return parseInt(field.value || 0);
}

function isCheckedByName(name) {
    const fields = document.querySelectorAll(`[name="${name}"]`);
    const field = fields[fields.length - 1];

    if (!field) {
        return false;
    }

    return field.checked;
}

function updateEstimate() {
    let price = 120;

    const bedrooms = getFieldValueByName("bedrooms");
    const bathrooms = getFieldValueByName("bathrooms");

    price += bedrooms * 30;
    price += bathrooms * 20;

    if (isCheckedByName("window_cleaning")) {
        price += 50;
    }

    if (isCheckedByName("carpet_shampooing")) {
        price += 100;
    }

    if (isCheckedByName("grout_cleaning")) {
        price += 75;
    }

    if (isCheckedByName("upholstery_cleaning")) {
        price += 60;
    }

    if (isCheckedByName("laundry_service")) {
        price += 60;
    }

    const estimateBox = document.getElementById("estimated-price");

    if (estimateBox) {
        estimateBox.innerText = "$" + price;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    document
        .querySelectorAll(
            'input[name="bedrooms"], input[name="bathrooms"], input[type="checkbox"], select'
        )
        .forEach(function (field) {
            field.addEventListener("change", updateEstimate);
            field.addEventListener("keyup", updateEstimate);
            field.addEventListener("input", updateEstimate);
        });

    const revealElements = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    revealElements.forEach(function (element) {
        observer.observe(element);
    });

    updateEstimate();
});


document.addEventListener("DOMContentLoaded", function () {
    const heroVideo = document.getElementById("heroVideo");
    const soundToggle = document.getElementById("heroSoundToggle");

    if (!heroVideo || !soundToggle) {
        return;
    }

    soundToggle.addEventListener("click", function () {
        heroVideo.muted = !heroVideo.muted;

        if (heroVideo.muted) {
            soundToggle.textContent = "🔇 Sound Off";
            soundToggle.setAttribute("aria-label", "Turn video sound on");
            soundToggle.setAttribute("aria-pressed", "false");
        } else {
            soundToggle.textContent = "🔊 Sound On";
            soundToggle.setAttribute("aria-label", "Turn video sound off");
            soundToggle.setAttribute("aria-pressed", "true");

            heroVideo.play().catch(function () {
                console.log("Video playback requires user interaction.");
            });
        }
    });
});