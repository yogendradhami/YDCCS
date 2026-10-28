# core/middleware.py

import logging
import time

from django.contrib import messages
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django.http import Http404
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

logger = logging.getLogger(__name__)


DASHBOARD_PERMISSION_SECTIONS = {
    "/dashboard/users/positions/create/": "security.manage_security_roles",
    "/dashboard/users/positions/": "security.manage_users",
    "/dashboard/users/": "security.manage_users",
    "/dashboard/security/findings/": (("security_monitor", "securityfinding"),),
    "/dashboard/security/audit/run/": (("security_monitor", "securityfinding"),),
    "/dashboard/security/audit/": "security.view_security_center",
    "/dashboard/security/": (("security_monitor", "securityfinding"), ("security_monitor", "securityalertdelivery")),
    "/dashboard/company-documents/bulk-import/item/": (
        ("company_documents", "bulkimportitem"),
    ),
    "/dashboard/company-documents/bulk-import/": (
        ("company_documents", "bulkimportbatch"),
    ),
    "/dashboard/company-documents/": (
        ("company_documents", "companydocument"),
    ),
    "/dashboard/support/live-chat/": (("support", "livechatconversation"),),
    "/dashboard/support/chat-counts/": (("support", "livechatconversation"),),
    "/dashboard/support/tickets/": (("support", "supportticket"),),
    "/dashboard/support/": (("support", "chatenquiry"),),
    "/dashboard/leads/": (("quotes", "quoterequest"),),
    "/dashboard/quote-requests/": (("quotes", "quoterequest"),),
    "/dashboard/quote-followups/": (("quotes", "quoterequest"),),
    "/dashboard/quote-conversion-analytics/": (("quotes", "quoterequest"),),
    "/dashboard/ai-quote-estimator/": (("invoices", "invoice"),),
    "/dashboard/update-status/": (("quotes", "quoterequest"),),
    "/dashboard/export-quotes/": (("quotes", "quoterequest"),),
    "/dashboard/quotes/convert/": (("quotes", "quoterequest"),),
    "/dashboard/corporate-leads/": (("corporate", "corporatelead"),),
    "/dashboard/customers/": (("customers", "customer"),),
    "/dashboard/customer/": (("customers", "customer"),),
    "/dashboard/customer-analytics/": (("customers", "customer"),),
    "/dashboard/customer-loyalty/": (("customers", "customer"),),
    "/dashboard/customer-value/": (("customers", "customer"),),
    "/dashboard/customer-behaviour/": (("analytics", "activityevent"), ("analytics", "searchevent"), ("analytics", "visitor"), ("analytics", "visitorsession")),
    "/dashboard/customer-360/": (("customers", "customer"), ("bookings", "booking"), ("invoices", "invoice"), ("reviews", "review"), ("dashboard", "emaillog"), ("quotes", "quoterequest")),
    "/dashboard/bookings/": (("bookings", "booking"),),
    "/dashboard/calendar/": (("bookings", "booking"),),
    "/dashboard/contracts/": (("contracts", "cleaningcontract"),),
    "/dashboard/reports/": (("reports", "cleaningreport"),),
    "/dashboard/gallery/": (("gallery", "galleryitem"),),
    "/dashboard/reviews/": (("reviews", "review"),),
    "/dashboard/review-analytics/": (("reviews", "review"), ("dashboard", "reviewrequestlog")),
    "/dashboard/review-requests/send/": (("bookings", "booking"), ("dashboard", "reviewrequestlog")),
    "/dashboard/review-requests/": (("bookings", "booking"), ("dashboard", "reviewrequestlog")),
    "/dashboard/employee-training/": (("induction", "employeeinduction"),),
    "/dashboard/employee-attendance-analytics/": (("attendance", "attendancelog"), ("employees", "employee"), ("leave_management", "leaverequest")),
    "/dashboard/employee-bonuses/": (("bookings", "booking"), ("employees", "employee")),
    "/dashboard/employee-kpi/": (("attendance", "attendancelog"), ("bookings", "booking"), ("employees", "employee")),
    "/dashboard/employee-performance-centre/": (("attendance", "attendancelog"), ("bookings", "booking"), ("employees", "employee"), ("payroll", "payrollrecord")),
    "/dashboard/employee-performance/email-report/": (("attendance", "attendancelog"), ("bookings", "booking"), ("employees", "employee"), ("payroll", "payrollrecord")),
    "/dashboard/employee-performance/export-pdf/": (("attendance", "attendancelog"), ("bookings", "booking"), ("employees", "employee"), ("payroll", "payrollrecord")),
    "/dashboard/employee-performance/": (("attendance", "attendancelog"), ("bookings", "booking"), ("employees", "employee"), ("payroll", "payrollrecord"), ("leave_management", "leaverequest")),
    "/dashboard/employee-schedule/": (("bookings", "booking"), ("employees", "employee"), ("leave_management", "leaverequest")),
    "/dashboard/employees/": (("employees", "employee"),),
    "/dashboard/induction/": (("induction", "employeeinduction"),),
    "/dashboard/attendance/": (("attendance", "attendancelog"),),
    "/dashboard/leave/": (("leave_management", "leaverequest"),),
    "/dashboard/rosters/": (("rosters", "roster"),),
    "/dashboard/payroll/": (("payroll", "payrollrecord"),),
    "/dashboard/invoices/": (("invoices", "invoice"),),
    "/dashboard/expenses/": (("expenses", "expense"),),
    "/dashboard/careers/": (("dashboard", "careerapplication"),),
    "/dashboard/campaign-performance/": (("dashboard", "campaignlog"),),
    "/dashboard/campaigns/": (("customers", "customer"), ("bookings", "booking"), ("dashboard", "reviewrequestlog"), ("dashboard", "campaignlog"), ("customers", "marketingsubscriber")),
    "/dashboard/vip-campaigns/": (("customers", "customer"),),
    "/dashboard/email-": (("dashboard", "emaillog"),),
    "/dashboard/email-center/": (("invoices", "invoice"), ("bookings", "booking"), ("quotes", "quoterequest")),
    "/dashboard/settings/": (("dashboard", "companysettings"),),
    "/dashboard/activity/": (("dashboard", "activitylog"),),
    "/dashboard/equipment/": (("dashboard", "equipment"),),
    "/dashboard/maintenance/": (("dashboard", "maintenancehistory"),),
    "/dashboard/supplies/": (("dashboard", "cleaningsupply"),),
    "/dashboard/purchase-orders/": (("dashboard", "purchaseorder"),),
    "/dashboard/suppliers/": (("dashboard", "supplier"),),
    "/dashboard/vehicles/": (("dashboard", "vehicle"),),
    "/dashboard/faq-questions/": (("core", "faqquestion"),),
    "/dashboard/financials/": (("invoices", "invoice"), ("expenses", "expense"), ("payroll", "payrollrecord")),
    "/dashboard/finance-trends/": (("invoices", "invoice"), ("expenses", "expense"), ("payroll", "payrollrecord")),
    "/dashboard/gst-report/": (("invoices", "invoice"), ("expenses", "expense")),
    "/dashboard/profit-loss/": (("bookings", "booking"), ("employees", "employee"), ("invoices", "invoice"), ("expenses", "expense"), ("payroll", "payrollrecord")),
    "/dashboard/business-health/": (("bookings", "booking"), ("payroll", "payrollrecord"), ("quotes", "quoterequest")),
    "/dashboard/business-intelligence/": (("bookings", "booking"), ("dashboard", "cleaningsupply"), ("customers", "customer"), ("employees", "employee"), ("dashboard", "equipment"), ("expenses", "expense"), ("invoices", "invoice"), ("quotes", "quoterequest"), ("dashboard", "vehicle")),
    "/dashboard/business-kpis/": (("bookings", "booking"), ("dashboard", "campaignlog"), ("customers", "customer"), ("employees", "employee"), ("invoices", "invoice"), ("payroll", "payrollrecord"), ("reviews", "review")),
    "/dashboard/business-forecasting/": (("expenses", "expense"), ("invoices", "invoice")),
    "/dashboard/executive-bi/": (("bookings", "booking"), ("contracts", "cleaningcontract"), ("customers", "customer")),
    "/dashboard/executive/": (("dashboard", "activitylog"), ("bookings", "booking"), ("invoices", "invoice"), ("payroll", "payrollrecord"), ("quotes", "quoterequest")),
    "/dashboard/operations-centre/": (("bookings", "booking"), ("dashboard", "cleaningsupply"), ("dashboard", "equipment"), ("invoices", "invoice"), ("dashboard", "purchaseorder"), ("dashboard", "vehicle")),
    "/dashboard/service-performance/": (("bookings", "booking"),),
    "/dashboard/job-profitability/": (("bookings", "booking"), ("invoices", "invoice")),
    "/dashboard/performance/": (("employees", "employee"),),
    "/dashboard/owner-command-centre/": (("bookings", "booking"), ("dashboard", "cleaningsupply"), ("dashboard", "equipment"), ("invoices", "invoice"), ("dashboard", "purchaseorder"), ("dashboard", "vehicle")),
    "/dashboard/owner-alerts/": (("contracts", "cleaningcontract"), ("invoices", "invoice"), ("leave_management", "leaverequest")),
    "/dashboard/reminders/": (("dashboard", "equipment"), ("dashboard", "cleaningsupply"), ("dashboard", "purchaseorder"), ("dashboard", "vehicle"), ("dashboard", "maintenancehistory"), ("contracts", "cleaningcontract")),
    "/dashboard/newsletter/subscribe/": (("customers", "marketingsubscriber"),),
    "/dashboard/newsletter/": (("customers", "marketingsubscriber"),),
    "/dashboard/onboarding/document/": (
        ("induction", "employeeonboardingdocument"),
    ),
    "/dashboard/onboarding/": (("induction", "employeeonboardingprofile"),),
    "/dashboard/staff-schedule/": (("bookings", "booking"),),
    "/dashboard/export-report/": (("expenses", "expense"), ("invoices", "invoice")),
    "/dashboard/email-report/": (("expenses", "expense"), ("invoices", "invoice")),
}


