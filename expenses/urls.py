from django.urls import path

from .views import (
<<<<<<< HEAD
    add_expense,
    delete_expense,
    edit_expense,
    expense_list,
)

urlpatterns = [
    path("dashboard/expenses/", expense_list, name="expense_list"),
    path("dashboard/expenses/add/", add_expense, name="add_expense"),
    path(
        "dashboard/expenses/<int:expense_id>/edit/", edit_expense, name="edit_expense"
    ),
    path(
        "dashboard/expenses/<int:expense_id>/delete/",
        delete_expense,
        name="delete_expense",
    ),
]
=======
    expense_list,
    add_expense,
    edit_expense,
    delete_expense,
)


urlpatterns = [
    path("dashboard/expenses/", expense_list, name="expense_list"),
    path("dashboard/expenses/add/", add_expense, name="add_expense"),
    path("dashboard/expenses/<int:expense_id>/edit/", edit_expense, name="edit_expense"),
    path("dashboard/expenses/<int:expense_id>/delete/", delete_expense, name="delete_expense"),
]
>>>>>>> 5815f15 (Initial project commit)
