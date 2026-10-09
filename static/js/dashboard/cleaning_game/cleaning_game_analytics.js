
/**
 * YD Commercial Cleaning
 * Cleaning Challenge Analytics Dashboard
 *
 * Features:
 * - Search recent activity
 * - Pagination for the activity table
 * - Page-size selection
 * - Previous / next navigation
 * - Responsive controls
 * - Accessible status announcements
 *
 * This file does not fetch or calculate database analytics.
 * Those values must be supplied by the Django view.
 */

(function () {
    "use strict";

    const page = document.querySelector(".cga-page");

    if (!page) return;

    const table = page.querySelector(".cga-table");
    const tableWrap = page.querySelector(".cga-table-wrap");
    const tableFooter = page.querySelector(".cga-table-footer");

    if (!table || !tableWrap || !table.tBodies.length) return;

    const tbody = table.tBodies[0];
    const allRows = Array.from(tbody.rows);

    // Avoid duplicating controls if the script is initialized twice.
    if (page.querySelector(".cga-table-controls")) return;

    const emptyStateRow =
        allRows.length === 1 &&
        allRows[0].cells.length === 1 &&
        allRows[0].cells[0].colSpan > 1;

    const dataRows = emptyStateRow ? [] : allRows;

    let filteredRows = [...dataRows];
    let currentPage = 1;
    let pageSize = 10;
    let searchTerm = "";

    const controls = document.createElement("div");
    controls.className = "cga-table-controls";

    controls.innerHTML = `
        <div class="cga-table-search">
            <label for="cgaActivitySearch">Search activity</label>
            <input
                id="cgaActivitySearch"
                type="search"
                placeholder="Search events, scores, performance..."
                autocomplete="off"
            >
        </div>

        <div class="cga-table-page-size">
            <label for="cgaPageSize">Rows per page</label>
            <select id="cgaPageSize">
                <option value="5">5</option>
                <option value="10" selected>10</option>
                <option value="25">25</option>
                <option value="50">50</option>
            </select>
        </div>
    `;

    tableWrap.parentNode.insertBefore(controls, tableWrap);

    const searchInput = controls.querySelector("#cgaActivitySearch");
    const pageSizeSelect = controls.querySelector("#cgaPageSize");

    const pagination = document.createElement("nav");
    pagination.className = "cga-pagination";
    pagination.setAttribute("aria-label", "Activity table pagination");

    pagination.innerHTML = `
        <span class="cga-pagination-summary" aria-live="polite"></span>

        <div class="cga-pagination-actions">
            <button type="button" class="cga-page-button cga-previous">
                Previous
            </button>

            <span class="cga-page-indicator" aria-live="polite"></span>

            <button type="button" class="cga-page-button cga-next">
                Next
            </button>
        </div>
    `;

    if (tableFooter) {
        tableFooter.insertAdjacentElement("afterend", pagination);
    } else {
        tableWrap.insertAdjacentElement("afterend", pagination);
    }

    const summary = pagination.querySelector(".cga-pagination-summary");
    const previousButton = pagination.querySelector(".cga-previous");
    const nextButton = pagination.querySelector(".cga-next");
    const pageIndicator = pagination.querySelector(".cga-page-indicator");

    function getTotalPages() {
        return Math.max(1, Math.ceil(filteredRows.length / pageSize));
    }

    function updateFooter(start, end) {
        if (!tableFooter) return;

        const footerItems = tableFooter.querySelectorAll("span");

        if (footerItems.length >= 2) {
            footerItems[0].textContent =
                filteredRows.length > 0
                    ? `Showing ${start}–${end} of ${filteredRows.length} events`
                    : "No matching events";

            footerItems[1].textContent =
                `${dataRows.length} total recorded rows`;
        }
    }

    function renderTable() {
        const totalPages = getTotalPages();

        currentPage = Math.min(Math.max(currentPage, 1), totalPages);

        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(
            startIndex + pageSize,
            filteredRows.length
        );

        const visibleRows = filteredRows.slice(startIndex, endIndex);

        // Hide all data rows before displaying the current page.
        dataRows.forEach((row) => {
            row.hidden = true;
        });

        if (emptyStateRow) {
            allRows[0].hidden = true;
        }

        visibleRows.forEach((row) => {
            row.hidden = false;
        });

        // If there are no matches, show a dedicated empty state.
        let noResultsRow = tbody.querySelector(".cga-no-results");

        if (filteredRows.length === 0) {
            if (!noResultsRow) {
                noResultsRow = document.createElement("tr");
                noResultsRow.className = "cga-no-results";

                const cell = document.createElement("td");
                cell.colSpan = table.rows[0]
                    ? table.rows[0].cells.length
                    : 5;

                const message = document.createElement("div");
                message.className = "cga-empty-state";

                const heading = document.createElement("strong");
                heading.textContent = "No matching activity";

                const description = document.createElement("p");
                description.textContent =
                    "Try another search term or clear the search field.";

                message.append(heading, description);
                cell.appendChild(message);
                noResultsRow.appendChild(cell);
                tbody.appendChild(noResultsRow);
            }

            noResultsRow.hidden = false;
        } else if (noResultsRow) {
            noResultsRow.hidden = true;
        }

        if (summary) {
            summary.textContent =
                filteredRows.length > 0
                    ? `Showing ${startIndex + 1}–${endIndex} of ${filteredRows.length}`
                    : "0 results";
        }

        if (pageIndicator) {
            pageIndicator.textContent =
                `Page ${currentPage} of ${totalPages}`;
        }

        previousButton.disabled = currentPage <= 1;
        nextButton.disabled = currentPage >= totalPages;

        pagination.hidden = filteredRows.length === 0;

        updateFooter(
            filteredRows.length > 0 ? startIndex + 1 : 0,
            endIndex
        );
    }

    function applySearch() {
        searchTerm = searchInput.value.trim().toLowerCase();

        filteredRows = dataRows.filter((row) => {
            return row.textContent.toLowerCase().includes(searchTerm);
        });

        currentPage = 1;
        renderTable();
    }

    searchInput.addEventListener("input", applySearch);

    pageSizeSelect.addEventListener("change", () => {
        pageSize = Number(pageSizeSelect.value) || 10;
        currentPage = 1;
        renderTable();
    });

    previousButton.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage -= 1;
            renderTable();
        }
    });

    nextButton.addEventListener("click", () => {
        if (currentPage < getTotalPages()) {
            currentPage += 1;
            renderTable();
        }
    });

    // Optional refresh timestamp in the footer.
    if (tableFooter) {
        const refreshLabel = document.createElement("span");
        refreshLabel.className = "cga-refresh-label";
        refreshLabel.textContent =
            `Page loaded ${new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit"
            })}`;

        tableFooter.appendChild(refreshLabel);
    }

    renderTable();
})();
