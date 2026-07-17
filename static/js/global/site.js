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
            publicMenu.classList.toggle("active");
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
});

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