# Dashboard URL names reviewed against the project URL resolver. New dashboard
# routes must be added here before a model permission prefix can authorize them.
DASHBOARD_PROTECTED_ROUTE_NAMES = frozenset(
    """
    activity_log_list add_booking add_contract add_customer add_employee add_equipment
    add_expense add_gallery_item add_leave_request add_maintenance add_purchase_order add_review
    add_roster add_supplier add_supply add_vehicle ai_quote_estimator approve_leave_request
    approve_payroll archive attendance_report booking_calendar booking_list bulk_import_analyse
    bulk_import_approve bulk_import_delete bulk_import_import bulk_import_item_edit bulk_import_list bulk_import_review
    bulk_import_upload business_forecasting_centre business_health business_intelligence business_kpis campaign_center
    campaign_history_detail campaign_performance campaign_preview cancel_invoice career_detail career_resume_download
    career_resume_preview careers_list company_settings compliance compliance_notifications compliance_overview
    compliance_renewals contract_detail contract_list contract_renewals convert_quote_to_booking corporate_lead_detail
    corporate_lead_list corporate_lead_update create_invoice create_invoice_from_booking create_stripe_checkout_session customer_360
    customer_analytics customer_behaviour customer_list customer_loyalty customer_profile_360 customer_value_dashboard
    dashboard dashboard_home dashboard_newsletter_subscribe delete delete_booking delete_campaign_history
    delete_contract delete_customer delete_employee delete_equipment delete_expense delete_gallery_item
    delete_invoice delete_newsletter_subscriber delete_quote_request delete_review delete_roster detail download
    download_invoice_pdf download_payslip_pdf edit edit_booking edit_campaign_history edit_contract
    edit_customer edit_employee edit_equipment edit_expense edit_gallery_item edit_invoice
    edit_newsletter_subscriber edit_review edit_roster edit_supplier edit_supply edit_vehicle
    email email_business_report email_center email_employee_performance_report email_log_list employee_attendance_analytics
    employee_bonuses employee_compliance employee_compliance_matrix employee_kpi_dashboard employee_list employee_performance
    employee_performance_centre employee_performance_detail employee_schedule employee_training_dashboard equipment_list executive_bi_dashboard
    executive_dashboard expense_list export_business_report export_employee_performance_pdf export_quotes_csv faq_question_list
    faq_question_reply finance_trends financial_dashboard gallery_list gallery_upload_batch generate_contract_bookings generate_payroll
    gst_report induction_cancel induction_completion_pdf induction_dashboard induction_detail induction_setup
    induction_start_record_pdf invoice_detail invoice_list job_profitability_dashboard lead_list leave_list
    list live_chat_assign live_chat_close live_chat_counts live_chat_detail live_chat_list live_chat_takeover maintenance_list
    mark_invoice_paid mark_invoice_unpaid mark_payroll_paid newsletter_subscriber_detail onboarding_dashboard onboarding_detail
    onboarding_document_review onboarding_set_status operations_command_centre owner_alert_centre owner_command_centre payroll_list
    profit_loss_dashboard purchase_orders quote_conversion_analytics quote_followup_centre receive_purchase_order reject_leave_request
    reminder_centre report_list review_analytics review_list review_requests roster_list run_audit
    security_center security_position_create security_position_edit security_position_list security_user_access_action security_user_create
    security_user_edit security_user_list send_booking_reminder send_contract_renewal_email send_customer_followup send_inactive_campaign
    send_invoice_reminder send_quote_followup send_quote_followup_email send_review_campaign send_review_request send_vip_campaign
    send_vip_campaign_legacy service_performance_dashboard staff_schedule_dashboard stripe_payment_cancel stripe_payment_success supplier_list
    supplies_list support_dashboard ticket_update update_booking_quick_status update_finding update_quote_status upload
    vehicle_list vip_campaigns
    """.split()
)


