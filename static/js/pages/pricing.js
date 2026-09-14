/* =========================================================
   YD COMMERCIAL CLEANING — PRICING CALCULATOR
   Front-end indicative estimator only.
   Does NOT change Django/backend pricing.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const service = document.getElementById("calc-service");
    const bedrooms = document.getElementById("calc-bedrooms");
    const bathrooms = document.getElementById("calc-bathrooms");
    const frequency = document.getElementById("calc-frequency");
    const quantity = document.getElementById("calc-quantity");

    const propertyFields = document.getElementById("property-fields");
    const frequencyField = document.getElementById("frequency-field");
    const quantityField = document.getElementById("quantity-field");
    const quantityLabel = document.getElementById("quantity-label");

    const total = document.getElementById("calc-total");
    const period = document.getElementById("calc-period");
    const breakdown = document.getElementById("calc-breakdown");

    /*
     * Stop safely if the calculator isn't present.
     * This means the JS won't break other pages.
     */
    if (!service || !total) {
        return;
    }

    /*
     * Published starting prices from the Pricing page.
     */
    const basePrices = {
        residential: 180,
        deep: 280,
        bond: 330,
        spring: 320,
        oven: 120,
        carpet: 160,
        bathroom: 110,
        window: 140
    };

    const serviceLabels = {
        residential: "Residential cleaning",
        deep: "Deep cleaning",
        bond: "Bond / end-of-lease cleaning",
        spring: "Spring cleaning",
        oven: "Oven cleaning",
        carpet: "Carpet cleaning",
        bathroom: "Bathroom cleaning",
        window: "Window cleaning"
    };

    /*
     * Format currency for Australian users.
     */
    function formatMoney(value) {
        return Math.round(value).toLocaleString("en-AU");
    }

    /*
     * Show/hide fields depending on selected service.
     */
    function updateControls() {

        const selected = service.value;

        /*
         * These services use property size.
         */
        const propertyBasedServices = [
            "residential",
            "deep",
            "bond",
            "spring"
        ];

        const isPropertyBased =
            propertyBasedServices.includes(selected);

        propertyFields.style.display =
            isPropertyBased ? "" : "none";

        /*
         * Cleaning frequency only applies to residential
         * recurring cleaning.
         */
        frequencyField.style.display =
            selected === "residential" ? "" : "none";

        /*
         * Quantity selector is used for specialist services.
         */
        const quantityServices = [
            "oven",
            "carpet",
            "bathroom",
            "window"
        ];

        quantityField.style.display =
            quantityServices.includes(selected) ? "" : "none";

        /*
         * Change quantity label depending on service.
         */
        switch (selected) {

            case "oven":
                quantityLabel.textContent =
                    "Number of ovens";
                break;

            case "carpet":
                quantityLabel.textContent =
                    "Number of rooms";
                break;

            case "bathroom":
                quantityLabel.textContent =
                    "Number of bathrooms";
                break;

            case "window":
                quantityLabel.textContent =
                    "Number of window services";
                break;

            default:
                quantityLabel.textContent =
                    "Quantity";
        }

        /*
         * Keep the quantity options consistent.
         */
        if (selected === "oven") {

            quantity.options[0].textContent = "1 oven";
            quantity.options[1].textContent = "2 ovens";
            quantity.options[2].textContent = "3 ovens";

        } else if (selected === "carpet") {

            quantity.options[0].textContent = "1 room";
            quantity.options[1].textContent = "2 rooms";
            quantity.options[2].textContent = "3 rooms";

        } else if (selected === "bathroom") {

            quantity.options[0].textContent =
                "1 bathroom";

            quantity.options[1].textContent =
                "2 bathrooms";

            quantity.options[2].textContent =
                "3 bathrooms";

        } else if (selected === "window") {

            quantity.options[0].textContent =
                "1 service";

            quantity.options[1].textContent =
                "2 services";

            quantity.options[2].textContent =
                "3 services";
        }
    }

    /*
     * Calculate the indicative price.
     */
    function calculatePrice() {

        const selected = service.value;

        let base =
            basePrices[selected] || 0;

        let adjustment = 0;

        let displayPeriod = "per service";

        let frequencyText = "One-off";

        /*
         * -----------------------------------------------------
         * RESIDENTIAL
         * -----------------------------------------------------
         */

        if (selected === "residential") {

            const bed =
                Number(bedrooms.value);

            const bath =
                Number(bathrooms.value);

            /*
             * Starting point:
             * $180
             *
             * Additional bedrooms:
             * +$20 each above 2
             *
             * Additional bathrooms:
             * +$25 each above 1
             */
            adjustment +=
                Math.max(0, bed - 2) * 20;

            adjustment +=
                Math.max(0, bath - 1) * 25;

            /*
             * Small indicative adjustment for
             * recurring services.
             */
            if (frequency.value === "weekly") {

                adjustment -= 10;

                frequencyText = "Weekly";

            } else if (
                frequency.value === "fortnightly"
            ) {

                adjustment -= 5;

                frequencyText = "Fortnightly";

            } else {

                frequencyText = "One-off";
            }

            displayPeriod = "per visit";
        }

        /*
         * -----------------------------------------------------
         * DEEP / BOND / SPRING
         * -----------------------------------------------------
         */

        else if (
            selected === "deep" ||
            selected === "bond" ||
            selected === "spring"
        ) {

            const bed =
                Number(bedrooms.value);

            const bath =
                Number(bathrooms.value);

            /*
             * Indicative property-size adjustment.
             */
            adjustment +=
                Math.max(0, bed - 2) * 25;

            adjustment +=
                Math.max(0, bath - 1) * 25;

            displayPeriod = "per property";

            frequencyText = "One-off";
        }

        /*
         * -----------------------------------------------------
         * SPECIALIST SERVICES
         * -----------------------------------------------------
         */

        else {

            const selectedQuantity =
                Math.min(
                    Number(quantity.value),
                    3
                );

            /*
             * Example:
             *
             * Oven = $120
             *
             * 1 oven = $120
             * 2 ovens = $240
             * 3 ovens = $360
             */
            adjustment =
                (selectedQuantity - 1) * base;

            if (selected === "carpet") {

                displayPeriod = "per room(s)";

            } else if (selected === "bathroom") {

                displayPeriod =
                    "per bathroom(s)";

            } else if (selected === "oven") {

                displayPeriod =
                    "per oven(s)";

            } else {

                displayPeriod =
                    "per service(s)";
            }

            frequencyText = "One-off";
        }

        /*
         * Never allow a negative price.
         */
        const finalPrice =
            Math.max(0, base + adjustment);

        /*
         * Update main displayed price.
         */
        total.textContent =
            formatMoney(finalPrice);

        period.textContent =
            displayPeriod;

        /*
         * Update breakdown.
         */
        const adjustmentSign =
            adjustment >= 0 ? "+" : "−";

        breakdown.innerHTML = `
            <div>
                <span>
                    Base ${serviceLabels[selected].toLowerCase()}
                </span>

                <strong>
                    $${formatMoney(base)}
                </strong>
            </div>

            <div>
                <span>
                    Indicative adjustment
                </span>

                <strong>
                    ${adjustmentSign}$${formatMoney(
                        Math.abs(adjustment)
                    )}
                </strong>
            </div>

            <div>
                <span>
                    Service timing
                </span>

                <strong>
                    ${frequencyText}
                </strong>
            </div>
        `;
    }

    /*
     * Listen for changes.
     */
    const fields = [
        service,
        bedrooms,
        bathrooms,
        frequency,
        quantity
    ];

    fields.forEach(function (field) {

        if (!field) {
            return;
        }

        field.addEventListener(
            "change",
            function () {

                updateControls();
                calculatePrice();

            }
        );
    });

    /*
     * Initial calculator state.
     */
    updateControls();
    calculatePrice();

});