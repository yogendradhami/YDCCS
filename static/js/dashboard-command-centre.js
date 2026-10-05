(function () {
    "use strict";

    function getJSON(id) {
        const element = document.getElementById(id);

        if (!element) {
            return [];
        }

        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            console.error(
                "Unable to parse dashboard chart data:",
                id,
                error
            );

            return [];
        }
    }


    function createChart(
        elementId,
        labels,
        values,
        label,
        currency = false
    ) {
        const canvas = document.getElementById(elementId);

        if (!canvas) {
            return;
        }

        if (typeof window.Chart === "undefined") {
            console.warn(
                "Chart.js is not available yet."
            );

            return;
        }

        const context = canvas.getContext("2d");

        if (!context) {
            return;
        }


        const height =
            canvas.parentElement?.clientHeight || 250;


        const gradient = context.createLinearGradient(
            0,
            0,
            0,
            height
        );

        gradient.addColorStop(
            0,
            "rgba(33, 166, 111, 0.20)"
        );

        gradient.addColorStop(
            1,
            "rgba(33, 166, 111, 0)"
        );


        new window.Chart(context, {
            type: "line",

            data: {
                labels: labels,

                datasets: [
                    {
                        label: label,
                        data: values,

                        borderColor: "#21a66f",
                        backgroundColor: gradient,

                        fill: true,

                        borderWidth: 2,

                        tension: 0.38,

                        pointRadius: 3,
                        pointHoverRadius: 5,

                        pointBackgroundColor: "#ffffff",
                        pointBorderColor: "#21a66f",
                        pointBorderWidth: 2
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index"
                },

                animation: {
                    duration: 700,
                    easing: "easeOutQuart"
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        backgroundColor: "#10242b",

                        titleColor: "#ffffff",
                        bodyColor: "rgba(255,255,255,.78)",

                        borderColor:
                            "rgba(255,255,255,.10)",

                        borderWidth: 1,

                        padding: 11,

                        displayColors: false,

                        titleFont: {
                            size: 11,
                            weight: "700"
                        },

                        bodyFont: {
                            size: 11
                        },

                        callbacks: {
                            label: function (context) {
                                const value =
                                    context.parsed.y ?? 0;

                                if (currency) {
                                    return (
                                        label +
                                        ": $" +
                                        Number(value)
                                            .toLocaleString()
                                    );
                                }

                                return (
                                    label +
                                    ": " +
                                    Number(value)
                                        .toLocaleString()
                                );
                            }
                        }
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
                            color: "#8a969f",

                            font: {
                                size: 9
                            },

                            maxRotation: 0
                        }
                    },

                    y: {
                        beginAtZero: true,

                        grid: {
                            color:
                                "rgba(20,33,43,.07)"
                        },

                        border: {
                            display: false
                        },

                        ticks: {
                            color: "#8a969f",

                            font: {
                                size: 9
                            },

                            padding: 7,

                            precision: 0,

                            callback: function (value) {
                                if (currency) {
                                    return (
                                        "$" +
                                        Number(value)
                                            .toLocaleString()
                                    );
                                }

                                return value;
                            }
                        }
                    }
                }
            }
        });
    }


    function initialiseDashboardCharts() {

        createChart(
            "quoteTrendChart",
            getJSON("quote-trend-labels"),
            getJSON("quote-trend-counts"),
            "Quotes"
        );


        createChart(
            "bookingTrendChart",
            getJSON("booking-trend-labels"),
            getJSON("booking-trend-counts"),
            "Bookings"
        );


        createChart(
            "revenueTrendChart",
            getJSON("revenue-trend-labels"),
            getJSON("revenue-trend-counts"),
            "Revenue",
            true
        );
    }


    function waitForChartJS() {

        if (typeof window.Chart !== "undefined") {
            initialiseDashboardCharts();
            return;
        }

        setTimeout(
            waitForChartJS,
            100
        );
    }


    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            waitForChartJS
        );
    } else {
        waitForChartJS();
    }

})();