# Route-specific rules handle endpoints that combine models, perform mutations
# while sending an email, or calculate a report from data on POST.
DASHBOARD_PERMISSION_ROUTE_OVERRIDES = {
    "dashboard_home": {
        "GET": ("dashboard.view_activitylog", "bookings.view_booking", "dashboard.view_cleaningsupply", "customers.view_customer", "employees.view_employee", "dashboard.view_equipment", "gallery.view_galleryitem", "quotes.view_quoterequest", "reviews.view_review", "dashboard.view_vehicle"),
        "HEAD": ("dashboard.view_activitylog", "bookings.view_booking", "dashboard.view_cleaningsupply", "customers.view_customer", "employees.view_employee", "dashboard.view_equipment", "gallery.view_galleryitem", "quotes.view_quoterequest", "reviews.view_review", "dashboard.view_vehicle"),
    },
    "security_center": {
        "GET": ("security.view_security_center",),
        "HEAD": ("security.view_security_center",),
        "POST": ("security.view_security_center", "security.add_securityauditreport"),
    },
    "dashboard": {
        "GET": ("security_monitor.view_securityfinding", "security_monitor.view_securityalertdelivery"),
        "HEAD": ("security_monitor.view_securityfinding", "security_monitor.view_securityalertdelivery"),
    },
    "update_finding": {"POST": ("security_monitor.change_securityfinding",)},
    "run_audit": {"POST": ("security_monitor.add_securityfinding", "security_monitor.change_securityfinding")},
    "live_chat_assign": {"POST": ("support.change_livechatconversation",)},
    "security_position_create": {"GET": ("security.manage_security_roles",), "POST": ("security.manage_security_roles",)},
    "security_position_edit": {"GET": ("security.manage_security_roles",), "POST": ("security.manage_security_roles",)},
    "security_position_list": {"GET": ("security.manage_users",), "HEAD": ("security.manage_users",)},
    "customer_profile_360": {"GET": ("customers.view_customer", "bookings.view_booking", "invoices.view_invoice", "reviews.view_review", "dashboard.view_emaillog", "quotes.view_quoterequest"), "HEAD": ("customers.view_customer", "bookings.view_booking", "invoices.view_invoice", "reviews.view_review", "dashboard.view_emaillog", "quotes.view_quoterequest")},
    "customer_360": {"GET": ("customers.view_customer", "bookings.view_booking", "invoices.view_invoice", "quotes.view_quoterequest"), "HEAD": ("customers.view_customer", "bookings.view_booking", "invoices.view_invoice", "quotes.view_quoterequest")},
    "send_customer_followup": {"POST": ("customers.change_customer",)},
    "create_invoice_from_booking": {"POST": ("bookings.view_booking", "invoices.add_invoice")},
    "update_quote_status": {"POST": ("quotes.change_quoterequest", "bookings.add_booking")},
    "delete_quote_request": {"POST": ("quotes.delete_quoterequest",)},
    "gallery_upload_batch": {"POST": ()},
    "business_health": {"GET": ("bookings.view_booking", "payroll.view_payrollrecord", "quotes.view_quoterequest"), "HEAD": ("bookings.view_booking", "payroll.view_payrollrecord", "quotes.view_quoterequest")},
    "business_intelligence": {"GET": ("bookings.view_booking", "dashboard.view_cleaningsupply", "customers.view_customer", "employees.view_employee", "dashboard.view_equipment", "expenses.view_expense", "invoices.view_invoice", "quotes.view_quoterequest", "dashboard.view_vehicle"), "HEAD": ("bookings.view_booking", "dashboard.view_cleaningsupply", "customers.view_customer", "employees.view_employee", "dashboard.view_equipment", "expenses.view_expense", "invoices.view_invoice", "quotes.view_quoterequest", "dashboard.view_vehicle")},
    "business_kpis": {"GET": ("bookings.view_booking", "dashboard.view_campaignlog", "customers.view_customer", "employees.view_employee", "invoices.view_invoice", "payroll.view_payrollrecord", "reviews.view_review"), "HEAD": ("bookings.view_booking", "dashboard.view_campaignlog", "customers.view_customer", "employees.view_employee", "invoices.view_invoice", "payroll.view_payrollrecord", "reviews.view_review")},
    "business_forecasting_centre": {"GET": ("expenses.view_expense", "invoices.view_invoice"), "HEAD": ("expenses.view_expense", "invoices.view_invoice")},
    "executive_dashboard": {"GET": ("dashboard.view_activitylog", "bookings.view_booking", "invoices.view_invoice", "payroll.view_payrollrecord", "quotes.view_quoterequest"), "HEAD": ("dashboard.view_activitylog", "bookings.view_booking", "invoices.view_invoice", "payroll.view_payrollrecord", "quotes.view_quoterequest")},
    "executive_bi_dashboard": {"GET": ("bookings.view_booking", "contracts.view_cleaningcontract", "customers.view_customer"), "HEAD": ("bookings.view_booking", "contracts.view_cleaningcontract", "customers.view_customer")},
    "operations_command_centre": {"GET": ("bookings.view_booking", "dashboard.view_cleaningsupply", "dashboard.view_equipment", "invoices.view_invoice", "dashboard.view_purchaseorder", "dashboard.view_vehicle"), "HEAD": ("bookings.view_booking", "dashboard.view_cleaningsupply", "dashboard.view_equipment", "invoices.view_invoice", "dashboard.view_purchaseorder", "dashboard.view_vehicle")},
    "owner_command_centre": {"GET": ("bookings.view_booking", "dashboard.view_cleaningsupply", "dashboard.view_equipment", "invoices.view_invoice", "dashboard.view_purchaseorder", "dashboard.view_vehicle"), "HEAD": ("bookings.view_booking", "dashboard.view_cleaningsupply", "dashboard.view_equipment", "invoices.view_invoice", "dashboard.view_purchaseorder", "dashboard.view_vehicle")},
    "owner_alert_centre": {"GET": ("contracts.view_cleaningcontract", "invoices.view_invoice", "leave_management.view_leaverequest"), "HEAD": ("contracts.view_cleaningcontract", "invoices.view_invoice", "leave_management.view_leaverequest")},
    "job_profitability_dashboard": {"GET": ("bookings.view_booking", "invoices.view_invoice"), "HEAD": ("bookings.view_booking", "invoices.view_invoice")},
    "profit_loss_dashboard": {"GET": ("bookings.view_booking", "employees.view_employee", "expenses.view_expense", "invoices.view_invoice", "payroll.view_payrollrecord"), "HEAD": ("bookings.view_booking", "employees.view_employee", "expenses.view_expense", "invoices.view_invoice", "payroll.view_payrollrecord")},
    "gst_report": {"GET": ("invoices.view_invoice", "expenses.view_expense"), "HEAD": ("invoices.view_invoice", "expenses.view_expense")},
    "ai_quote_estimator": {"GET": ("invoices.view_invoice",), "HEAD": ("invoices.view_invoice",), "POST": ("invoices.view_invoice",)},
    "send_review_request": {"POST": ("bookings.view_booking", "dashboard.add_reviewrequestlog", "dashboard.change_reviewrequestlog", "dashboard.add_emaillog", "dashboard.add_activitylog")},
    "review_requests": {"GET": ("bookings.view_booking", "dashboard.view_reviewrequestlog"), "HEAD": ("bookings.view_booking", "dashboard.view_reviewrequestlog")},
    "review_analytics": {"GET": ("reviews.view_review", "dashboard.view_reviewrequestlog"), "HEAD": ("reviews.view_review", "dashboard.view_reviewrequestlog")},
    "employee_schedule": {"GET": ("bookings.view_booking", "employees.view_employee", "leave_management.view_leaverequest"), "HEAD": ("bookings.view_booking", "employees.view_employee", "leave_management.view_leaverequest")},
    "employee_performance_centre": {"GET": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord"), "HEAD": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord")},
    "employee_performance": {"GET": ("dashboard.view_activitylog", "attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord"), "HEAD": ("dashboard.view_activitylog", "attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord")},
    "employee_performance_detail": {"GET": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord", "leave_management.view_leaverequest"), "HEAD": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord", "leave_management.view_leaverequest")},
    "export_employee_performance_pdf": {"GET": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord"), "HEAD": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord")},
    "email_employee_performance_report": {"POST": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord")},
    "employee_attendance_analytics": {"GET": ("attendance.view_attendancelog", "employees.view_employee", "leave_management.view_leaverequest"), "HEAD": ("attendance.view_attendancelog", "employees.view_employee", "leave_management.view_leaverequest")},
    "employee_kpi_dashboard": {"GET": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee"), "HEAD": ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee")},
    "staff_schedule_dashboard": {"GET": ("bookings.view_booking",), "HEAD": ("bookings.view_booking",)},
    "campaign_center": {"GET": ("customers.view_customer", "bookings.view_booking", "dashboard.view_reviewrequestlog", "dashboard.view_campaignlog", "customers.view_marketingsubscriber"), "HEAD": ("customers.view_customer", "bookings.view_booking", "dashboard.view_reviewrequestlog", "dashboard.view_campaignlog", "customers.view_marketingsubscriber")},
    "send_vip_campaign": {"POST": ("customers.view_customer", "dashboard.add_campaignlog", "dashboard.add_emaillog", "dashboard.add_activitylog")},
    "send_vip_campaign_legacy": {"POST": ("customers.view_customer", "dashboard.add_campaignlog", "dashboard.add_emaillog", "dashboard.add_activitylog")},
    "send_inactive_campaign": {"POST": ("customers.view_customer", "dashboard.add_campaignlog", "dashboard.add_emaillog", "dashboard.add_activitylog")},
    "send_review_campaign": {"POST": ("bookings.view_booking", "dashboard.add_reviewrequestlog", "dashboard.add_emaillog", "dashboard.add_campaignlog", "dashboard.add_activitylog")},
    "campaign_preview": {"GET": ("customers.view_customer", "bookings.view_booking"), "HEAD": ("customers.view_customer", "bookings.view_booking")},
    "campaign_performance": {"GET": ("dashboard.view_campaignlog",), "HEAD": ("dashboard.view_campaignlog",)},
    "campaign_history_detail": {"GET": ("dashboard.view_campaignlog",), "HEAD": ("dashboard.view_campaignlog",)},
    "edit_campaign_history": {"GET": ("dashboard.change_campaignlog",), "POST": ("dashboard.change_campaignlog",)},
    "delete_campaign_history": {"GET": ("dashboard.delete_campaignlog",), "POST": ("dashboard.delete_campaignlog",)},
    "dashboard_newsletter_subscribe": {"POST": ("customers.add_marketingsubscriber", "customers.change_marketingsubscriber", "dashboard.add_emaillog", "dashboard.add_activitylog")},
    "newsletter_subscriber_detail": {"GET": ("customers.view_marketingsubscriber",), "HEAD": ("customers.view_marketingsubscriber",)},
    "edit_newsletter_subscriber": {"GET": ("customers.change_marketingsubscriber",), "POST": ("customers.change_marketingsubscriber",)},
    "delete_newsletter_subscriber": {"GET": ("customers.delete_marketingsubscriber",), "POST": ("customers.delete_marketingsubscriber",)},
    "receive_purchase_order": {"POST": ("dashboard.change_purchaseorder", "dashboard.change_cleaningsupply")},
    "mark_payroll_paid": {"POST": ("payroll.change_payrollrecord",)},
    "email_business_report": {"POST": ("expenses.view_expense", "invoices.view_invoice")},
    "send_quote_followup_email": {"POST": ("quotes.change_quoterequest",)},
    "send_booking_reminder": {"POST": ("bookings.change_booking", "dashboard.add_emaillog")},
    "send_invoice_reminder": {"POST": ("invoices.change_invoice", "dashboard.add_emaillog")},
    "send_quote_followup": {"POST": ("quotes.change_quoterequest", "dashboard.add_emaillog")},
    "generate_contract_bookings": {"POST": ("contracts.change_cleaningcontract", "bookings.add_booking")},
    "send_contract_renewal_email": {"POST": ("contracts.change_cleaningcontract", "dashboard.add_emaillog")},
    "email_center": {"GET": ("invoices.view_invoice", "bookings.view_booking", "quotes.view_quoterequest"), "HEAD": ("invoices.view_invoice", "bookings.view_booking", "quotes.view_quoterequest")},
    "bulk_import_list": {"GET": ("company_documents.view_bulkimportbatch",), "HEAD": ("company_documents.view_bulkimportbatch",)},
    "bulk_import_upload": {"GET": ("company_documents.add_bulkimportbatch", "company_documents.add_bulkimportitem"), "POST": ("company_documents.add_bulkimportbatch", "company_documents.add_bulkimportitem")},
    "bulk_import_review": {"GET": ("company_documents.view_bulkimportbatch", "company_documents.change_bulkimportbatch", "company_documents.view_bulkimportitem"), "HEAD": ("company_documents.view_bulkimportbatch", "company_documents.change_bulkimportbatch", "company_documents.view_bulkimportitem")},
    "bulk_import_analyse": {"POST": ("company_documents.change_bulkimportbatch", "company_documents.change_bulkimportitem")},
    "bulk_import_approve": {"POST": ("company_documents.view_bulkimportbatch", "company_documents.change_bulkimportitem")},
    "bulk_import_import": {"POST": ("company_documents.change_bulkimportbatch", "company_documents.change_bulkimportitem", "company_documents.add_companydocument")},
    # Let an authorized user reach the view's POST-only guard on GET so it
    # returns 405; no delete operation is possible on that method.
    "bulk_import_delete": {
        "GET": ("company_documents.delete_bulkimportbatch",),
        "POST": ("company_documents.delete_bulkimportbatch",),
    },
    "bulk_import_item_edit": {"GET": ("company_documents.change_bulkimportitem",), "POST": ("company_documents.change_bulkimportitem",)},
    "upload": {"GET": ("company_documents.add_companydocument",), "POST": ("company_documents.add_companydocument",)},
    "edit": {"GET": ("company_documents.change_companydocument",), "POST": ("company_documents.change_companydocument",)},
    "compliance_overview": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee", "dashboard.view_vehicle", "customers.view_customer", "dashboard.view_supplier", "contracts.view_cleaningcontract"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee", "dashboard.view_vehicle", "customers.view_customer", "dashboard.view_supplier", "contracts.view_cleaningcontract")},
    "employee_compliance_matrix": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee")},
    "employee_compliance": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument", "employees.view_employee")},
    "compliance": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument")},
    "compliance_renewals": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument")},
    "compliance_notifications": {"GET": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument"), "HEAD": ("company_documents.view_compliancerequirement", "company_documents.view_companydocument")},
    "create_stripe_checkout_session": {"POST": ("invoices.view_invoice",)},
    "email": {"GET": ("company_documents.view_companydocument",), "HEAD": ("company_documents.view_companydocument",), "POST": ("company_documents.change_companydocument",)},
    "archive": {"POST": ("company_documents.change_companydocument",)},
    "delete": {"POST": ("company_documents.delete_companydocument",)},
}


