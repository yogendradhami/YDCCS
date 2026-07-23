from django.urls import path

from .views import (
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
