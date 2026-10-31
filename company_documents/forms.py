import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from company_documents.services.invoice_review import is_valid_abn
from dashboard.models import PurchaseOrder
from expenses.models import Expense
from .models import CompanyDocument

from employees.models import Employee
from customers.models import Customer
from dashboard.models import Vehicle, Supplier
from contracts.models import CleaningContract


class CompanyDocumentForm(forms.ModelForm):
    """
    Create and edit company documents.

    On CREATE:
        - A file is required.

    On EDIT:
        - The existing file can remain unchanged.
        - A new file can optionally replace the existing file.
    """

    class Meta:
        model = CompanyDocument

        fields = [
            "name",
            "category",
            "document_type",
            "description",
            "document_reference",
            "related_type",
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
            "issue_date",
            "expiry_date",
            "review_date",
            "is_sensitive",
            "file",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Public Liability Insurance",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "document_type": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Insurance Certificate",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add a description or notes about this document...",
                }
            ),

            "document_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. POL-2026-001",
                }
            ),

            "related_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "employee": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "customer": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "vehicle": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "supplier": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "contract": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "issue_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "review_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "is_sensitive": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,"
                        ".csv,.txt,.zip,.rar,.jpg,.jpeg,.png,.webp"
                    ),
                }
            ),
        }

        labels = {
            "name": "Document name",
            "category": "Category",
            "document_type": "Document type",
            "description": "Description",
            "document_reference": "Document reference",
            "related_type": "Related to",
            "employee": "Employee",
            "customer": "Customer",
            "vehicle": "Vehicle",
            "supplier": "Supplier",
            "contract": "Contract",
            "issue_date": "Issue date",
            "expiry_date": "Expiry date",
            "review_date": "Review date",
            "is_sensitive": "Sensitive document",
            "file": "Document file",
        }

        help_texts = {
            "file": (
                "Maximum file size: 50 MB. "
                "Leave blank when editing to keep the existing document."
            ),
            "is_sensitive": (
                "Sensitive documents require additional permission to download."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---------------------------------------------------------
        # Querysets
        # ---------------------------------------------------------

        self.fields["employee"].queryset = (
            Employee.objects
            .filter(active=True)
            .order_by("full_name")
        )

        self.fields["customer"].queryset = (
            Customer.objects
            .order_by("full_name")
        )

        self.fields["vehicle"].queryset = (
            Vehicle.objects
            .order_by("vehicle_name")
        )

        self.fields["supplier"].queryset = (
            Supplier.objects
            .filter(active=True)
            .order_by("name")
        )

        self.fields["contract"].queryset = (
            CleaningContract.objects
            .select_related("customer")
            .order_by(
                "customer__full_name",
                "service_type",
            )
        )

        # ---------------------------------------------------------
        # Empty relationship fields
        # ---------------------------------------------------------

        self.fields["employee"].required = False
        self.fields["customer"].required = False
        self.fields["vehicle"].required = False
        self.fields["supplier"].required = False
        self.fields["contract"].required = False

        # ---------------------------------------------------------
        # File behaviour
        #
        # IMPORTANT:
        # The file is optional here because the edit view may
        # retain the existing file.
        # ---------------------------------------------------------

        self.fields["file"].required = False

        # ---------------------------------------------------------
        # Show current file information during editing
        # ---------------------------------------------------------

        if self.instance and self.instance.pk:
            self.fields["file"].help_text = (
                "Leave this blank to keep the existing file. "
                "Upload a new file only if you want to replace it. "
                "Maximum file size: 50 MB."
            )

    # =============================================================
    # FILE VALIDATION
    # =============================================================

    def clean_file(self):
        """
        Validate an uploaded company document.

        The file is optional when editing an existing document.

        Handles all of these cases safely:
        - No file submitted
        - Empty file field
        - Uploaded file with no size value
        - Normal uploaded file
        - File larger than the configured maximum
        """

        uploaded_file = self.cleaned_data.get("file")

        # ---------------------------------------------------------
        # No file selected
        # ---------------------------------------------------------
        if not uploaded_file:
            return None

        # ---------------------------------------------------------
        # Safely obtain the uploaded file size.
        #
        # Some empty/optional file submissions can result in
        # uploaded_file.size being None.
        # ---------------------------------------------------------
        file_size = getattr(uploaded_file, "size", None)

        # ---------------------------------------------------------
        # If Django did not provide a size, don't compare None
        # with an integer.
        #
        # The actual file handling/upload process will deal with
        # the file later.
        # ---------------------------------------------------------
        if file_size is None:
            return uploaded_file

        # ---------------------------------------------------------
        # Maximum allowed size
        # ---------------------------------------------------------
        max_size = getattr(
            settings,
            "COMPANY_DOCUMENT_MAX_SIZE",
            50 * 1024 * 1024,
        )

        # ---------------------------------------------------------
        # Size validation
        # ---------------------------------------------------------
        if file_size > max_size:
            raise forms.ValidationError(
                "The selected file is larger than the "
                "maximum allowed size of 50 MB."
            )

        return uploaded_file

    # =============================================================
    # FORM VALIDATION
    # =============================================================

    def clean(self):
        cleaned_data = super().clean()

        related_type = cleaned_data.get("related_type")

        employee = cleaned_data.get("employee")
        customer = cleaned_data.get("customer")
        vehicle = cleaned_data.get("vehicle")
        supplier = cleaned_data.get("supplier")
        contract = cleaned_data.get("contract")

        # ---------------------------------------------------------
        # Clear unrelated relationships.
        #
        # This prevents a document from accidentally being linked
        # to multiple unrelated records.
        # ---------------------------------------------------------

        if related_type != "employee":
            cleaned_data["employee"] = None

        if related_type != "customer":
            cleaned_data["customer"] = None

        if related_type != "vehicle":
            cleaned_data["vehicle"] = None

        if related_type != "supplier":
            cleaned_data["supplier"] = None

        if related_type != "contract":
            cleaned_data["contract"] = None

        # ---------------------------------------------------------
        # Validate required relationship
        # ---------------------------------------------------------

        if related_type == "employee" and not employee:
            self.add_error(
                "employee",
                "Please select the employee this document belongs to.",
            )

        elif related_type == "customer" and not customer:
            self.add_error(
                "customer",
                "Please select the customer this document belongs to.",
            )

        elif related_type == "vehicle" and not vehicle:
            self.add_error(
                "vehicle",
                "Please select the vehicle this document belongs to.",
            )

        elif related_type == "supplier" and not supplier:
            self.add_error(
                "supplier",
                "Please select the supplier this document belongs to.",
            )

        elif related_type == "contract" and not contract:
            self.add_error(
                "contract",
                "Please select the contract this document belongs to.",
            )

        # ---------------------------------------------------------
        # Date validation
        # ---------------------------------------------------------

        issue_date = cleaned_data.get("issue_date")
        expiry_date = cleaned_data.get("expiry_date")
        review_date = cleaned_data.get("review_date")

        if issue_date and expiry_date:
            if expiry_date < issue_date:
                self.add_error(
                    "expiry_date",
                    "Expiry date cannot be earlier than the issue date.",
                )

        if issue_date and review_date:
            if review_date < issue_date:
                self.add_error(
                    "review_date",
                    "Review date cannot be earlier than the issue date.",
                )

        return cleaned_data


class InvoiceReviewVerificationForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.none(),
        required=True,
    )
    supplier_name = forms.CharField(max_length=200)
    abn = forms.CharField(max_length=11, required=False)
    invoice_number = forms.CharField(max_length=150)
    invoice_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    description = forms.CharField(max_length=255)
    line_items_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "spellcheck": "false"}),
    )
    subtotal = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    gst = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        label="GST",
    )
    total = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(active=True).order_by(
            "name"
        )

    def clean_abn(self):
        value = "".join(character for character in self.cleaned_data["abn"] if character.isdigit())
        if value and not is_valid_abn(value):
            raise ValidationError("Enter a valid 11-digit Australian Business Number.")
        return value

    def clean_line_items_json(self):
        raw = self.cleaned_data.get("line_items_json", "").strip()
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Line items must be valid JSON.") from exc
        if not isinstance(items, list) or len(items) > 100:
            raise ValidationError("Provide no more than 100 line items.")

        cleaned_items = []
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError("Each line item must be an object.")
            description = str(item.get("description", "")).strip()
            if not description or len(description) > 255:
                raise ValidationError("Each line item needs a short description.")
            try:
                quantity = Decimal(str(item.get("quantity", "")))
                unit_price = Decimal(str(item.get("unit_price", "")))
                line_total = (
                    Decimal(str(item["line_total"]))
                    if item.get("line_total") not in (None, "")
                    else quantity * unit_price
                )
            except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
                raise ValidationError(
                    "Line item quantities and prices must be valid numbers."
                ) from exc
            if quantity <= 0 or unit_price < 0 or line_total < 0:
                raise ValidationError("Line item quantities and prices cannot be negative.")
            cleaned_items.append(
                {
                    "description": description,
                    "quantity": str(quantity),
                    "unit_price": str(unit_price.quantize(Decimal("0.01"))),
                    "line_total": str(line_total.quantize(Decimal("0.01"))),
                }
            )
        return cleaned_items

    def clean(self):
        cleaned = super().clean()
        invoice_date = cleaned.get("invoice_date")
        due_date = cleaned.get("due_date")
        if invoice_date and due_date and due_date < invoice_date:
            self.add_error("due_date", "Due date cannot be earlier than invoice date.")
        subtotal = cleaned.get("subtotal")
        gst = cleaned.get("gst")
        total = cleaned.get("total")
        if subtotal is not None and gst is not None and total is not None:
            if abs(subtotal + gst - total) > Decimal("0.02"):
                self.add_error(
                    "total",
                    "Subtotal plus GST must match the invoice total.",
                )
        return cleaned