DASHBOARD_POST_ROUTE_NAMES = frozenset(
    {
        "security_user_create", "security_user_edit", "security_user_access_action",
        "career_detail", "company_settings", "update_quote_status",
        "corporate_lead_update", "add_customer", "edit_customer", "delete_customer",
        "delete_quote_request",
        "add_booking", "edit_booking", "delete_booking", "update_booking_quick_status",
        "create_invoice_from_booking", "add_employee", "edit_employee", "delete_employee",
        "add_gallery_item", "edit_gallery_item", "delete_gallery_item", "add_review",
        "edit_review", "delete_review", "send_customer_followup", "send_review_request",
        "dashboard_newsletter_subscribe", "edit_newsletter_subscriber",
        "delete_newsletter_subscriber", "add_equipment", "edit_equipment",
        "gallery_upload_batch",
        "delete_equipment", "add_supply", "edit_supply", "add_purchase_order",
        "receive_purchase_order", "add_supplier", "edit_supplier", "add_vehicle",
        "edit_vehicle", "add_maintenance", "send_quote_followup_email",
        "convert_quote_to_booking", "faq_question_reply", "send_vip_campaign",
        "send_vip_campaign_legacy", "send_inactive_campaign", "send_review_campaign",
        "edit_campaign_history", "delete_campaign_history", "generate_payroll",
        "approve_payroll", "mark_payroll_paid", "create_invoice", "edit_invoice",
        "mark_invoice_paid", "mark_invoice_unpaid", "cancel_invoice", "delete_invoice",
        "induction_setup", "induction_cancel", "onboarding_document_review",
        "onboarding_set_status", "add_contract", "edit_contract", "delete_contract",
        "generate_contract_bookings", "send_contract_renewal_email", "add_leave_request",
        "approve_leave_request", "reject_leave_request", "add_roster", "edit_roster",
        "delete_roster", "add_expense", "edit_expense", "delete_expense",
        "ticket_update", "live_chat_takeover", "live_chat_assign", "live_chat_close", "upload", "edit",
        "email", "archive", "delete", "bulk_import_delete", "bulk_import_upload",
        "bulk_import_analyse", "bulk_import_approve", "bulk_import_import",
        "bulk_import_item_edit", "update_finding", "run_audit",
    }
)


