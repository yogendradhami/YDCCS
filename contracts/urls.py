from django.urls import path

from .views import (
<<<<<<< HEAD
    add_contract,
    contract_detail,
    contract_list,
    contract_renewals,
    delete_contract,
    edit_contract,
    generate_contract_bookings,
    send_contract_renewal_email,
)

urlpatterns = [
    path("dashboard/contracts/", contract_list, name="contract_list"),
    path("dashboard/contracts/add/", add_contract, name="add_contract"),
    path(
        "dashboard/contracts/<int:contract_id>/",
        contract_detail,
        name="contract_detail",
    ),
    path(
        "dashboard/contracts/<int:contract_id>/edit/",
        edit_contract,
        name="edit_contract",
    ),
    path(
        "dashboard/contracts/<int:contract_id>/delete/",
        delete_contract,
        name="delete_contract",
    ),
    path(
        "dashboard/contracts/<int:contract_id>/generate-bookings/",
        generate_contract_bookings,
        name="generate_contract_bookings",
    ),
    path(
        "<int:contract_id>/generate-bookings/",
        generate_contract_bookings,
        name="generate_contract_bookings",
    ),
    path("dashboard/contracts/renewals/", contract_renewals, name="contract_renewals"),
    path(
        "dashboard/contracts/<int:contract_id>/renewal-email/",
        send_contract_renewal_email,
        name="send_contract_renewal_email",
    ),
]
=======
    contract_list,
    add_contract,
    edit_contract,
    delete_contract,
    contract_detail,
    generate_contract_bookings,
    contract_renewals,
    send_contract_renewal_email,
)


urlpatterns = [
    path("dashboard/contracts/", contract_list, name="contract_list"),
    path("dashboard/contracts/add/", add_contract, name="add_contract"),
    path("dashboard/contracts/<int:contract_id>/", contract_detail, name="contract_detail"),
    path("dashboard/contracts/<int:contract_id>/edit/", edit_contract, name="edit_contract"),
    path("dashboard/contracts/<int:contract_id>/delete/", delete_contract, name="delete_contract"),
    path("dashboard/contracts/<int:contract_id>/generate-bookings/", generate_contract_bookings, name="generate_contract_bookings"),
    path("<int:contract_id>/generate-bookings/",generate_contract_bookings,name="generate_contract_bookings"),

    path("dashboard/contracts/renewals/",contract_renewals,name="contract_renewals"),
    path("dashboard/contracts/<int:contract_id>/renewal-email/",send_contract_renewal_email,name="send_contract_renewal_email"),
]
>>>>>>> 5815f15 (Initial project commit)
