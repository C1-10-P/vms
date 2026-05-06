from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import EdgeNode, NodeHeartbeat, NodeHealth, FirmwareVersion, OTASession, NodeConfiguration
from .forms import EdgeNodeForm, FirmwareUploadForm, NodeConfigurationForm
from .services import DeviceService, OTAService


# ============ Node Management Views ============

class EdgeNodeListView(LoginRequiredMixin, ListView):
    """List all edge nodes"""
    model = EdgeNode
    ordering = ['-created_at']
    template_name = 'devices/node_list.html'
    context_object_name = 'nodes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by type
        node_type = self.request.GET.get('node_type')
        if node_type:
            queryset = queryset.filter(node_type=node_type)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(node_uuid__icontains=search) |
                Q(mac_address__icontains=search)
            )
        
        return queryset.select_related('zone', 'institution')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.access.models import AccessZone
        from apps.core.models import Institution
        
        context['zones'] = AccessZone.objects.filter(is_active=True)
        context['institutions'] = Institution.objects.filter(is_active=True)
        context['total_nodes'] = EdgeNode.objects.count()
        context['online_nodes'] = EdgeNode.objects.filter(status='online').count()
        context['offline_nodes'] = EdgeNode.objects.filter(status='offline').count()
        context['maintenance_nodes'] = EdgeNode.objects.filter(status='maintenance').count()
        return context


class EdgeNodeDetailView(LoginRequiredMixin, DetailView):
    """Edge node detail view"""
    model = EdgeNode
    template_name = 'devices/node_detail.html'
    context_object_name = 'node'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent heartbeats
        context['recent_heartbeats'] = NodeHeartbeat.objects.filter(
            node=self.object
        ).order_by('-timestamp')[:20]
        
        # Get health status
        context['health'] = NodeHealth.objects.filter(node=self.object).first()
        
        # Get configuration
        context['config'] = NodeConfiguration.objects.filter(node=self.object).first()
        
        # Get OTA sessions
        context['ota_sessions'] = OTASession.objects.filter(node=self.object).order_by('-started_at')[:10]
        
        # Calculate uptime percentage
        heartbeats = NodeHeartbeat.objects.filter(node=self.object, timestamp__gte=timezone.now() - timezone.timedelta(days=7))
        if heartbeats.exists():
            context['uptime_percentage'] = (heartbeats.count() / (24 * 7 * 6)) * 100  # Assuming 10-min intervals
        else:
            context['uptime_percentage'] = 0
        
        return context


class EdgeNodeCreateView(LoginRequiredMixin, CreateView):
    """Create new edge node"""
    model = EdgeNode
    form_class = EdgeNodeForm
    template_name = 'devices/node_form.html'
    success_url = reverse_lazy('devices:node_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Edge node {form.instance.name} created successfully.')
        return super().form_valid(form)


class EdgeNodeUpdateView(LoginRequiredMixin, UpdateView):
    """Update edge node"""
    model = EdgeNode
    form_class = EdgeNodeForm
    template_name = 'devices/node_form.html'
    
    def get_success_url(self):
        return reverse_lazy('devices:node_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Edge node {form.instance.name} updated successfully.')
        return super().form_valid(form)


class EdgeNodeDeleteView(LoginRequiredMixin, DeleteView):
    """Delete edge node (soft delete)"""
    model = EdgeNode
    template_name = 'devices/node_confirm_delete.html'
    success_url = reverse_lazy('devices:node_list')
    
    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        node.soft_delete()
        messages.success(request, f'Edge node {node.name} has been archived.')
        return redirect(self.success_url)


@permission_required(VMSPermissions.DEVICE_REBOOT)
def node_reboot(request, pk):
    """Reboot an edge node"""
    node = get_object_or_404(EdgeNode, pk=pk)
    
    # Send reboot command via MQTT
    from apps.firmware.mqtt_client import mqtt_client
    mqtt_client.publish(f'jkuat/system/commands/{node.node_uuid}', {
        'command': 'reboot',
        'timestamp': timezone.now().isoformat()
    })
    
    messages.success(request, f'Reboot command sent to {node.name}')
    return redirect('devices:node_detail', pk=pk)