def dashboard_required_permissions(path, method, url_name=None):
    method = method.upper()
    if url_name is None:
        try:
            url_name = resolve(path).url_name
        except Resolver404:
            return None
    if url_name not in DASHBOARD_PROTECTED_ROUTE_NAMES:
        return None

    route_override = DASHBOARD_PERMISSION_ROUTE_OVERRIDES.get(url_name)
    if route_override is not None:
        return route_override.get(method)

    if method in {"PUT", "PATCH", "DELETE", "OPTIONS"}:
        return None
    if method == "POST" and url_name not in DASHBOARD_POST_ROUTE_NAMES:
        return None
    if method not in {"GET", "HEAD", "POST"}:
        return None

    section = next(
        (
            permissions
            for prefix, permissions in sorted(
                DASHBOARD_PERMISSION_SECTIONS.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            )
            if path.startswith(prefix)
        ),
        None,
    )
    if section is None:
        return None
    if isinstance(section, str):
        return (section,)
    if not section:
        return ()
    if len(section) == 2 and isinstance(section[0], str):
        section = (section,)

    lowered_path = path.casefold()
    if method == "DELETE" or any(part in lowered_path for part in ("/delete", "/remove")):
        action = "delete"
    elif method in {"PUT", "PATCH"}:
        action = "change"
    elif any(part in lowered_path for part in ("/add", "/create", "/upload", "/generate")):
        action = "add"
    elif method == "POST" or any(part in lowered_path for part in ("/edit", "/update", "/approve", "/mark-", "/send", "/receive", "/takeover", "/close", "/reply", "/convert", "/renewal-email")):
        action = "change"
    else:
        action = "view"
    return tuple(f"{app_label}.{action}_{model_name}" for app_label, model_name in section)


