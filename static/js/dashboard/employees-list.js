(function () {
    "use strict";

    const rows = [...document.querySelectorAll("#employeeRows tr[data-search]")];
    const search = document.getElementById("employeeSearch");
    const role = document.getElementById("employeeRoleFilter");
    const status = document.getElementById("employeeStatusFilter");
    const noResults = document.getElementById("employeeNoResults");
    const clear = document.getElementById("clearEmployeeFilters");
    if (!rows.length && !search) return;

    function applyFilters() {
        const query = (search?.value || "").trim().toLocaleLowerCase();
        const selectedRole = role?.value || "";
        const selectedStatus = status?.value || "";
        let visibleCount = 0;

        rows.forEach((row) => {
            const matches = row.dataset.search.includes(query)
                && (!selectedRole || row.dataset.role === selectedRole)
                && (!selectedStatus || row.dataset.status === selectedStatus);
            row.hidden = !matches;
            if (matches) visibleCount += 1;
        });
        if (noResults) noResults.hidden = visibleCount !== 0;
    }

    [search, role, status].forEach((control) => {
        control?.addEventListener("input", applyFilters);
        control?.addEventListener("change", applyFilters);
    });

    clear?.addEventListener("click", () => {
        if (search) search.value = "";
        if (role) role.value = "";
        if (status) status.value = "";
        applyFilters();
        search?.focus();
    });

    document.querySelectorAll("[data-delete-employee]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const employeeName = form.dataset.deleteEmployee;
            if (!window.confirm(`Delete ${employeeName}'s employee profile? This cannot be undone.`)) {
                event.preventDefault();
            }
        });
    });
})();