class InvoiceReviewRejectionForm(forms.Form):
    review_notes = forms.CharField(
        min_length=3,
        max_length=2000,
        label="Reason for rejection",
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class InvoicePostingForm(forms.Form):
    category = forms.ChoiceField(
        choices=Expense.CATEGORY_CHOICES,
        label="Expense category",
    )
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.none(),
        required=False,
        label="Matching purchase order",
        empty_label="No purchase order",
    )

    def __init__(
        self,
        *args,
        supplier=None,
        suggested_purchase_order=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.supplier = supplier
        orders = PurchaseOrder.objects.exclude(status="cancelled")
        if supplier:
            orders = orders.filter(supplier_name__iexact=supplier.name)
        else:
            orders = orders.none()
        self.fields["purchase_order"].queryset = orders.select_related(
            "supply"
        ).order_by("-order_date", "-pk")
        if suggested_purchase_order:
            self.initial.setdefault("purchase_order", suggested_purchase_order.pk)

    def clean_purchase_order(self):
        order = self.cleaned_data.get("purchase_order")
        if (
            order
            and self.supplier
            and order.supplier_name.strip().casefold()
            != self.supplier.name.strip().casefold()
        ):
            raise ValidationError(
                "The purchase order supplier must match the verified supplier."
            )
        return order