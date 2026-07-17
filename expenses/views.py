<<<<<<< HEAD
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ExpenseForm
from .models import Expense
=======
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from .models import Expense
from .forms import ExpenseForm
>>>>>>> 5815f15 (Initial project commit)


@login_required
def expense_list(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

<<<<<<< HEAD
    expenses = Expense.objects.select_related("paid_by").all()

    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or 0

    month_expenses = (
        expenses.filter(date__gte=month_start).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    return render(
        request,
        "expense_list.html",
        {
            "expenses": expenses,
            "total_expenses": total_expenses,
            "month_expenses": month_expenses,
        },
    )
=======
    expenses = Expense.objects.select_related(
        "paid_by"
    ).all()

    total_expenses = expenses.aggregate(
        total=Sum("amount")
    )["total"] or 0

    month_expenses = expenses.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    return render(request, "expenses/expense_list.html", {
        "expenses": expenses,
        "total_expenses": total_expenses,
        "month_expenses": month_expenses,
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)

        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.save()

            messages.success(request, "✅ Expense added successfully.")
            return redirect("expense_list")

        messages.error(request, "❌ Please check the expense form.")
    else:
        form = ExpenseForm()

<<<<<<< HEAD
    return render(
        request,
        "expense_form.html",
        {
            "form": form,
            "page_title": "Add Expense",
            "button_text": "Save Expense",
        },
    )
=======
    return render(request, "expenses/expense_form.html", {
        "form": form,
        "page_title": "Add Expense",
        "button_text": "Save Expense",
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES, instance=expense)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Expense updated successfully.")
            return redirect("expense_list")

        messages.error(request, "❌ Please check the expense form.")
    else:
        form = ExpenseForm(instance=expense)

<<<<<<< HEAD
    return render(
        request,
        "expense_form.html",
        {
            "form": form,
            "page_title": "Edit Expense",
            "button_text": "Update Expense",
        },
    )
=======
    return render(request, "expenses/expense_form.html", {
        "form": form,
        "page_title": "Edit Expense",
        "button_text": "Update Expense",
    })
>>>>>>> 5815f15 (Initial project commit)


@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "✅ Expense deleted successfully.")
        return redirect("expense_list")

<<<<<<< HEAD
    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": str(expense),
            "cancel_url": "/dashboard/expenses/",
        },
    )
=======
    return render(request, "shared/confirm_delete.html", {
        "object_name": str(expense),
        "cancel_url": "/dashboard/expenses/",
    })
>>>>>>> 5815f15 (Initial project commit)