@permission_required(VMSPermissions.DEVICE_CONFIGURE)
def node_configure(request, pk):
    """Configure an edge node"""
    node = get_object_or_404(EdgeNode, pk=pk)
    
    if request.method == 'POST':
        form = NodeConfigurationForm(request.POST)
        if form.is_valid():
            config, created = NodeConfiguration.objects.update_or_create(
                node=node,
                defaults={
                    'version': form.cleaned_data['version'],
                    'scan_interval_seconds': form.cleaned_data['scan_interval_seconds'],
                    'ble_scan_duration': form.cleaned_data['ble_scan_duration'],
                    'log_level': form.cleaned_data['log_level'],
                    'custom_settings': form.cleaned_data['custom_settings']
                }
            )
            
            # Send config via MQTT
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f'jkuat/system/config/{node.node_uuid}', config.to_dict())
            
            messages.success(request, f'Configuration sent to {node.name}')
            return redirect('devices:node_detail', pk=pk)
    else:
        form = NodeConfigurationForm(instance=NodeConfiguration.objects.filter(node=node).first())
    
    return render(request, 'devices/node_configure.html', {'form': form, 'node': node})


# ============ Device Monitoring Views ============

class DeviceMonitorView(LoginRequiredMixin, TemplateView):
    """Device monitoring dashboard"""
    template_name = 'devices/monitor.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all nodes with their latest heartbeat
        nodes = EdgeNode.objects.filter(is_active=True)
        
        context['nodes'] = nodes
        context['online_count'] = nodes.filter(status='online').count()
        context['offline_count'] = nodes.filter(status='offline').count()
        context['critical_count'] = NodeHealth.objects.filter(health_status='critical').count()
        
        # Get average metrics
        context['avg_battery'] = nodes.aggregate(Avg('battery_level'))['battery_level__avg']
        context['avg_uptime'] = NodeHeartbeat.objects.aggregate(Avg('uptime_seconds'))['uptime_seconds__avg']
        
        return context


def device_health_dashboard(request):
    """Device health dashboard"""
    nodes = EdgeNode.objects.filter(is_active=True)
    health_data = []
    
    for node in nodes:
        health = NodeHealth.objects.filter(node=node).first()
        health_data.append({
            'name': node.name,
            'status': node.status,
            'health': health.health_status if health else 'unknown',
            'last_heartbeat': node.last_heartbeat,
            'battery': node.battery_level
        })
    
    return render(request, 'devices/health_dashboard.html', {'health_data': health_data})


def heartbeat_list(request):
    """List of heartbeats"""
    heartbeats = NodeHeartbeat.objects.select_related('node').order_by('-timestamp')[:100]
    return render(request, 'devices/heartbeat_list.html', {'heartbeats': heartbeats})


def device_alerts(request):
    """Device alerts view"""
    from apps.vms.models import VisitorAlert
    
    alerts = VisitorAlert.objects.filter(
        alert_type__in=['low_battery', 'tag_lost'],
        status='new'
    ).select_related('tag')
    
    return render(request, 'devices/alerts.html', {'alerts': alerts})


# ============ Firmware Management Views ============

class FirmwareListView(LoginRequiredMixin, ListView):
    """List firmware versions"""
    model = FirmwareVersion
    ordering = ['-created_at']
    template_name = 'devices/firmware_list.html'
    context_object_name = 'firmware'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.firmware.models import EdgeNode
        
        context['nodes'] = EdgeNode.objects.filter(is_active=True)
        context['total_versions'] = FirmwareVersion.objects.count()
        context['stable_count'] = FirmwareVersion.objects.filter(stability='stable').count()
        context['beta_alpha_count'] = FirmwareVersion.objects.filter(stability__in=['beta', 'alpha']).count()
       
        context['now'] = timezone.now()
        return context


class FirmwareDetailView(LoginRequiredMixin, DetailView):
    """Firmware detail view"""
    model = FirmwareVersion
    template_name = 'devices/firmware_detail.html'
    context_object_name = 'firmware'


class FirmwareUploadView(LoginRequiredMixin, CreateView):
    """Upload new firmware"""
    model = FirmwareVersion
    form_class = FirmwareUploadForm
    template_name = 'devices/firmware_upload.html'
    success_url = reverse_lazy('devices:firmware_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Firmware {form.instance.version} uploaded successfully.')
        return super().form_valid(form)


@permission_required(VMSPermissions.DEVICE_UPDATE_FIRMWARE)
def firmware_deploy(request, pk):
    """Deploy firmware to nodes"""
    firmware = get_object_or_404(FirmwareVersion, pk=pk)
    
    if request.method == 'POST':
        node_ids = request.POST.getlist('nodes')
        nodes = EdgeNode.objects.filter(id__in=node_ids)
        
        ota_service = OTAService()
        result = ota_service.deploy_firmware(firmware, nodes, request.user)
        
        messages.success(request, f'Firmware deployment started for {result["deployed"]} nodes.')
        return redirect('devices:ota_list')
    
    nodes = EdgeNode.objects.filter(is_active=True)
    return render(request, 'devices/firmware_deploy.html', {'firmware': firmware, 'nodes': nodes})


