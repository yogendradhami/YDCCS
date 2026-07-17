from django.urls import path

<<<<<<< HEAD
from .views import (
    activity_log_list,
    add_booking,
    add_customer,
    add_employee,
    add_equipment,
    add_gallery_item,
    add_maintenance,
    add_purchase_order,
    add_review,
    add_supplier,
    add_supply,
    add_vehicle,
    ai_quote_estimator,
    attendance_report,
    booking_calendar,
    booking_list,
    business_forecasting_centre,
    business_health,
    business_intelligence,
    business_kpis,
    campaign_center,
    campaign_performance,
    campaign_preview,
    company_settings,
    convert_quote_to_booking,
    create_invoice_from_booking,
    customer_360,
    customer_analytics,
    customer_list,
    customer_loyalty,
    customer_profile_360,
    customer_value_dashboard,
    dashboard_home,
    delete_booking,
    delete_customer,
    delete_employee,
    delete_equipment,
    delete_gallery_item,
    delete_review,
    edit_booking,
    edit_customer,
    edit_employee,
    edit_equipment,
    edit_gallery_item,
    edit_review,
    edit_supplier,
    edit_supply,
    edit_vehicle,
    email_business_report,
    email_center,
    email_employee_performance_report,
    email_log_list,
    employee_attendance_analytics,
    employee_bonuses,
    employee_kpi_dashboard,
    employee_list,
    employee_performance,
    employee_performance_centre,
    employee_performance_detail,
    employee_schedule,
    equipment_list,
    executive_bi_dashboard,
    executive_dashboard,
    export_business_report,
    export_employee_performance_pdf,
    export_quotes_csv,
    finance_trends,
    financial_dashboard,
    gallery_list,
    gst_report,
    job_profitability_dashboard,
    lead_list,
    maintenance_list,
    operations_command_centre,
    owner_alert_centre,
    owner_command_centre,
    profit_loss_dashboard,
    purchase_orders,
    quote_conversion_analytics,
    quote_followup_centre,
    receive_purchase_order,
    reminder_center,
    reminder_centre,
    review_analytics,
    review_list,
    review_requests,
    send_booking_reminder,
    send_customer_followup,
    send_inactive_campaign,
    send_invoice_reminder,
    send_quote_followup,
    send_quote_followup_email,
    send_review_campaign,
    send_review_request,
    send_vip_campaign,
    service_performance_dashboard,
    staff_schedule_dashboard,
    supplier_list,
    supplies_list,
    update_booking_quick_status,
    update_quote_status,
    vehicle_list,
    vip_campaigns,
)

