/* ==========================================================
   YD COMMERCIAL CLEANING
   PREMIUM DASHBOARD HOME JAVASCRIPT
========================================================== */

(function () {

    "use strict";


    /* ==========================================================
       INITIALISE
    ========================================================== */

    document.addEventListener("DOMContentLoaded", function () {

        initialiseDashboardCharts();
        initialiseDashboardInteractions();

    });


    /* ==========================================================
       SAFE JSON READER
    ========================================================== */

    function getJSON(id) {

        const element = document.getElementById(id);

        if (!element) {
            return [];
        }

        try {

            return JSON.parse(element.textContent);

        } catch (error) {

            console.warn(
                "Unable to parse dashboard JSON:",
                id,
                error
            );

            return [];
        }
    }


    /* ==========================================================
       CHART DEFAULTS
    ========================================================== */

    function chartOptions() {

        return {

            responsive: true,

            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    displayColors: false,

                    backgroundColor: "#111827",

                    titleColor: "#ffffff",

                    bodyColor: "#e5e7eb",

                    padding: 12,

                    cornerRadius: 10

                }

            },

            scales: {

                x: {

                    grid: {
                        display: false
                    },

                    border: {
                        display: false
                    },

                    ticks: {

                        color: "#94a3b8",

                        font: {
                            size: 10
                        }

                    }

                },

                y: {

                    beginAtZero: true,

                    grid: {
                        color: "#f1f5f9"
                    },

                    border: {
                        display: false
                    },

                    ticks: {

                        color: "#94a3b8",

                        font: {
                            size: 10
                        }

                    }

                }

            }

        };

    }


    /* ==========================================================
       GRADIENT
    ========================================================== */

    function createGradient(context, chartArea) {

        const gradient = context.createLinearGradient(
            0,
            chartArea.bottom,
            0,
            chartArea.top
        );

        gradient.addColorStop(
            0,
            "rgba(37, 99, 235, 0)"
        );

        gradient.addColorStop(
            1,
            "rgba(37, 99, 235, 0.18)"
        );

        return gradient;

    }


    /* ==========================================================
       MAIN CHART INITIALISATION
    ========================================================== */

    function initialiseDashboardCharts() {

        if (typeof Chart === "undefined") {

            console.warn(
                "Chart.js is not available on the dashboard."
            );

            return;
        }


        /*
         * IMPORTANT:
         *
         * These IDs intentionally match the Django json_script
         * IDs inside templates/dashboard.html.
         */


        initialiseQuoteChart();

        initialiseBookingChart();

        initialiseRevenueChart();

    }


    /* ==========================================================
       QUOTE CHART
    ========================================================== */

    function initialiseQuoteChart() {

        const canvas =
            document.getElementById("quoteTrendChart");

        if (!canvas) {
            return;
        }


        const labels =
            getJSON("quote-trend-labels");

        const values =
            getJSON("quote-trend-counts");


        new Chart(canvas, {

            type: "line",

            data: {

                labels: labels.length
                    ? labels
                    : ["No data"],

                datasets: [

                    {

                        label: "Quotes",

                        data: values.length
                            ? values
                            : [0],

                        borderColor: "#2563eb",

                        borderWidth: 2.5,

                        tension: 0.4,

                        fill: true,

                        pointRadius: 3,

                        pointHoverRadius: 6,

                        pointBackgroundColor: "#2563eb",

                        backgroundColor: function (context) {

                            const chart =
                                context.chart;

                            const {
                                ctx,
                                chartArea
                            } = chart;

                            if (!chartArea) {

                                return "rgba(37,99,235,.08)";

                            }

                            return createGradient(
                                ctx,
                                chartArea
                            );

                        }

                    }

                ]

            },

            options: chartOptions()

        });

    }


    /* ==========================================================
       BOOKING CHART
    ========================================================== */

    function initialiseBookingChart() {

        const canvas =
            document.getElementById("bookingTrendChart");

        if (!canvas) {
            return;
        }


        const labels =
            getJSON("booking-trend-labels");

        const values =
            getJSON("booking-trend-counts");


        new Chart(canvas, {

            type: "bar",

            data: {

                labels: labels.length
                    ? labels
                    : ["No data"],

                datasets: [

                    {

                        label: "Bookings",

                        data: values.length
                            ? values
                            : [0],

                        backgroundColor:
                            "rgba(37, 99, 235, .85)",

                        borderRadius: 7,

                        borderSkipped: false

                    }

                ]

            },

            options: chartOptions()

        });

    }


    /* ==========================================================
       REVENUE CHART
    ========================================================== */

    function initialiseRevenueChart() {

        const canvas =
            document.getElementById("revenueTrendChart");

        if (!canvas) {
            return;
        }


        const labels =
            getJSON("revenue-trend-labels");

        const values =
            getJSON("revenue-trend-counts");


        const options =
            chartOptions();


        options.scales.y.ticks.callback =
            function (value) {

                return "$" +
                    Number(value || 0)
                        .toLocaleString();

            };


        options.plugins.tooltip.callbacks = {

            label: function (context) {

                return "$" +
                    Number(
                        context.raw || 0
                    ).toLocaleString();

            }

        };


        new Chart(canvas, {

            type: "line",

            data: {

                labels: labels.length
                    ? labels
                    : ["No data"],

                datasets: [

                    {

                        label: "Revenue",

                        data: values.length
                            ? values
                            : [0],

                        borderColor: "#111827",

                        borderWidth: 2.5,

                        tension: 0.4,

                        fill: true,

                        pointRadius: 3,

                        pointHoverRadius: 6,

                        pointBackgroundColor: "#111827",

                        backgroundColor: function (context) {

                            const chart =
                                context.chart;

                            const {
                                ctx,
                                chartArea
                            } = chart;

                            if (!chartArea) {

                                return "rgba(17,24,39,.06)";

                            }

                            const gradient =
                                ctx.createLinearGradient(
                                    0,
                                    chartArea.bottom,
                                    0,
                                    chartArea.top
                                );

                            gradient.addColorStop(
                                0,
                                "rgba(17,24,39,0)"
                            );

                            gradient.addColorStop(
                                1,
                                "rgba(17,24,39,.10)"
                            );

                            return gradient;

                        }

                    }

                ]

            },

            options: options

        });

    }


    /* ==========================================================
       DASHBOARD INTERACTIONS
    ========================================================== */

    function initialiseDashboardInteractions() {

        setupActionCardKeyboard();

        setupTableOverflow();

    }


    /* ==========================================================
       ACTION CARD ACCESSIBILITY
    ========================================================== */

    function setupActionCardKeyboard() {

        const cards =
            document.querySelectorAll(
                ".dashboard-action-card, .dashboard-quick-card"
            );


        cards.forEach(function (card) {

            card.addEventListener(
                "keydown",
                function (event) {

                    if (
                        event.key === "Enter" ||
                        event.key === " "
                    ) {

                        event.preventDefault();

                        card.click();

                    }

                }
            );

        });

    }


    /* ==========================================================
       TABLE OVERFLOW
    ========================================================== */

    function setupTableOverflow() {

        const wrappers =
            document.querySelectorAll(
                ".dashboard-table-wrapper"
            );


        wrappers.forEach(function (wrapper) {

            if (wrapper.scrollWidth > wrapper.clientWidth) {

                wrapper.classList.add(
                    "dashboard-table-scrollable"
                );

            }

        });

    }


})();