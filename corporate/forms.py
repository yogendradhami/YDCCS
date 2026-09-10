from django import forms
from django.utils import timezone

from .models import CorporateLead


class CorporateLeadBaseForm(forms.ModelForm):
    """
    Shared form foundation for all corporate enquiries.
    """

    class Meta:
        model = CorporateLead
        fields = [
            "full_name",
            "job_title",
            "company_name",
            "email",
            "phone",
            "industry",
            "number_of_sites",
            "service_locations",
            "facility_size",
            "services_required",
            "frequency",
            "preferred_start_date",
            "current_cleaning_provider",
            "location_coverage",
            "centralised_invoicing",
            "reporting_requirements",
            "access_requirements",
            "message",
            "consent",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full name *",
                    "autocomplete": "name",
                }
            ),
            "job_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Job title",
                    "autocomplete": "organization-title",
                }
            ),
            "company_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Company / organisation",
                    "autocomplete": "organization",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Business email *",
                    "autocomplete": "email",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Business phone",
                    "autocomplete": "tel",
                }
            ),
            "industry": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "number_of_sites": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Number of sites",
                    "min": "1",
                }
            ),
            "service_locations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Suburbs, cities or locations requiring service",
                    "rows": 3,
                }
            ),
            "facility_size": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Approximate facility size",
                }
            ),
            "services_required": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "What cleaning services do you require?",
                    "rows": 4,
                }
            ),
            "frequency": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "preferred_start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "current_cleaning_provider": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Current cleaning provider (optional)",
                }
            ),
            "location_coverage": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe the locations or geographic coverage required",
                    "rows": 3,
                }
            ),
            "centralised_invoicing": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "reporting_requirements": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Reporting, compliance or service documentation requirements",
                    "rows": 3,
                }
            ),
            "access_requirements": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Building access, keys, security or access-control requirements",
                    "rows": 3,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tell us about your cleaning requirements",
                    "rows": 5,
                }
            ),
            "consent": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["full_name"].label = "Full name"
        self.fields["job_title"].label = "Job title"
        self.fields["company_name"].label = "Company / Organisation"
        self.fields["email"].label = "Business email"
        self.fields["phone"].label = "Business phone"
        self.fields["industry"].label = "Business / Industry"
        self.fields["number_of_sites"].label = "Number of sites"
        self.fields["service_locations"].label = "Service locations"
        self.fields["facility_size"].label = "Approximate facility size"
        self.fields["services_required"].label = "Services required"
        self.fields["frequency"].label = "Cleaning frequency"
        self.fields["preferred_start_date"].label = "Preferred start date"
        self.fields["current_cleaning_provider"].label = (
            "Current cleaning provider"
        )
        self.fields["location_coverage"].label = "Location coverage"
        self.fields["centralised_invoicing"].label = (
            "Centralised invoicing"
        )
        self.fields["reporting_requirements"].label = (
            "Reporting requirements"
        )
        self.fields["access_requirements"].label = (
            "Access requirements"
        )
        self.fields["message"].label = "Additional requirements"
        self.fields["consent"].label = (
            "I agree to be contacted regarding this enquiry."
        )

        # Only the fields that are generally essential.
        self.fields["full_name"].required = True
        self.fields["email"].required = True
        self.fields["consent"].required = True

    def clean_preferred_start_date(self):
        date = self.cleaned_data.get("preferred_start_date")

        if date and date < timezone.localdate():
            raise forms.ValidationError(
                "Please select today or a future date."
            )

        return date

    def clean_number_of_sites(self):
        number = self.cleaned_data.get("number_of_sites")

        if number is not None and number < 1:
            raise forms.ValidationError(
                "Number of sites must be at least 1."
            )

        return number

    def clean_consent(self):
        consent = self.cleaned_data.get("consent")

        if not consent:
            raise forms.ValidationError(
                "Please confirm that you agree to be contacted."
            )

        return consent


class CorporateProposalForm(CorporateLeadBaseForm):
    """
    Form submitted from 'Request a Corporate Proposal'.
    """

    def save(self, commit=True):
        lead = super().save(commit=False)

        lead.lead_type = "proposal"
        lead.lead_source = "corporate_proposal"

        if commit:
            lead.save()

        return lead


class CorporateTeamContactForm(CorporateLeadBaseForm):
    """
    Form submitted from 'Speak With Our Team'.
    """

    def save(self, commit=True):
        lead = super().save(commit=False)

        lead.lead_type = "team_contact"
        lead.lead_source = "corporate_team_contact"

        if commit:
            lead.save()

        return lead


class CorporateMultiSiteForm(CorporateLeadBaseForm):
    """
    Form submitted from 'Discuss Multi-Site Cleaning'.
    """

    def save(self, commit=True):
        lead = super().save(commit=False)

        lead.lead_type = "multi_site"
        lead.lead_source = "corporate_multi_site"

        if commit:
            lead.save()

        return lead