@permission_required(VMSPermissions.DEVICE_UPDATE_FIRMWARE)
def firmware_rollback(request, pk):
    """Rollback firmware version"""
    firmware = get_object_or_404(FirmwareVersion, pk=pk)
    
    # Get previous version
    previous = FirmwareVersion.objects.filter(
        node_type=firmware.node_type,
        release_date__lt=firmware.release_date
    ).order_by('-release_date').first()
    
    if previous:
        ota_service = OTAService()
        result = ota_service.rollback_firmware(previous, firmware, request.user)
        messages.success(request, f'Rollback to {previous.version} initiated.')
    else:
        messages.error(request, 'No previous version found for rollback.')
    
    return redirect('devices:firmware_list')


# ============ OTA Update Views ============

class OTASessionListView(LoginRequiredMixin, ListView):
    """List OTA sessions"""
    model = OTASession
    ordering = ['-created_at']
    template_name = 'devices/ota_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        return super().get_queryset().order_by('-started_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.firmware.models import EdgeNode, FirmwareVersion
        
        context['nodes'] = EdgeNode.objects.filter(is_active=True)
        context['firmwares'] = FirmwareVersion.objects.filter(is_active=True)
        context['total_sessions'] = OTASession.objects.count()
        context['success_count'] = OTASession.objects.filter(status='success').count()
        context['failed_count'] = OTASession.objects.filter(status='failed').count()
        context['in_progress_count'] = OTASession.objects.filter(status__in=['pending', 'downloading', 'updating']).count()
        return context


class OTASessionDetailView(LoginRequiredMixin, DetailView):
    """OTA session detail"""
    model = OTASession
    template_name = 'devices/ota_detail.html'
    context_object_name = 'session'


class OTASessionCreateView(LoginRequiredMixin, CreateView):
    """Create OTA session"""
    model = OTASession
    fields = ['node', 'firmware']
    template_name = 'devices/ota_form.html'
    success_url = reverse_lazy('devices:ota_list')
    
    def form_valid(self, form):
        form.instance.initiated_by = self.request.user.person.staff
        form.instance.initiated_via = 'web'
        messages.success(self.request, f'OTA update initiated for {form.instance.node.name}')
        return super().form_valid(form)


def ota_cancel(request, pk):
    """Cancel OTA session"""
    session = get_object_or_404(OTASession, pk=pk)
    session.status = 'cancelled'
    session.save()
    messages.success(request, f'OTA session cancelled.')
    return redirect('devices:ota_detail', pk=pk)


# ============ Report Views ============

class DeviceReportView(LoginRequiredMixin, TemplateView):
    """Device reports"""
    template_name = 'devices/report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Summary statistics
        context['total_devices'] = EdgeNode.objects.count()
        context['online_devices'] = EdgeNode.objects.filter(status='online').count()
        context['offline_devices'] = EdgeNode.objects.filter(status='offline').count()
        
        # By type
        context['by_type'] = list(EdgeNode.objects.values('node_type').annotate(count=Count('id')))
        
        # By status
        context['by_status'] = list(EdgeNode.objects.values('status').annotate(count=Count('id')))
        
        return context


def device_performance_report(request):
    """Device performance report"""
    from datetime import timedelta
    days = int(request.GET.get('days', 7))
    cutoff = timezone.now() - timedelta(days=days)
    
    heartbeats = NodeHeartbeat.objects.filter(timestamp__gte=cutoff)
    
    report = {
        'period_days': days,
        'total_heartbeats': heartbeats.count(),
        'avg_uptime': heartbeats.aggregate(Avg('uptime_seconds'))['uptime_seconds__avg'],
        'avg_battery': heartbeats.aggregate(Avg('battery_level'))['battery_level__avg'],
        'by_node': list(heartbeats.values('node__name').annotate(
            avg_uptime=Avg('uptime_seconds'),
            avg_battery=Avg('battery_level')
        ))
    }
    
    return JsonResponse(report)


def uptime_report(request):
    """Uptime report"""
    nodes = EdgeNode.objects.filter(is_active=True)
    report = []
    
    for node in nodes:
        heartbeats = NodeHeartbeat.objects.filter(node=node, timestamp__gte=timezone.now() - timezone.timedelta(days=30))
        uptime_percentage = (heartbeats.count() / (30 * 24 * 6)) * 100 if heartbeats.exists() else 0
        
        report.append({
            'node': node.name,
            'status': node.status,
            'last_heartbeat': node.last_heartbeat,
            'uptime_percentage': round(uptime_percentage, 2)
        })
    
    return render(request, 'devices/uptime_report.html', {'report': report})


