document.addEventListener("DOMContentLoaded", function () {
    setupMobileSidebar();
    setupNotifications();
    setupAdvancedTables();
    setupDashboardCharts();
<<<<<<< HEAD
=======
    setupSidebarDropdowns();
>>>>>>> 5815f15 (Initial project commit)
});

function setupMobileSidebar() {
    const button = document.getElementById("crmMenuButton");
    const sidebar = document.getElementById("crmSidebar");
    const overlay = document.getElementById("crmOverlay");

    if (!button || !sidebar || !overlay) {
        return;
    }

    function openMenu() {
        sidebar.classList.add("active");
        overlay.classList.add("active");
        button.textContent = "×";
    }

    function closeMenu() {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        button.textContent = "☰";
    }

    button.addEventListener("click", function () {
        if (sidebar.classList.contains("active")) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    overlay.addEventListener("click", closeMenu);
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

function setupNotifications() {
    const bell = document.getElementById("notificationBell");
    const count = document.getElementById("notificationCount");

    if (!bell) {
        return;
    }

    bell.addEventListener("click", function () {
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
            if (data.success) {
                if (count) {
                    count.textContent = "0";
                    count.style.display = "none";
                }

                document.querySelectorAll(".side-badge").forEach(function (badge) {
                    badge.remove();
                });

                document.querySelectorAll(".notification-dropdown a.unread").forEach(function (item) {
                    item.classList.remove("unread");
                });
            }
        })
        .catch(function () {
            console.log("Notification update failed.");
        });
    });
}

function setupAdvancedTables() {
    const tables = document.querySelectorAll(".advanced-table");

    tables.forEach(function (table) {
        if (table.dataset.enhanced === "true") {
            return;
        }

        table.dataset.enhanced = "true";

        const wrapper = document.createElement("div");
        wrapper.className = "advanced-table-card";

        const toolbar = document.createElement("div");
        toolbar.className = "advanced-table-toolbar";

        const searchInput = document.createElement("input");
        searchInput.type = "text";
        searchInput.placeholder = "Search table...";
        searchInput.className = "advanced-table-search";

        const rowsSelect = document.createElement("select");
        rowsSelect.className = "advanced-table-rows";
        rowsSelect.innerHTML = `
            <option value="5">5 rows</option>
            <option value="10" selected>10 rows</option>
            <option value="20">20 rows</option>
            <option value="50">50 rows</option>
        `;

        toolbar.appendChild(searchInput);
        toolbar.appendChild(rowsSelect);

        const pagination = document.createElement("div");
        pagination.className = "advanced-table-pagination";

        const parent = table.parentNode;
        parent.insertBefore(wrapper, table);
        wrapper.appendChild(toolbar);
        wrapper.appendChild(table);
        wrapper.appendChild(pagination);

        const allRows = Array.from(table.querySelectorAll("tbody tr"));
        let currentPage = 1;

        function renderTable() {
            const rowsPerPage = parseInt(rowsSelect.value);
            const searchValue = searchInput.value.toLowerCase().trim();

            const filteredRows = allRows.filter(function (row) {
                return row.innerText.toLowerCase().includes(searchValue);
            });

            const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));

            if (currentPage > totalPages) {
                currentPage = totalPages;
            }

            allRows.forEach(function (row) {
                row.style.display = "none";
            });

            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;

            filteredRows.slice(start, end).forEach(function (row) {
                row.style.display = "";
            });

            pagination.innerHTML = `
                <span>Showing ${filteredRows.length === 0 ? 0 : start + 1}-${Math.min(end, filteredRows.length)} of ${filteredRows.length}</span>
                <div class="pagination-buttons">
                    <button ${currentPage === 1 ? "disabled" : ""} data-action="prev">Prev</button>
                    <strong>${currentPage} / ${totalPages}</strong>
                    <button ${currentPage === totalPages ? "disabled" : ""} data-action="next">Next</button>
                </div>
            `;

            pagination.querySelectorAll("button").forEach(function (button) {
                button.addEventListener("click", function () {
                    if (this.dataset.action === "prev") {
                        currentPage--;
                    }

                    if (this.dataset.action === "next") {
                        currentPage++;
                    }

                    renderTable();
                });
            });
        }

        searchInput.addEventListener("input", function () {
            currentPage = 1;
            renderTable();
        });

        rowsSelect.addEventListener("change", function () {
            currentPage = 1;
            renderTable();
        });

        renderTable();
    });
}

function getChartData(id) {
    const element = document.getElementById(id);

    if (!element) {
        return [];
    }

    try {
        return JSON.parse(element.textContent);
    } catch (error) {
        return [];
    }
}

function setupDashboardCharts() {
    if (typeof Chart === "undefined") {
        console.log("Chart.js is not loaded.");
        return;
    }

    const quoteCanvas = document.getElementById("quoteTrendChart");
    const bookingCanvas = document.getElementById("bookingTrendChart");
    const revenueCanvas = document.getElementById("revenueTrendChart");

    const quoteLabels = getChartData("quote-trend-labels");
    const quoteCounts = getChartData("quote-trend-counts");

    const bookingLabels = getChartData("booking-trend-labels");
    const bookingCounts = getChartData("booking-trend-counts");

    const revenueLabels = getChartData("revenue-trend-labels");
    const revenueCounts = getChartData("revenue-trend-counts");

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        }
    };

    if (quoteCanvas) {
        new Chart(quoteCanvas, {
            type: "line",
            data: {
                labels: quoteLabels.length ? quoteLabels : ["No Data"],
                datasets: [{
                    label: "Quotes",
                    data: quoteCounts.length ? quoteCounts : [0],
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                }]
            },
            options: options
        });
    }

    if (bookingCanvas) {
        new Chart(bookingCanvas, {
            type: "bar",
            data: {
                labels: bookingLabels.length ? bookingLabels : ["No Data"],
                datasets: [{
                    label: "Bookings",
                    data: bookingCounts.length ? bookingCounts : [0],
                    borderWidth: 1
                }]
            },
            options: options
        });
    }

    if (revenueCanvas) {
        new Chart(revenueCanvas, {
            type: "line",
            data: {
                labels: revenueLabels.length ? revenueLabels : ["No Data"],
                datasets: [{
                    label: "Revenue",
                    data: revenueCounts.length ? revenueCounts : [0],
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                }]
            },
            options: options
        });
    }
<<<<<<< HEAD
}
=======
}
function setupSidebarDropdowns() {
    const dropdownButtons = document.querySelectorAll(".sidebar-dropdown-btn");

    dropdownButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const parent = button.closest(".sidebar-dropdown");

            if (!parent) {
                return;
            }

            parent.classList.toggle("open");
        });
    });
}
>>>>>>> 5815f15 (Initial project commit)
