document.addEventListener("DOMContentLoaded", function () {
    setupMobileSidebar();
    setupAdvancedTables();
    setupDashboardCharts();
    setupSidebarDropdowns();
    setupActiveSidebarNavigation();
    setupSidebarBadges();
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
        button.setAttribute("aria-label", "Close dashboard menu");
        button.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        button.textContent = "☰";
        button.setAttribute("aria-label", "Open dashboard menu");
        button.setAttribute("aria-expanded", "false");
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
}

function setupSidebarDropdowns() {
    const dropdownButtons = document.querySelectorAll(".sidebar-dropdown-btn");

    dropdownButtons.forEach(function (button) {
        const parent = button.closest(".sidebar-dropdown");
        const submenu = parent && parent.querySelector(".sidebar-submenu");
        if (submenu && !submenu.id) {
            const index = Array.prototype.indexOf.call(
                document.querySelectorAll(".sidebar-submenu"),
                submenu
            );
            submenu.id = "sidebar-submenu-" + (index + 1);
        }
        if (submenu) {
            button.setAttribute("aria-controls", submenu.id);
        }
        if (parent) {
            button.setAttribute("aria-expanded", parent.classList.contains("open") ? "true" : "false");
        }

        button.addEventListener("click", function () {
            if (!parent) {
                return;
            }

            const isOpen = parent.classList.toggle("open");
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    });
}

function setupActiveSidebarNavigation() {
    const rawPath = window.location.pathname.replace(/\/+$/, "") || "/";
    const currentPath = rawPath.replace(/^\/dashboard\/customer\//, "/dashboard/customers/");
    const links = document.querySelectorAll(".crm-sidebar a[href]");
    let activeLink = null;

    links.forEach(function (link) {
        const target = new URL(link.href, window.location.origin);
        const targetPath = target.pathname.replace(/\/+$/, "") || "/";
        const isDashboardHome = targetPath === "/dashboard";
        const isCurrent = isDashboardHome
            ? currentPath === targetPath
            : currentPath === targetPath || currentPath.startsWith(targetPath + "/");

        if (isCurrent && (!activeLink || targetPath.length > new URL(activeLink.href).pathname.length)) {
            activeLink = link;
        }
    });

    if (activeLink) {
        activeLink.setAttribute("aria-current", "page");
        const dropdown = activeLink.closest(".sidebar-dropdown");
        if (dropdown) {
            dropdown.classList.add("open");
            const button = dropdown.querySelector(".sidebar-dropdown-btn");
            if (button) {
                button.setAttribute("aria-expanded", "true");
            }
        }

        function setupSidebarBadges() {
            document.querySelectorAll(".side-badge").forEach(function (badge) {
                if (badge.dataset.notificationType) {
                    return;
                }

                const link = badge.closest("a");
                const label = link ? link.querySelector("span") : null;
                const count = badge.textContent.trim();
                const item = label ? label.textContent.trim() : "dashboard";
                badge.setAttribute("aria-label", count + " items needing attention in " + item);
                badge.title = count + " items needing attention";
            });
        }
    }
}