class ExceptionLoggingMiddleware:
    """Write unexpected request tracebacks to the service console logs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            logger.error(
                "Unhandled request exception for %s %s",
                request.method,
                request.path,
                exc_info=(type(exception), exception, exception.__traceback__),
            )
        return None


class SlowRequestLoggingMiddleware:
    """Record end-to-end and SQL timing for slow HTTP requests."""

    SLOW_REQUEST_SECONDS = 1.0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        query_stats = {"count": 0, "seconds": 0.0}

        def time_query(execute, sql, params, many, context):
            query_started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                query_stats["count"] += 1
                query_stats["seconds"] += time.perf_counter() - query_started

        response = None
        try:
            with connection.execute_wrapper(time_query):
                response = self.get_response(request)
            return response
        finally:
            elapsed = time.perf_counter() - started
            if elapsed >= self.SLOW_REQUEST_SECONDS:
                logger.warning(
                    "Slow request method=%s path=%s status=%s total_ms=%.1f db_queries=%s db_ms=%.1f",
                    request.method,
                    request.path,
                    getattr(response, "status_code", "exception"),
                    elapsed * 1000,
                    query_stats["count"],
                    query_stats["seconds"] * 1000,
                )


class RoleAccessMiddleware:
    """
    Role-based access control.

    Rules:
    - Customers can access /portal/ only.
    - Employees can access /employee/ only.
    - Staff and superusers can access all protected areas.
    - OAuth callbacks that must be reached before authentication
      are explicitly allowed through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # ======================================================
        # PUBLIC / AUTHENTICATION PATHS
        # ======================================================
        #
        # These paths must be reachable without an authenticated
        # user. This includes OAuth callbacks because the external
        # provider redirects the browser back before Django has
        # established the application session.
        #

        public_paths = (
            # Static / media
            "/static/",
            "/media/",

            # Customer authentication
            "/portal/login/",
            "/portal/register/",
            "/portal/verify-email/",
            "/portal/resend-verification/",
            "/portal/logout/",
            "/portal/password-reset/",

            # Employee authentication
            "/employee/login/",
            "/employee/logout/",

            # Employee Google OAuth callback
            "/employee/google/oauth/callback/",

            # Dashboard authentication
            "/dashboard/login/",
            "/dashboard/logout/",
        )

        if path.startswith(public_paths):
            return self.get_response(request)

        # ======================================================
        # UNAUTHENTICATED USERS
        # ======================================================

        if not request.user.is_authenticated:

            if path.startswith("/dashboard/"):
                return redirect("dashboard_login")

            if path.startswith("/employee/"):
                return redirect("employee_login")

            if path.startswith("/portal/"):
                return redirect("portal_login")

            return self.get_response(request)

        # ======================================================
        # STAFF / SUPERUSER
        # ======================================================
        #
        # Staff users need a dashboard role. Superusers retain full access.
        #

        if request.user.is_staff or request.user.is_superuser:
            if request.user.is_superuser or not path.startswith("/dashboard/"):
                return self.get_response(request)

            if path.startswith("/dashboard/logout/"):
                return self.get_response(request)

            if not request.user.has_perm("security.access_dashboard"):
                raise PermissionDenied

            try:
                match = resolve(path)
            except Resolver404:
                raise PermissionDenied

            required_permissions = dashboard_required_permissions(
                path,
                request.method,
                match.url_name,
            )
            if required_permissions is None:
                raise PermissionDenied
            if required_permissions and not all(
                request.user.has_perm(permission)
                for permission in required_permissions
            ):
                raise PermissionDenied
            return self.get_response(request)

        # ======================================================
        # DETERMINE USER ROLE
        # ======================================================

        is_customer = hasattr(
            request.user,
            "customer_profile",
        )

        is_employee = hasattr(
            request.user,
            "employee_profile",
        )

        # ======================================================
        # DASHBOARD ACCESS
        # ======================================================

        if path.startswith("/dashboard/"):
            messages.error(
                request,
                "You do not have permission to access admin dashboard.",
            )

            if is_customer:
                return redirect("portal_dashboard")

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        # ======================================================
        # EMPLOYEE PORTAL ACCESS
        # ======================================================

        if path.startswith("/employee/") and not is_employee:
            messages.error(
                request,
                "Only employees can access employee portal.",
            )

            if is_customer:
                return redirect("portal_dashboard")

            return redirect("/")

        # ======================================================
        # CUSTOMER PORTAL ACCESS
        # ======================================================

        if path.startswith("/portal/") and not is_customer:
            messages.error(
                request,
                "Only customers can access customer portal.",
            )

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        return self.get_response(request)