# ============ Export Views ============

@permission_required(VMSPermissions.DEVICE_VIEW)
def export_devices_csv(request):
    """Export devices to CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="devices.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Type', 'Status', 'MAC Address', 'IP Address', 'Last Heartbeat', 'Battery'])
    
    for node in EdgeNode.objects.filter(is_active=True):
        writer.writerow([
            node.name,
            node.get_node_type_display(),
            node.status,
            node.mac_address,
            node.ip_address or '',
            node.last_heartbeat,
            f"{node.battery_level}%" if node.battery_level else ''
        ])
    
    return response


def export_health_report(request):
    """Export health report to Excel"""
    from openpyxl import Workbook
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Device Health"
    
    headers = ['Node', 'Type', 'Status', 'Health', 'Last Heartbeat', 'Uptime (days)', 'Battery']
    ws.append(headers)
    
    for node in EdgeNode.objects.filter(is_active=True):
        health = NodeHealth.objects.filter(node=node).first()
        uptime_days = node.uptime_seconds / 86400 if node.uptime_seconds else 0
        
        ws.append([
            node.name,
            node.get_node_type_display(),
            node.status,
            health.health_status if health else 'Unknown',
            node.last_heartbeat,
            round(uptime_days, 1),
            f"{node.battery_level}%" if node.battery_level else 'N/A'
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="device_health.xlsx"'
    wb.save(response)
    return response


# ============ API Endpoints ============

@csrf_exempt
def api_heartbeat(request):
    """API endpoint for device heartbeat"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        node_uuid = data.get('node_uuid')
        
        node = EdgeNode.objects.get(node_uuid=node_uuid)
        node.update_heartbeat(data)
        
        # Create heartbeat record
        NodeHeartbeat.objects.create(
            node=node,
            timestamp=timezone.now(),
            uptime_seconds=data.get('uptime', 0),
            free_heap=data.get('free_heap', 0),
            rssi=data.get('rssi'),
            battery_level=data.get('battery'),
            temperature=data.get('temperature')
        )
        
        return JsonResponse({'status': 'ok'})
    except EdgeNode.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_register_device(request):
    """API endpoint for device registration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        node = EdgeNode.objects.create(
            node_uuid=data.get('node_uuid'),
            node_type=data.get('node_type'),
            name=data.get('name', data.get('node_uuid')[:8]),
            mac_address=data.get('mac_address'),
            firmware_version=data.get('firmware_version', '1.0.0'),
            has_camera=data.get('has_camera', False),
            has_ble=data.get('has_ble', False),
            status='online'
        )
        
        return JsonResponse({
            'success': True,
            'node_id': node.id,
            'config': {
                'scan_interval': 30,
                'log_level': 'info'
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_device_status(request, node_uuid):
    """Get device status"""
    try:
        node = EdgeNode.objects.get(node_uuid=node_uuid)
        return JsonResponse({
            'status': node.status,
            'last_heartbeat': node.last_heartbeat,
            'firmware': node.firmware_version,
            'battery': node.battery_level,
            'uptime': node.uptime_seconds
        })
    except EdgeNode.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)


@csrf_exempt
def api_device_config(request, node_uuid):
    """Get or update device configuration"""
    try:
        node = EdgeNode.objects.get(node_uuid=node_uuid)
        
        if request.method == 'GET':
            config = NodeConfiguration.objects.filter(node=node).first()
            return JsonResponse(config.to_dict() if config else {})
        
        elif request.method == 'POST':
            data = json.loads(request.body)
            config, created = NodeConfiguration.objects.update_or_create(
                node=node,
                defaults={
                    'version': data.get('version', '1.0.0'),
                    'scan_interval_seconds': data.get('scan_interval', 30),
                    'log_level': data.get('log_level', 'info'),
                    'custom_settings': data.get('custom_settings', {})
                }
            )
            return JsonResponse({'success': True})
        
    except EdgeNode.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)


@csrf_exempt
def api_send_command(request, node_uuid):
    """Send command to device"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        node = EdgeNode.objects.get(node_uuid=node_uuid)
        data = json.loads(request.body)
        command = data.get('command')
        
        from apps.firmware.mqtt_client import mqtt_client
        mqtt_client.publish(f'jkuat/system/commands/{node.node_uuid}', {
            'command': command,
            'params': data.get('params', {}),
            'timestamp': timezone.now().isoformat()
        })
        
        return JsonResponse({'success': True, 'command_sent': command})
    except EdgeNode.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)


