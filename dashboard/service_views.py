"""
Service Management Views for Dashboard
File: dashboard/service_views.py
Purpose: Views for managing services through the dashboard interface
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from services.models import Service
from .service_forms import ServiceForm
import json


@login_required
def service_list(request):
    """List all services in dashboard"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard_home')
    
    services = Service.objects.all().order_by('-updated_at')
    
    context = {
        'services': services,
        'page_title': 'Service Management',
    }
    return render(request, 'dashboard/services/service_list.html', context)


@login_required
def add_service(request):
    """Add a new service"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service "{service.name}" created successfully!')
            return redirect('dashboard_service_list')
    else:
        form = ServiceForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Service',
        'action': 'Add',
    }
    return render(request, 'dashboard/services/service_form.html', context)


@login_required
def edit_service(request, service_id):
    """Edit an existing service"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard_home')
    
    service = get_object_or_404(Service, id=service_id)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service "{service.name}" updated successfully!')
            return redirect('dashboard_service_list')
    else:
        # Pre-populate the form with existing data
        initial_data = {
            'included_items': '\n'.join(service.included) if service.included else '',
            'packages_json': json.dumps(service.packages, indent=2) if service.packages else '',
        }
        form = ServiceForm(instance=service, initial=initial_data)
    
    context = {
        'form': form,
        'service': service,
        'page_title': f'Edit {service.name}',
        'action': 'Edit',
    }
    return render(request, 'dashboard/services/service_form.html', context)


@login_required
def delete_service(request, service_id):
    """Delete a service"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard_home')
    
    service = get_object_or_404(Service, id=service_id)
    service_name = service.name
    service.delete()
    messages.success(request, f'Service "{service_name}" deleted successfully!')
    return redirect('dashboard_service_list')


@login_required
def toggle_service_status(request, service_id):
    """Toggle service active/inactive status (AJAX)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    service = get_object_or_404(Service, id=service_id)
    service.is_active = not service.is_active
    service.save()
    
    return JsonResponse({
        'success': True,
        'is_active': service.is_active,
        'message': f'Service "{service.name}" is now {"active" if service.is_active else "inactive"}.'
    })