class SEOMiddleware:
    """
    Controls SEO-related response headers.

    Public HTML pages:
        X-Robots-Tag: index, follow

    Private application areas:
        X-Robots-Tag: noindex, nofollow

    Authenticated responses:
        Cache-Control: private, no-store

    Sitemap and robots.txt are handled separately.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ======================================================
        # SITEMAP
        # ======================================================

        if request.path == "/sitemap.xml":
            # Django may add an X-Robots-Tag header to the
            # sitemap. Remove it so the sitemap itself remains
            # crawlable.
            if "X-Robots-Tag" in response.headers:
                del response.headers["X-Robots-Tag"]

            return response

        # ======================================================
        # ROBOTS.TXT
        # ======================================================

        if request.path == "/robots.txt":
            return response

        # ======================================================
        # AUTHENTICATED RESPONSES
        # ======================================================

        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # PRIVATE APPLICATION AREAS
        # ======================================================

        private_paths = (
            "/admin/",
            "/dashboard/",
            "/portal/",
            "/employee/",
        )

        if request.path.startswith(private_paths):
            response["X-Robots-Tag"] = "noindex, nofollow"
            response["Cache-Control"] = "private, no-store"

        # ======================================================
        # PUBLIC HTML
        # ======================================================

        elif (
            response.status_code == 200
            and "text/html" in response.get("Content-Type", "")
        ):
            response["X-Robots-Tag"] = "index, follow"

        return response


class CacheHeaderMiddleware:
    """
    Safe cache-control policy.

    Goals:
    - Keep caching for public website pages.
    - Keep long-lived caching for static files.
    - Keep media caching.
    - Cache robots.txt and sitemap.xml.
    - Never publicly cache authenticated responses.
    - Never cache state-changing requests.
    - Avoid caching requests carrying session/CSRF cookies.
    - Protect sensitive application areas from accidental caching.

    This middleware does not modify:
    - application logic
    - authentication
    - SEO behaviour
    - URLs
    - templates
    - database access
    - Cloudinary
    - Stripe
    - email
    - OAuth configuration
    - Channels
    - WebSockets
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path

        # ======================================================
        # 1. NEVER CACHE STATE-CHANGING REQUESTS
        # ======================================================

        if request.method not in ("GET", "HEAD"):
            response["Cache-Control"] = "no-store"
            return response

        # ======================================================
        # 2. NEVER CACHE AUTHENTICATED USERS
        # ======================================================

        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 3. NEVER CACHE REQUESTS WITH SESSION / CSRF COOKIES
        # ======================================================

        if (
            "sessionid" in request.COOKIES
            or "csrftoken" in request.COOKIES
        ):
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 4. NEVER CACHE RESPONSES THAT SET COOKIES
        # ======================================================

        if "Set-Cookie" in response.headers:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 5. PRIVATE / SENSITIVE APPLICATION AREAS
        # ======================================================

        private_paths = (
            # Django admin
            "/admin/",

            # Internal dashboards
            "/dashboard/",

            # Customer portal
            "/portal/",

            # Employee portal
            "/employee/",

            # Authentication
            "/login/",
            "/logout/",
            "/register/",
            "/password-reset/",

            # Booking / checkout / account
            "/booking/",
            "/bookings/",
            "/checkout/",
            "/account/",

            # Customer information
            "/customers/",
            "/customer/",

            # Financial information
            "/invoice/",
            "/invoices/",
            "/payroll/",
            "/expenses/",

            # Employee information
            "/employees/",
            "/attendance/",
            "/leave/",
            "/leave_management/",
            "/rosters/",

            # Business management
            "/contracts/",
            "/reports/",

            # Notifications
            "/notifications/",

            # Support / live chat
            "/support/",
            "/chat/",

            # Analytics
            "/analytics/",
        )

        if path.startswith(private_paths):
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 6. SEO FILES
        # ======================================================

        if path == "/robots.txt":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )
            return response

        if path == "/sitemap.xml":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )
            return response

        # ======================================================
        # 7. STATIC FILES
        # ======================================================

        if path.startswith("/static/"):
            response["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
            return response

        # ======================================================
        # 8. MEDIA FILES
        # ======================================================

        if path.startswith("/media/"):
            response["Cache-Control"] = (
                "public, max-age=2592000"
            )
            return response

        # ======================================================
        # 9. SAFE PUBLIC WEBSITE PAGES
        # ======================================================
        #
        # Only normal anonymous GET/HEAD requests reach here.
        #

        if (
            response.status_code == 200
            and "text/html" in response.get(
                "Content-Type",
                "",
            )
        ):
            response["Cache-Control"] = (
                "public, max-age=3600, must-revalidate"
            )

        return response