# ============ AJAX Endpoints ============

def ajax_node_status(request):
    """Get status of all nodes for dashboard"""
    nodes = EdgeNode.objects.filter(is_active=True).values('id', 'name', 'status', 'last_heartbeat', 'battery_level')
    return JsonResponse({'nodes': list(nodes)})


@csrf_exempt
def ajax_update_heartbeat(request):
    """Update node heartbeat via AJAX"""
    if request.method == 'POST':
        node_id = request.POST.get('node_id')
        node = get_object_or_404(EdgeNode, pk=node_id)
        node.last_heartbeat = timezone.now()
        node.status = 'online'
        node.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid method'}, status=405)


def ajax_node_metrics(request, pk):
    """Get node metrics for charts"""
    node = get_object_or_404(EdgeNode, pk=pk)
    
    # Get last 24 hours of heartbeats
    heartbeats = NodeHeartbeat.objects.filter(
        node=node,
        timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('timestamp')
    
    metrics = {
        'timestamps': [h.timestamp.strftime('%H:%M') for h in heartbeats],
        'battery': [h.battery_level for h in heartbeats],
        'rssi': [h.rssi for h in heartbeats],
        'uptime': [h.uptime_seconds / 3600 for h in heartbeats]  # Convert to hours
    }
    
    return JsonResponse(metrics)

def get_monitor_stats(request):
    """AJAX endpoint for real-time monitor stats"""
    nodes = EdgeNode.objects.filter(is_active=True)
    return JsonResponse({
        'online_count': nodes.filter(status='online').count(),
        'offline_count': nodes.filter(status='offline').count(),
        'critical_count': NodeHealth.objects.filter(health_status='critical').count(),
        'avg_battery': nodes.aggregate(Avg('battery_level'))['battery_level__avg'] or 0,
        'avg_uptime': NodeHeartbeat.objects.aggregate(Avg('uptime_seconds'))['uptime_seconds__avg'] or 0,
    })

def firmware_promote(request, pk):
    if request.method == 'POST':
        try:
            firmware = FirmwareVersion.objects.get(pk=pk)
            firmware.stability = 'stable'
            firmware.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


def firmware_deprecate(request, pk):
    if request.method == 'POST':
        try:
            firmware = FirmwareVersion.objects.get(pk=pk)
            firmware.stability = 'deprecated'
            firmware.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

def get_node_detail_json(request, pk):
    """Return node details as JSON for modal"""
    node = get_object_or_404(EdgeNode.objects.select_related(
        'institution', 'college', 'school', 'department', 'zone'
    ), pk=pk)
    
    return JsonResponse({
        'id': node.id,
        'node_uuid': node.node_uuid,
        'name': node.name,
        'node_type': node.node_type,
        'node_type_display': node.get_node_type_display(),
        'status': node.status,
        'status_display': node.get_status_display(),
        'model': node.model,
        'serial_number': node.serial_number,
        'hardware_version': node.hardware_version,
        'firmware_version': node.firmware_version,
        'ip_address': node.ip_address,
        'mac_address': node.mac_address,
        'wifi_ssid': node.wifi_ssid,
        'wifi_rssi': node.wifi_rssi,
        'institution_name': node.institution.name if node.institution else None,
        'college_name': node.college.name if node.college else None,
        'school_name': node.school.name if node.school else None,
        'department_name': node.department.name if node.department else None,
        'zone_name': node.zone.name if node.zone else None,
        'location_description': node.location_description,
        'latitude': float(node.latitude) if node.latitude else None,
        'longitude': float(node.longitude) if node.longitude else None,
        'power_source': node.power_source,
        'power_source_display': node.get_power_source_display(),
        'battery_level': node.battery_level,
        'battery_voltage': float(node.battery_voltage) if node.battery_voltage else None,
        'cpu_usage': float(node.cpu_usage) if node.cpu_usage else None,
        'temperature': float(node.temperature) if node.temperature else None,
        'uptime_seconds': node.uptime_seconds,
        'has_camera': node.has_camera,
        'has_ble': node.has_ble,
        'has_rfid': node.has_rfid,
        'has_pir': node.has_pir,
        'has_led': node.has_led,
        'has_buzzer': node.has_buzzer,
        'total_events': node.total_events,
        'total_errors': node.total_errors,
        'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
        'last_event_time': node.last_event_time.isoformat() if node.last_event_time else None,
        'config_version': node.config_version,
        'config': node.config,
    })