urlpatterns = [
    path("dashboard/", dashboard_home, name="dashboard_home"),
    path("dashboard/settings/", company_settings, name="company_settings"),
    path("dashboard/leads/", lead_list, name="lead_list"),
    path(
        "dashboard/update-status/<int:quote_id>/",
        update_quote_status,
        name="update_quote_status",
    ),
    path("dashboard/customers/", customer_list, name="customer_list"),
    path("dashboard/customers/add/", add_customer, name="add_customer"),
    path(
        "dashboard/customers/<int:customer_id>/edit/",
        edit_customer,
        name="edit_customer",
    ),
    path(
        "dashboard/customers/<int:customer_id>/delete/",
        delete_customer,
        name="delete_customer",
    ),
    path("dashboard/bookings/", booking_list, name="booking_list"),
    path("dashboard/bookings/add/", add_booking, name="add_booking"),
    path(
        "dashboard/bookings/<int:booking_id>/edit/", edit_booking, name="edit_booking"
    ),
    path(
        "dashboard/bookings/<int:booking_id>/delete/",
        delete_booking,
        name="delete_booking",
    ),
    path("dashboard/calendar/", booking_calendar, name="booking_calendar"),
    path("dashboard/employees/", employee_list, name="employee_list"),
    path("dashboard/employees/add/", add_employee, name="add_employee"),
    path(
        "dashboard/employees/<int:employee_id>/edit/",
        edit_employee,
        name="edit_employee",
    ),
    path(
        "dashboard/employees/<int:employee_id>/delete/",
        delete_employee,
        name="delete_employee",
    ),
    path("dashboard/gallery/", gallery_list, name="gallery_list"),
    path("dashboard/gallery/add/", add_gallery_item, name="add_gallery_item"),
    path(
        "dashboard/gallery/<int:item_id>/edit/",
        edit_gallery_item,
        name="edit_gallery_item",
    ),
    path(
        "dashboard/gallery/<int:item_id>/delete/",
        delete_gallery_item,
        name="delete_gallery_item",
    ),
    path("dashboard/reviews/", review_list, name="review_list"),
    path("dashboard/reviews/add/", add_review, name="add_review"),
    path("dashboard/reviews/<int:review_id>/edit/", edit_review, name="edit_review"),
    path(
        "dashboard/reviews/<int:review_id>/delete/", delete_review, name="delete_review"
    ),
    path("dashboard/performance/", employee_performance, name="employee_performance"),
    path("dashboard/export-quotes/", export_quotes_csv, name="export_quotes_csv"),
    path("dashboard/attendance/", attendance_report, name="attendance_report"),
    path("dashboard/activity/", activity_log_list, name="activity_log_list"),
    path("dashboard/business-health/", business_health, name="business_health"),
    path("dashboard/financials/", financial_dashboard, name="financial_dashboard"),
    path("dashboard/executive/", executive_dashboard, name="executive_dashboard"),
    path("dashboard/reminders/", reminder_center, name="reminder_center"),
    path("dashboard/email-center/", email_center, name="email_center"),
    path(
        "dashboard/email-center/invoice/<int:invoice_id>/send/",
        send_invoice_reminder,
        name="send_invoice_reminder",
    ),
    path(
        "dashboard/email-center/booking/<int:booking_id>/send/",
        send_booking_reminder,
        name="send_booking_reminder",
    ),
    path(
        "dashboard/email-center/quote/<int:quote_id>/send/",
        send_quote_followup,
        name="send_quote_followup",
    ),
    path("dashboard/email-logs/", email_log_list, name="email_log_list"),
    path(
        "dashboard/customer-analytics/", customer_analytics, name="customer_analytics"
    ),
    path("dashboard/review-requests/", review_requests, name="review_requests"),
    path(
        "dashboard/review-requests/send/<int:booking_id>/",
        send_review_request,
        name="send_review_request",
    ),
    path("dashboard/review-analytics/", review_analytics, name="review_analytics"),
    path("dashboard/customer-loyalty/", customer_loyalty, name="customer_loyalty"),
    path(
        "dashboard/customer/<int:customer_id>/",
        customer_profile_360,
        name="customer_profile_360",
    ),
    path("dashboard/employee-bonuses/", employee_bonuses, name="employee_bonuses"),
    path("dashboard/campaigns/", campaign_center, name="campaign_center"),
    path("dashboard/campaigns/send-vip/", send_vip_campaign, name="send_vip_campaign"),
    path(
        "dashboard/campaigns/send-inactive/",
        send_inactive_campaign,
        name="send_inactive_campaign",
    ),
    path(
        "dashboard/campaigns/send-review/",
        send_review_campaign,
        name="send_review_campaign",
    ),
    path(
        "dashboard/campaigns/preview/<str:campaign_type>/",
        campaign_preview,
        name="campaign_preview",
    ),
    path(
        "dashboard/campaign-performance/",
        campaign_performance,
        name="campaign_performance",
    ),
    path("dashboard/profit-loss/", profit_loss_dashboard, name="profit_loss_dashboard"),
    path("dashboard/business-kpis/", business_kpis, name="business_kpis"),
    path("dashboard/employee-schedule/", employee_schedule, name="employee_schedule"),
    path("dashboard/gst-report/", gst_report, name="gst_report"),
    path("dashboard/finance-trends/", finance_trends, name="finance_trends"),
    path(
        "dashboard/bookings/<int:booking_id>/quick-status/<str:new_status>/",
        update_booking_quick_status,
        name="update_booking_quick_status",
    ),
    path("dashboard/equipment/", equipment_list, name="equipment_list"),
    path("dashboard/equipment/add/", add_equipment, name="add_equipment"),
    path(
        "dashboard/equipment/<int:equipment_id>/edit/",
        edit_equipment,
        name="edit_equipment",
    ),
    path(
        "dashboard/equipment/<int:equipment_id>/delete/",
        delete_equipment,
        name="delete_equipment",
    ),
    path("dashboard/supplies/", supplies_list, name="supplies_list"),
    path("dashboard/supplies/add/", add_supply, name="add_supply"),
    path("dashboard/supplies/<int:supply_id>/edit/", edit_supply, name="edit_supply"),
    path("dashboard/purchase-orders/", purchase_orders, name="purchase_orders"),
    path(
        "dashboard/purchase-orders/add/", add_purchase_order, name="add_purchase_order"
    ),
    path(
        "dashboard/purchase-orders/<int:order_id>/receive/",
        receive_purchase_order,
        name="receive_purchase_order",
    ),
    path("dashboard/suppliers/", supplier_list, name="supplier_list"),
    path("dashboard/suppliers/add/", add_supplier, name="add_supplier"),
    path(
        "dashboard/suppliers/<int:supplier_id>/edit/",
        edit_supplier,
        name="edit_supplier",
    ),
    path("dashboard/vehicles/", vehicle_list, name="vehicle_list"),
    path("dashboard/vehicles/add/", add_vehicle, name="add_vehicle"),
    path(
        "dashboard/vehicles/<int:vehicle_id>/edit/", edit_vehicle, name="edit_vehicle"
    ),
    path("dashboard/maintenance/", maintenance_list, name="maintenance_list"),
    path("dashboard/maintenance/add/", add_maintenance, name="add_maintenance"),
    path("dashboard/reminders/", reminder_centre, name="reminder_centre"),
    path(
        "dashboard/business-intelligence/",
        business_intelligence,
        name="business_intelligence",
    ),
    path(
        "dashboard/export-report/",
        export_business_report,
        name="export_business_report",
    ),
    path(
        "dashboard/email-report/", email_business_report, name="email_business_report"
    ),
    path(
        "dashboard/operations-centre/",
        operations_command_centre,
        name="operations_command_centre",
    ),
    path(
        "dashboard/customer-360/<int:customer_id>/", customer_360, name="customer_360"
    ),
    path(
        "dashboard/customer/<int:customer_id>/followup/",
        send_customer_followup,
        name="send_customer_followup",
    ),
    path(
        "dashboard/employee-performance-centre/",
        employee_performance_centre,
        name="employee_performance_centre",
    ),
    path(
        "dashboard/employee-performance/<int:employee_id>/",
        employee_performance_detail,
        name="employee_performance_detail",
    ),
    path(
        "dashboard/employee-performance/export-pdf/",
        export_employee_performance_pdf,
        name="export_employee_performance_pdf",
    ),
    path(
        "dashboard/employee-performance/email-report/",
        email_employee_performance_report,
        name="email_employee_performance_report",
=======
# Service Management Views
from .service_views import (
    service_list,
    add_service,
    edit_service,
    delete_service,
    toggle_service_status,
)

# Main Dashboard Views
from .views import (
    dashboard_home,
    export_quotes_csv,
    update_quote_status,
    lead_list,
    customer_list,
    add_customer,
    edit_customer,
    delete_customer,
    booking_list,
    add_booking,
    edit_booking,
    delete_booking,
    booking_calendar,
    employee_list,
    add_employee,
    edit_employee,
    delete_employee,
    gallery_list,
    add_gallery_item,
    edit_gallery_item,
    delete_gallery_item,
    site_images_list,
    add_site_image,
    edit_site_image,
    delete_site_image,
    web_image_posts_list,
    add_web_image_post,
    edit_web_image_post,
    delete_web_image_post,
    blog_post_list,
    add_blog_post,
    edit_blog_post,
    delete_blog_post,
    review_list,
    add_review,
    edit_review,
    delete_review,
    attendance_report,
    company_settings,
    employee_performance,
    activity_log_list,
    business_health,
    financial_dashboard,
    executive_dashboard,
    reminder_center,
    email_center,
    send_invoice_reminder,
    send_booking_reminder,
    send_quote_followup,
    email_log_list,
    customer_analytics,
    review_requests,
    send_review_request,
    review_analytics,
    customer_loyalty,
    customer_profile_360,
    employee_bonuses,
    campaign_center,
    send_vip_campaign,
    send_inactive_campaign,
    send_review_campaign,
    campaign_preview,
    campaign_performance,
    profit_loss_dashboard,
    business_kpis,
    employee_schedule,
    gst_report,
    finance_trends,
    update_booking_quick_status,
    equipment_list,
    add_equipment,
    edit_equipment,
    delete_equipment,
    reminder_centre,
    business_intelligence,
    export_business_report,
    email_business_report,
    operations_command_centre,
    receive_purchase_order,
    customer_360,
    send_customer_followup,
    employee_performance_centre,
    employee_performance_detail,
    export_employee_performance_pdf,
    email_employee_performance_report,
    employee_attendance_analytics,
    owner_command_centre,
    business_forecasting_centre,
    ai_quote_estimator,
    quote_conversion_analytics,
    quote_followup_centre,
    send_quote_followup_email,
    convert_quote_to_booking,
    create_invoice_from_booking,
    owner_alert_centre,
    customer_value_dashboard,
    vip_campaigns,
    job_profitability_dashboard,
    service_performance_dashboard,
    executive_bi_dashboard,
    employee_kpi_dashboard,
    staff_schedule_dashboard,
    sync_google_reviews_dashboard,
    dashboard_login,
    dashboard_logout,
    supplies_list,
    add_supply,
    edit_supply,
    purchase_orders,
    add_purchase_order,
    supplier_list,
    add_supplier,
    edit_supplier,
    vehicle_list,
    add_vehicle,
    edit_vehicle,
    maintenance_list,
    add_maintenance,
    reminder_centre,
    business_intelligence,
    export_business_report,
    email_business_report,
    operations_command_centre,
    receive_purchase_order,
    customer_360,
    send_customer_followup,
    employee_performance_centre,
    employee_performance_detail,
    export_employee_performance_pdf,
    email_employee_performance_report,
    employee_attendance_analytics,
    owner_command_centre,
    business_forecasting_centre,
    ai_quote_estimator,
    quote_conversion_analytics,
    quote_followup_centre,
    send_quote_followup_email,
    convert_quote_to_booking,
    create_invoice_from_booking,
    owner_alert_centre,
    customer_value_dashboard,
    vip_campaigns,
    job_profitability_dashboard,
    service_performance_dashboard,
    executive_bi_dashboard,
    employee_kpi_dashboard,
    staff_schedule_dashboard,
    sync_google_reviews_dashboard,
)


urlpatterns = [
    path("dashboard/login/", dashboard_login, name="dashboard_login"),
    path("dashboard/logout/", dashboard_logout, name="dashboard_logout"),
    path("dashboard/", dashboard_home, name="dashboard_home"),
    path("dashboard/settings/", company_settings, name="company_settings"),
    path("dashboard/leads/", lead_list, name="lead_list"),
    path("dashboard/update-status/<int:quote_id>/", update_quote_status, name="update_quote_status"),

    path("dashboard/customers/", customer_list, name="customer_list"),
    path("dashboard/customers/add/", add_customer, name="add_customer"),
    path("dashboard/customers/<int:customer_id>/edit/", edit_customer, name="edit_customer"),
    path("dashboard/customers/<int:customer_id>/delete/", delete_customer, name="delete_customer"),

    path("dashboard/bookings/", booking_list, name="booking_list"),
    path("dashboard/bookings/add/", add_booking, name="add_booking"),
    path("dashboard/bookings/<int:booking_id>/edit/", edit_booking, name="edit_booking"),
    path("dashboard/bookings/<int:booking_id>/delete/", delete_booking, name="delete_booking"),
    path("dashboard/calendar/", booking_calendar, name="booking_calendar"),

    path("dashboard/employees/", employee_list, name="employee_list"),
    path("dashboard/employees/add/", add_employee, name="add_employee"),
    path("dashboard/employees/<int:employee_id>/edit/", edit_employee, name="edit_employee"),
    path("dashboard/employees/<int:employee_id>/delete/", delete_employee, name="delete_employee"),

    path("dashboard/gallery/", gallery_list, name="gallery_list"),
    path("dashboard/gallery/add/", add_gallery_item, name="add_gallery_item"),
    path("dashboard/gallery/<int:item_id>/edit/", edit_gallery_item, name="edit_gallery_item"),
    path("dashboard/gallery/<int:item_id>/delete/", delete_gallery_item, name="delete_gallery_item"),

    # Site images management
    path("dashboard/site-images/", site_images_list, name="site_images_list"),
    path("dashboard/site-images/add/", add_site_image, name="add_site_image"),
    path("dashboard/site-images/<int:image_id>/edit/", edit_site_image, name="edit_site_image"),
    path("dashboard/site-images/<int:image_id>/delete/", delete_site_image, name="delete_site_image"),
    # Web Image Post - unified view for web image uploads
    path("dashboard/web-image-posts/", web_image_posts_list, name="web_image_posts_list"),
    path("dashboard/web-image-posts/add/", add_web_image_post, name="add_web_image_post"),
    path("dashboard/web-image-posts/<int:image_id>/edit/", edit_web_image_post, name="edit_web_image_post"),
    path("dashboard/web-image-posts/<int:image_id>/delete/", delete_web_image_post, name="delete_web_image_post"),

    path("dashboard/reviews/", review_list, name="review_list"),
    path("dashboard/reviews/add/", add_review, name="add_review"),
    path("dashboard/reviews/<int:review_id>/edit/", edit_review, name="edit_review"),
    path("dashboard/reviews/<int:review_id>/delete/", delete_review, name="delete_review"),
    path("dashboard/performance/", employee_performance, name="employee_performance"),

    # Blog posts management
    path("dashboard/blog/", blog_post_list, name="blog_post_list"),
    path("dashboard/blog/add/", add_blog_post, name="add_blog_post"),
    path("dashboard/blog/<int:post_id>/edit/", edit_blog_post, name="edit_blog_post"),
    path("dashboard/blog/<int:post_id>/delete/", delete_blog_post, name="delete_blog_post"),

    path("dashboard/export-quotes/", export_quotes_csv, name="export_quotes_csv"),
    
    path("dashboard/attendance/", attendance_report, name="attendance_report"),
    path("dashboard/activity/",activity_log_list,name="activity_log_list"),
    path("dashboard/business-health/",business_health,name="business_health"),
    path("dashboard/financials/",financial_dashboard,name="financial_dashboard"),
    path("dashboard/executive/",executive_dashboard,name="executive_dashboard"),
    path("dashboard/reminders/",reminder_center,name="reminder_center"),


    path("dashboard/email-center/", email_center, name="email_center"),

    path(
        "dashboard/email-center/invoice/<int:invoice_id>/send/",
        send_invoice_reminder,
        name="send_invoice_reminder"
    ),

    path(
        "dashboard/email-center/booking/<int:booking_id>/send/",
        send_booking_reminder,
        name="send_booking_reminder"
    ),

    path(
        "dashboard/email-center/quote/<int:quote_id>/send/",
        send_quote_followup,
        name="send_quote_followup"
    ),

    path("dashboard/email-logs/",email_log_list,name="email_log_list"),
    path("dashboard/customer-analytics/",customer_analytics,name="customer_analytics"),

    path(
    "dashboard/review-requests/",
    review_requests,
    name="review_requests"
    ),

    path(
        "dashboard/review-requests/send/<int:booking_id>/",
        send_review_request,
        name="send_review_request"
    ),
    path("dashboard/review-analytics/",review_analytics,name="review_analytics"),
    path("dashboard/customer-loyalty/",customer_loyalty,name="customer_loyalty"),
    path("dashboard/customer/<int:customer_id>/",customer_profile_360,name="customer_profile_360"),
    path("dashboard/employee-bonuses/",employee_bonuses,name="employee_bonuses"),
    path("dashboard/campaigns/",campaign_center,name="campaign_center"),
    path("dashboard/campaigns/send-vip/", send_vip_campaign, name="send_vip_campaign"),
    path("dashboard/campaigns/send-inactive/", send_inactive_campaign, name="send_inactive_campaign"),
    path("dashboard/campaigns/send-review/", send_review_campaign, name="send_review_campaign"),
    path("dashboard/campaigns/preview/<str:campaign_type>/",campaign_preview,name="campaign_preview"),
    path("dashboard/campaign-performance/",campaign_performance,name="campaign_performance"),
    path("dashboard/profit-loss/",profit_loss_dashboard,name="profit_loss_dashboard"),
    path("dashboard/business-kpis/",business_kpis,name="business_kpis"),
    path("dashboard/employee-schedule/",employee_schedule,name="employee_schedule"),
    path("dashboard/gst-report/",gst_report,name="gst_report"),
    path("dashboard/finance-trends/",finance_trends,name="finance_trends"),
    path("dashboard/bookings/<int:booking_id>/quick-status/<str:new_status>/",update_booking_quick_status,name="update_booking_quick_status"),
    path("dashboard/equipment/", equipment_list, name="equipment_list"),
    path("dashboard/equipment/add/", add_equipment, name="add_equipment"),
    path("dashboard/equipment/<int:equipment_id>/edit/", edit_equipment, name="edit_equipment"),
    path("dashboard/equipment/<int:equipment_id>/delete/", delete_equipment, name="delete_equipment"),

    path(
        "dashboard/supplies/",
        supplies_list,
        name="supplies_list"
    ),

    path(
        "dashboard/supplies/add/",
        add_supply,
        name="add_supply"
    ),

    path(
        "dashboard/supplies/<int:supply_id>/edit/",
        edit_supply,
        name="edit_supply"
    ),


    path(
    "dashboard/purchase-orders/",
    purchase_orders,
    name="purchase_orders"
    ),

    path(
        "dashboard/purchase-orders/add/",
        add_purchase_order,
        name="add_purchase_order"
    ),

    path(
        "dashboard/purchase-orders/<int:order_id>/receive/",
        receive_purchase_order,
        name="receive_purchase_order"
    ),

    path("dashboard/suppliers/", supplier_list, name="supplier_list"),
    path("dashboard/suppliers/add/", add_supplier, name="add_supplier"),
    path("dashboard/suppliers/<int:supplier_id>/edit/", edit_supplier, name="edit_supplier"),
    path("dashboard/vehicles/", vehicle_list, name="vehicle_list"),
    path("dashboard/vehicles/add/", add_vehicle, name="add_vehicle"),
    path("dashboard/vehicles/<int:vehicle_id>/edit/", edit_vehicle, name="edit_vehicle"),

    path(
        "dashboard/maintenance/",
        maintenance_list,
        name="maintenance_list"
    ),

    path(
        "dashboard/maintenance/add/",
        add_maintenance,
        name="add_maintenance"
    ),

    path(
    "dashboard/reminders/",
    reminder_centre,
    name="reminder_centre"
    ),  

    path(
    "dashboard/business-intelligence/",
    business_intelligence,
    name="business_intelligence"
    ),
    path(
    "dashboard/export-report/",
    export_business_report,
    name="export_business_report"
    ),
    path(
    "dashboard/email-report/",
    email_business_report,
    name="email_business_report"
    ),

    path(
    "dashboard/operations-centre/",
    operations_command_centre,
    name="operations_command_centre"
    ),

    path(
    "dashboard/customer-360/<int:customer_id>/",
    customer_360,
    name="customer_360"
    ),

    path(
    "dashboard/customer/<int:customer_id>/followup/",
    send_customer_followup,
    name="send_customer_followup"
    ),  

    path(
    "dashboard/employee-performance-centre/",
    employee_performance_centre,
    name="employee_performance_centre"
    ),

    path(
    "dashboard/employee-performance/<int:employee_id>/",
    employee_performance_detail,
    name="employee_performance_detail"
    ),

    path(
    "dashboard/employee-performance/export-pdf/",
    export_employee_performance_pdf,
    name="export_employee_performance_pdf"
    ),

    path(
    "dashboard/employee-performance/email-report/",
    email_employee_performance_report,
    name="email_employee_performance_report"
>>>>>>> 5815f15 (Initial project commit)
    ),
    path(
        "dashboard/employee-attendance-analytics/",
        employee_attendance_analytics,
<<<<<<< HEAD
        name="employee_attendance_analytics",
=======
        name="employee_attendance_analytics"
>>>>>>> 5815f15 (Initial project commit)
    ),
    path(
        "dashboard/owner-command-centre/",
        owner_command_centre,
<<<<<<< HEAD
        name="owner_command_centre",
    ),
    path(
        "dashboard/business-forecasting/",
        business_forecasting_centre,
        name="business_forecasting_centre",
    ),
    path(
        "dashboard/ai-quote-estimator/", ai_quote_estimator, name="ai_quote_estimator"
    ),
    path(
        "dashboard/quote-conversion-analytics/",
        quote_conversion_analytics,
        name="quote_conversion_analytics",
    ),
    path(
        "dashboard/quote-followups/",
        quote_followup_centre,
        name="quote_followup_centre",
    ),
    path(
        "dashboard/quote-followups/send/<int:quote_id>/",
        send_quote_followup_email,
        name="send_quote_followup_email",
    ),
    path(
        "dashboard/quotes/convert/<int:quote_id>/",
        convert_quote_to_booking,
        name="convert_quote_to_booking",
    ),
    path(
        "dashboard/bookings/<int:booking_id>/create-invoice/",
        create_invoice_from_booking,
        name="create_invoice_from_booking",
    ),
    path("dashboard/owner-alerts/", owner_alert_centre, name="owner_alert_centre"),
    path(
        "dashboard/customer-value/",
        customer_value_dashboard,
        name="customer_value_dashboard",
    ),
    path("dashboard/vip-campaigns/", vip_campaigns, name="vip_campaigns"),
    path("dashboard/vip-campaigns/send/", send_vip_campaign, name="send_vip_campaign"),
    path(
        "dashboard/job-profitability/",
        job_profitability_dashboard,
        name="job_profitability_dashboard",
    ),
    path(
        "dashboard/service-performance/",
        service_performance_dashboard,
        name="service_performance_dashboard",
    ),
    path(
        "dashboard/executive-bi/", executive_bi_dashboard, name="executive_bi_dashboard"
    ),
    path(
        "dashboard/employee-kpi/", employee_kpi_dashboard, name="employee_kpi_dashboard"
    ),
    path(
        "dashboard/staff-schedule/",
        staff_schedule_dashboard,
        name="staff_schedule_dashboard",
    ),
]
=======
        name="owner_command_centre"
    ),

    path(
    "dashboard/business-forecasting/",
    business_forecasting_centre,
    name="business_forecasting_centre"
    ),

    path(
    "dashboard/ai-quote-estimator/",
    ai_quote_estimator,
    name="ai_quote_estimator"
    ),

    path(
    "dashboard/quote-conversion-analytics/",
    quote_conversion_analytics,
    name="quote_conversion_analytics"
    ),

    path(
    "dashboard/quote-followups/",
    quote_followup_centre,
    name="quote_followup_centre"
    ),

    path(
        "dashboard/quote-followups/send/<int:quote_id>/",
        send_quote_followup_email,
        name="send_quote_followup_email"
    ),

    path(
    "dashboard/quotes/convert/<int:quote_id>/",
    convert_quote_to_booking,
    name="convert_quote_to_booking"
    ),

    path(
    "dashboard/bookings/<int:booking_id>/create-invoice/",
    create_invoice_from_booking,
    name="create_invoice_from_booking"
    ),

    path(
        "dashboard/owner-alerts/",
        owner_alert_centre,
        name="owner_alert_centre"
    ),

    path(
        "dashboard/customer-value/",
        customer_value_dashboard,
        name="customer_value_dashboard"
    ),

    path(
        "dashboard/vip-campaigns/",
        vip_campaigns,
        name="vip_campaigns"
    ),
    path("dashboard/vip-campaigns/send/",send_vip_campaign,name="send_vip_campaign"),
    path("dashboard/job-profitability/",job_profitability_dashboard,name="job_profitability_dashboard"),
    path("dashboard/service-performance/",service_performance_dashboard,name="service_performance_dashboard"),
    path("dashboard/executive-bi/",executive_bi_dashboard,name="executive_bi_dashboard"),
    path("dashboard/employee-kpi/",employee_kpi_dashboard,name="employee_kpi_dashboard"),
    path("dashboard/staff-schedule/",staff_schedule_dashboard,name="staff_schedule_dashboard"),
    path("sync-google-reviews/",sync_google_reviews_dashboard,name="sync_google_reviews_dashboard"),
    
    # Service Management Routes
    path("dashboard/services/", service_list, name="dashboard_service_list"),
    path("dashboard/services/add/", add_service, name="dashboard_add_service"),
    path("dashboard/services/<int:service_id>/edit/", edit_service, name="dashboard_edit_service"),
    path("dashboard/services/<int:service_id>/delete/", delete_service, name="dashboard_delete_service"),
    path("dashboard/services/<int:service_id>/toggle-status/", toggle_service_status, name="dashboard_toggle_service_status"),
]


>>>>>>> 5815f15 (Initial project commit)
