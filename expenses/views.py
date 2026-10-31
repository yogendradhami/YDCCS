from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import ExpenseForm
from .models import Expense


@login_required
def expense_list(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    all_expenses = Expense.objects.select_related(
        "paid_by",
        "supplier",
        "invoice_review__document",
    ).all()
    expenses = all_expenses
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    date_from_value = request.GET.get("date_from", "").strip()
    date_to_value = request.GET.get("date_to", "").strip()

    total_expenses = all_expenses.aggregate(total=Sum("amount"))["total"] or 0

    month_expenses = (
        all_expenses.filter(
            date__gte=month_start,
            date__lte=today,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    if query:
        expenses = expenses.filter(
            Q(description__icontains=query)
            | Q(invoice_number__icontains=query)
            | Q(supplier__name__icontains=query)
        )
    if category in dict(Expense.CATEGORY_CHOICES):
        expenses = expenses.filter(category=category)
    else:
        category = ""
    date_from = parse_date(date_from_value) if date_from_value else None
    date_to = parse_date(date_to_value) if date_to_value else None
    filter_error = ""
    if date_from_value and not date_from:
        filter_error = "Enter a valid start date."
        date_from_value = ""
    if date_to_value and not date_to:
        filter_error = "Enter a valid end date."
        date_to_value = ""
    if date_from and date_to and date_from > date_to:
        filter_error = "The start date must be on or before the end date."
    else:
        if date_from:
            expenses = expenses.filter(date__gte=date_from)
        if date_to:
            expenses = expenses.filter(date__lte=date_to)

    paginator = Paginator(expenses, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "expenses/expense_list.html",
        {
            "expenses": page_obj.object_list,
            "page_obj": page_obj,
            "category_choices": Expense.CATEGORY_CHOICES,
            "total_expenses": total_expenses,
            "month_expenses": month_expenses,
            "today": today,
            "filtered_total": expenses.aggregate(total=Sum("amount"))["total"] or 0,
            "query": query,
            "category": category,
            "date_from": date_from_value,
            "date_to": date_to_value,
            "filter_error": filter_error,
        },
    )


@login_required
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)

        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.recorded_by = request.user
            expense.save()

            messages.success(request, "✅ Expense added successfully.")
            return redirect("expense_list")

        messages.error(request, "❌ Please check the expense form.")
    else:
        form = ExpenseForm()

    return render(
        request,
        "expenses/expense_form.html",
        {
            "form": form,
            "page_title": "Add Expense",
            "button_text": "Save Expense",
            "expense": None,
        },
    )


@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES, instance=expense)

        if form.is_valid():
            previous_payment_status = expense.payment_status
            form.save()
            if expense.payment_status != previous_payment_status:
                from dashboard.operations_automation import record_operations_event

                record_operations_event(
                    module="Finance",
                    event=f"Expense #{expense.pk} payment status confirmed",
                    trigger="Authorised user changed the payment status.",
                    action_taken=(
                        f"Payment status changed from {previous_payment_status} "
                        f"to {expense.payment_status}."
                    ),
                    actor=request.user,
                    metadata={
                        "expense_id": expense.pk,
                        "old_payment_status": previous_payment_status,
                        "payment_status": expense.payment_status,
                    },
                )
            messages.success(request, "✅ Expense updated successfully.")
            return redirect("expense_list")

        messages.error(request, "❌ Please check the expense form.")
    else:
        form = ExpenseForm(instance=expense)

    return render(
        request,
        "expenses/expense_form.html",
        {
            "form": form,
            "page_title": "Edit Expense",
            "button_text": "Update Expense",
            "expense": expense,
        },
    )


@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if expense.invoice_review_id:
        messages.error(
            request,
            "This expense is linked to a supplier invoice and is retained for audit.",
        )
        return redirect("expense_list")

    if request.method == "POST":
        expense.delete()
        messages.success(request, "✅ Expense deleted successfully.")
        return redirect("expense_list")

    return render(
        request,
        "expenses/expense_confirm_delete.html",
        {
            "object_name": str(expense),
            "cancel_url": "/dashboard/expenses/",
        },
    )
