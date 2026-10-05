from django import forms
from django.conf import settings

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