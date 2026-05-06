from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import Institution, College, School, Department, Program, Student, Staff
from .services import InstitutionService, CollegeService, SchoolService, DepartmentService, ProgramService
from .forms import InstitutionForm, CollegeForm, SchoolForm, DepartmentForm, ProgramForm


# ============ Institution CRUD ============

class InstitutionListView(LoginRequiredMixin, ListView):
    """
    List all institutions
    """
    model = Institution
    template_name = 'core/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20
    
    @permission_required(VMSPermissions.SYSTEM_MANAGE_USERS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(abbreviation__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Institutions'
        context['total_count'] = Institution.objects.filter(is_active=True).count()
        return context


class InstitutionDetailView(LoginRequiredMixin, DetailView):
    """
    Institution detail view with statistics
    """
    model = Institution
    template_name = 'core/institution_detail.html'
    context_object_name = 'institution'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['college_count'] = self.object.colleges.filter(is_active=True).count()
        context['school_count'] = School.objects.filter(
            college__institution=self.object,
            is_active=True
        ).count()
        context['department_count'] = Department.objects.filter(
            school__college__institution=self.object,
            is_active=True
        ).count()
        context['student_count'] = Student.objects.filter(
            institution=self.object,
            is_active=True
        ).count()
        context['staff_count'] = Staff.objects.filter(
            institution=self.object,
            is_active=True
        ).count()
        
        # Recent activity
        from apps.classroom.models import ClassAttendance
        context['recent_attendance'] = ClassAttendance.objects.filter(
            student__institution=self.object
        ).select_related('student__person', 'class_obj')[:10]
        
        return context


class InstitutionCreateView(LoginRequiredMixin, CreateView):
    """
    Create new institution
    """
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institution_form.html'
    success_url = reverse_lazy('core:institution_list')
    
    @permission_required(VMSPermissions.SYSTEM_MANAGE_USERS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Institution'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Institution {self.object.name} created successfully.')
        return response


class InstitutionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update institution
    """
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institution_form.html'
    success_url = reverse_lazy('core:institution_list')
    
    @permission_required(VMSPermissions.SYSTEM_MANAGE_USERS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Institution: {self.object.name}'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Institution {self.object.name} updated successfully.')
        return response


class InstitutionDeleteView(LoginRequiredMixin, DeleteView):
    """
    Soft delete institution
    """
    model = Institution
    template_name = 'core/institution_confirm_delete.html'
    success_url = reverse_lazy('core:institution_list')
    
    @permission_required(VMSPermissions.SYSTEM_MANAGE_USERS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        institution = self.get_object()
        institution.soft_delete()
        messages.success(request, f'Institution {institution.name} has been archived.')
        return redirect(self.success_url)


# ============ College CRUD ============

class CollegeListView(LoginRequiredMixin, ListView):
    model = College
    ordering = ['-created_at']
    template_name = 'core/college_list.html'
    context_object_name = 'colleges'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        institution_id = self.request.GET.get('institution_id')
        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['institutions'] = Institution.objects.filter(is_active=True)
        return context


class CollegeCreateView(LoginRequiredMixin, CreateView):
    model = College
    form_class = CollegeForm
    template_name = 'core/college_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:college_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add College'
        context['institutions'] = Institution.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'College {self.object.name} created successfully.')
        return response


class CollegeUpdateView(LoginRequiredMixin, UpdateView):
    model = College
    form_class = CollegeForm
    template_name = 'core/college_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:college_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit College: {self.object.name}'
        context['institutions'] = Institution.objects.filter(is_active=True)
        return context


# ============ School CRUD ============

class SchoolListView(LoginRequiredMixin, ListView):
    model = School
    ordering = ['-created_at']
    template_name = 'core/school_list.html'
    context_object_name = 'schools'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('college')
        college_id = self.request.GET.get('college_id')
        if college_id:
            queryset = queryset.filter(college_id=college_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['colleges'] = College.objects.filter(is_active=True)
        context['staff_members'] = Staff.objects.filter(is_active=True).select_related('person')
        context['colleges_count'] = College.objects.filter(is_active=True).count()
        context['total_schools'] = School.objects.filter(is_active=True).count()
        context['active_schools'] = School.objects.filter(is_active=True).count()
        return context


class SchoolCreateView(LoginRequiredMixin, CreateView):
    model = School
    
    form_class = SchoolForm
    template_name = 'core/school_form.html'
    success_url = reverse_lazy('core:school_list')

    def get_initial(self):
        initial = super().get_initial()
        college_id = self.request.GET.get('college_id')
        if college_id:
            initial['college'] = college_id
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add School'
        context['colleges'] = College.objects.filter(is_active=True)
        return context


# ============ Department CRUD ============

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    ordering = ['-created_at']
    template_name = 'core/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        school_id = self.request.GET.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schools'] = School.objects.filter(is_active=True)
        context['schools_count'] = School.objects.filter(is_active=True).count()
        context['staff_members'] = Staff.objects.filter(is_active=True)
        return context


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Department'
        context['schools'] = School.objects.filter(is_active=True)
        return context


# ============ Program CRUD ============

class ProgramListView(LoginRequiredMixin, ListView):
    model = Program
    ordering = ['-created_at']
    template_name = 'core/program_list.html'
    context_object_name = 'programs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        department_id = self.request.GET.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        context['departments_count'] = Department.objects.filter(is_active=True).count()
        context['staff_members'] = Staff.objects.filter(is_active=True)
        
        # Get total students across all programs
        from apps.core.models import Student
        context['total_students'] = Student.objects.filter(is_active=True).count()
        
        return context


class ProgramCreateView(LoginRequiredMixin, CreateView):
    model = Program
    form_class = ProgramForm
    template_name = 'core/program_form.html'
    success_url = reverse_lazy('core:program_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Program'
        context['departments'] = Department.objects.filter(is_active=True)
        return context
    
class ProgramDetailView(LoginRequiredMixin, DetailView):
    """Program detail view with statistics"""
    model = Program
    template_name = 'core/program_detail.html'
    context_object_name = 'program'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.core.models import Student, Class
        from apps.classroom.models import ClassAttendance
        
        # Students in this program
        context['students'] = self.object.students.filter(is_active=True).select_related('person')[:50]
        context['total_students'] = self.object.students.filter(is_active=True).count()
        
        # Students by year
        from django.db.models import Count
        context['students_by_year'] = list(self.object.students.filter(
            is_active=True
        ).values('current_year').annotate(
            count=Count('id')
        ).order_by('current_year'))
        
        # Classes in this program
        context['classes'] = self.object.classes.filter(is_active=True).select_related('academic_unit')[:20]
        context['total_classes'] = self.object.classes.filter(is_active=True).count()
        
        # Attendance statistics
        context['total_attendance'] = ClassAttendance.objects.filter(
            student__program=self.object,
            verification_status='success'
        ).count()
        
        # Graduation statistics
        from django.utils import timezone
        context['graduating_this_year'] = self.object.students.filter(
            expected_graduation__year=timezone.now().year,
            status='active'
        ).count()
        
        # Performance metrics
        from django.db.models import Avg
        context['avg_gpa'] = self.object.students.filter(
            is_active=True,
            cumulative_gpa__isnull=False
        ).aggregate(Avg('cumulative_gpa'))['cumulative_gpa__avg']
        
        return context


class ProgramUpdateView(LoginRequiredMixin, UpdateView):
    """Update program information"""
    model = Program
    form_class = ProgramForm
    template_name = 'core/program_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:program_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Program {form.instance.name} updated successfully.')
        return super().form_valid(form)


class ProgramDeleteView(LoginRequiredMixin, DeleteView):
    """Delete program (soft delete)"""
    model = Program
    template_name = 'core/program_confirm_delete.html'
    success_url = reverse_lazy('core:program_list')
    
    def delete(self, request, *args, **kwargs):
        program = self.get_object()
        program.soft_delete()
        messages.success(request, f'Program {program.name} has been archived.')
        return redirect(self.success_url)


class CollegeDetailView(LoginRequiredMixin, DetailView):
    """College detail view with statistics"""
    model = College
    template_name = 'core/college_detail.html'
    context_object_name = 'college'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get schools under this college
        context['schools'] = self.object.schools.filter(is_active=True)
        
        # Statistics
        from apps.core.models import School, Department, Student, Staff
        
        context['total_schools'] = self.object.schools.filter(is_active=True).count()
        context['total_departments'] = Department.objects.filter(
            school__college=self.object,
            is_active=True
        ).count()
        context['total_students'] = Student.objects.filter(
            college=self.object,
            is_active=True
        ).count()
        context['total_staff'] = Staff.objects.filter(
            college=self.object,
            is_active=True
        ).count()
        
        # Recent activity
        from apps.classroom.models import ClassAttendance
        context['recent_attendance'] = ClassAttendance.objects.filter(
            student__college=self.object
        ).select_related('student__person', 'class_obj')[:10]
        
        return context


class CollegeUpdateView(LoginRequiredMixin, UpdateView):
    """Update college information"""
    model = College
    form_class = CollegeForm
    template_name = 'core/college_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:college_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'College {form.instance.name} updated successfully.')
        return super().form_valid(form)


class CollegeDeleteView(LoginRequiredMixin, DeleteView):
    """Delete college (soft delete)"""
    model = College
    template_name = 'core/college_confirm_delete.html'
    success_url = reverse_lazy('core:college_list')
    
    def delete(self, request, *args, **kwargs):
        college = self.get_object()
        college.soft_delete()
        messages.success(request, f'College {college.name} has been archived.')
        return redirect(self.success_url)


# ============ School Detail/Update Views ============

class SchoolDetailView(LoginRequiredMixin, DetailView):
    """School detail view with statistics"""
    model = School
    template_name = 'core/school_detail.html'
    context_object_name = 'school'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get departments under this school
        context['departments'] = self.object.departments.filter(is_active=True)
        
        # Statistics
        from apps.core.models import Department, Student, Staff
        
        context['total_departments'] = self.object.departments.filter(is_active=True).count()
        context['total_students'] = Student.objects.filter(
            school=self.object,
            is_active=True
        ).count()
        context['total_staff'] = Staff.objects.filter(
            school=self.object,
            is_active=True
        ).count()
        
        # Get programs
        from apps.core.models import Program
        context['programs'] = Program.objects.filter(
            department__school=self.object,
            is_active=True
        )[:20]
        
        # Recent attendance
        from apps.classroom.models import ClassAttendance
        context['recent_attendance'] = ClassAttendance.objects.filter(
            student__school=self.object
        ).select_related('student__person', 'class_obj')[:10]
        
        return context


class SchoolUpdateView(LoginRequiredMixin, UpdateView):
    """Update school information"""
    model = School
    form_class = SchoolForm
    template_name = 'core/school_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:school_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'School {form.instance.name} updated successfully.')
        return super().form_valid(form)


class SchoolDeleteView(LoginRequiredMixin, DeleteView):
    """Delete school (soft delete)"""
    model = School
    template_name = 'core/school_confirm_delete.html'
    success_url = reverse_lazy('core:school_list')
    
    def delete(self, request, *args, **kwargs):
        school = self.get_object()
        school.soft_delete()
        messages.success(request, f'School {school.name} has been archived.')
        return redirect(self.success_url)


# ============ Department Detail/Update Views ============

class DepartmentDetailView(LoginRequiredMixin, DetailView):
    """Department detail view with statistics"""
    model = Department
    template_name = 'core/department_detail.html'
    context_object_name = 'department'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        from apps.core.models import Program, Student, Staff
        from apps.classroom.models import ClassAttendance
        
        context['programs'] = self.object.programs.filter(is_active=True)
        context['total_programs'] = self.object.programs.filter(is_active=True).count()
        context['total_students'] = Student.objects.filter(
            department=self.object,
            is_active=True
        ).count()
        context['total_staff'] = Staff.objects.filter(
            department=self.object,
            is_active=True
        ).count()
        
        # Staff by category
        context['academic_staff'] = Staff.objects.filter(
            department=self.object,
            staff_category='academic',
            is_active=True
        ).count()
        context['administrative_staff'] = Staff.objects.filter(
            department=self.object,
            staff_category='administrative',
            is_active=True
        ).count()
        
        # Recent students
        context['recent_students'] = Student.objects.filter(
            department=self.object,
            is_active=True
        ).select_related('person')[:20]
        
        # Recent attendance
        context['recent_attendance'] = ClassAttendance.objects.filter(
            student__department=self.object
        ).select_related('student__person', 'class_obj')[:10]
        
        # Classes in this department
        from apps.core.models import Class
        context['classes'] = Class.objects.filter(
            department=self.object,
            is_active=True
        )[:10]
        
        return context


class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    """Update department information"""
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:department_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Department {form.instance.name} updated successfully.')
        return super().form_valid(form)


class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete department (soft delete)"""
    model = Department
    template_name = 'core/department_confirm_delete.html'
    success_url = reverse_lazy('core:department_list')
    
    def delete(self, request, *args, **kwargs):
        department = self.get_object()
        department.soft_delete()
        messages.success(request, f'Department {department.name} has been archived.')
        return redirect(self.success_url)






def toggle_college_status(request, pk):
    """Toggle college active status via AJAX"""
    if request.method == 'POST':
        try:
            college = College.objects.get(pk=pk)
            college.is_active = not college.is_active
            college.save()
            status_text = 'activated' if college.is_active else 'deactivated'
            return JsonResponse({
                'success': True, 
                'is_active': college.is_active,
                'message': f'College {college.name} {status_text} successfully'
            })
        except College.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'College not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def toggle_school_status(request, pk):
    """Toggle school active status via AJAX"""
    if request.method == 'POST':
        try:
            school = School.objects.get(pk=pk)
            school.is_active = not school.is_active
            school.save()
            status_text = 'activated' if school.is_active else 'deactivated'
            return JsonResponse({
                'success': True, 
                'is_active': school.is_active,
                'message': f'School {school.name} {status_text} successfully'
            })
        except School.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'School not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def update_school(request, pk):
    if request.method == 'POST':
        try:
            school = School.objects.get(pk=pk)
            school.name = request.POST.get('name')
            school.short_name = request.POST.get('short_name')
            school.code = request.POST.get('code')
            school.college_id = request.POST.get('college')
            school.dean_id = request.POST.get('dean') or None
            school.contact_email = request.POST.get('contact_email')
            school.phone = request.POST.get('phone')
            school.description = request.POST.get('description')
            school.is_active = request.POST.get('is_active') == 'on'
            school.save()
            
            return JsonResponse({'success': True, 'message': f'School {school.name} updated successfully'})
        except School.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'School not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_school_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        school = School.objects.get(pk=pk)
        colleges = College.objects.filter(is_active=True)
        
        html = f'''
        <form id="editSchoolForm" method="POST" action="/core/schools/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">School Name</label>
                        <input type="text" name="name" class="form-control" value="{school.name}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Short Name</label>
                        <input type="text" name="short_name" class="form-control" value="{school.short_name or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Code</label>
                        <input type="text" name="code" class="form-control" value="{school.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label required">College</label>
                        <select name="college" class="form-select" required>
                            <option value="">Select College</option>
        '''
        for college in colleges:
            selected = 'selected' if school.college_id == college.id else ''
            html += f'<option value="{college.id}" {selected}>{college.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Dean/Director</label>
                        <select name="dean" class="form-select">
                            <option value="">Select Dean</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Contact Email</label>
                        <input type="email" name="contact_email" class="form-control" value="{school.contact_email or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{school.phone or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3">{school.description or ''}</textarea>
                    </div>
                    <div class="col-md-6">
                        <div class="form-check mt-4">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if school.is_active else ''}>
                            <label class="form-check-label">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update School</button>
            </div>
        </form>
        <script>
            $('#editSchoolForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editSchoolModal').modal('hide');
                            toastr.success(response.message || 'School updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update school');
                            submitBtn.prop('disabled', false).html('Update School');
                        }}
                    }},
                    error: function() {{
                        toastr.error('An error occurred');
                        submitBtn.prop('disabled', false).html('Update School');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)
    


def toggle_department_status(request, pk):
    """Toggle department active status via AJAX"""
    if request.method == 'POST':
        try:
            department = Department.objects.get(pk=pk)
            department.is_active = not department.is_active
            department.save()
            status_text = 'activated' if department.is_active else 'deactivated'
            return JsonResponse({
                'success': True, 
                'is_active': department.is_active,
                'message': f'Department {department.name} {status_text} successfully'
            })
        except Department.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Department not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def get_department_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        department = Department.objects.get(pk=pk)
        schools = School.objects.filter(is_active=True)
        staff_members = Staff.objects.filter(is_active=True)
        
        html = f'''
        <form id="editDepartmentForm" method="POST" action="/core/departments/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">Department Name</label>
                        <input type="text" name="name" class="form-control" value="{department.name}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Short Name</label>
                        <input type="text" name="short_name" class="form-control" value="{department.short_name or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Code</label>
                        <input type="text" name="code" class="form-control" value="{department.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label required">School</label>
                        <select name="school" class="form-select" required>
                            <option value="">Select School</option>
        '''
        for school in schools:
            selected = 'selected' if department.school_id == school.id else ''
            html += f'<option value="{school.id}" {selected}>{school.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Head of Department</label>
                        <select name="hod" class="form-select">
                            <option value="">Select HOD</option>
        '''
        for staff in staff_members:
            selected = 'selected' if department.hod_id == staff.id else ''
            html += f'<option value="{staff.id}" {selected}>{staff.get_full_name() or staff.username}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Contact Email</label>
                        <input type="email" name="contact_email" class="form-control" value="{department.contact_email or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{department.phone or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3">{department.description or ''}</textarea>
                    </div>
                    <div class="col-md-6">
                        <div class="form-check mt-4">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if department.is_active else ''}>
                            <label class="form-check-label">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Department</button>
            </div>
        </form>
        <script>
            $('#editDepartmentForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editDepartmentModal').modal('hide');
                            toastr.success(response.message || 'Department updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update department');
                            submitBtn.prop('disabled', false).html('Update Department');
                        }}
                    }},
                    error: function() {{
                        toastr.error('An error occurred');
                        submitBtn.prop('disabled', false).html('Update Department');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)



def update_department(request, pk):
    """Update department via AJAX"""
    if request.method == 'POST':
        try:
            department = Department.objects.get(pk=pk)
            department.name = request.POST.get('name')
            department.short_name = request.POST.get('short_name')
            department.code = request.POST.get('code')
            department.school_id = request.POST.get('school')
            department.hod_id = request.POST.get('hod') or None
            department.contact_email = request.POST.get('contact_email')
            department.phone = request.POST.get('phone')
            department.description = request.POST.get('description')
            department.is_active = request.POST.get('is_active') == 'on'
            department.save()
            
            return JsonResponse({'success': True, 'message': f'Department {department.name} updated successfully'})
        except Department.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Department not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})



def toggle_program_status(request, pk):
    if request.method == 'POST':
        try:
            program = Program.objects.get(pk=pk)
            program.is_active = not program.is_active
            program.save()
            status_text = 'activated' if program.is_active else 'deactivated'
            return JsonResponse({
                'success': True,
                'is_active': program.is_active,
                'message': f'Program {program.name} {status_text} successfully'
            })
        except Program.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Program not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def get_program_edit_form(request, pk):
    try:
        program = Program.objects.get(pk=pk)
        departments = Department.objects.filter(is_active=True)
        staff_members = Staff.objects.filter(is_active=True)
        
        html = f'''
        <form id="editProgramForm" method="POST" action="/core/programs/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">Program Name</label>
                        <input type="text" name="name" class="form-control" value="{program.name}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Short Name</label>
                        <input type="text" name="short_name" class="form-control" value="{program.short_name or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Code</label>
                        <input type="text" name="code" class="form-control" value="{program.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label required">Department</label>
                        <select name="department" class="form-select" required>
                            <option value="">Select Department</option>
        '''
        for dept in departments:
            selected = 'selected' if program.department_id == dept.id else ''
            html += f'<option value="{dept.id}" {selected}>{dept.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Degree Level</label>
                        <select name="degree_level" class="form-select">
                            <option value="">Select Level</option>
                            <option value="bachelor" {'selected' if program.degree_level == 'bachelor' else ''}>Bachelor's Degree</option>
                            <option value="master" {'selected' if program.degree_level == 'master' else ''}>Master's Degree</option>
                            <option value="phd" {'selected' if program.degree_level == 'phd' else ''}>PhD/Doctorate</option>
                            <option value="diploma" {'selected' if program.degree_level == 'diploma' else ''}>Diploma</option>
                            <option value="certificate" {'selected' if program.degree_level == 'certificate' else ''}>Certificate</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Duration (Years)</label>
                        <input type="number" name="duration_years" class="form-control" step="0.5" value="{program.duration_years or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Total Credits</label>
                        <input type="number" name="total_credits" class="form-control" value="{program.total_credits or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Program Coordinator</label>
                        <select name="coordinator" class="form-select">
                            <option value="">Select Coordinator</option>
        '''
        for staff in staff_members:
            selected = 'selected' if program.coordinator_id == staff.id else ''
            html += f'<option value="{staff.id}" {selected}>{staff.get_full_name() or staff.username}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3">{program.description or ''}</textarea>
                    </div>
                    <div class="col-md-6">
                        <div class="form-check mt-4">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if program.is_active else ''}>
                            <label class="form-check-label">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Program</button>
            </div>
        </form>
        <script>
            $('#editProgramForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editProgramModal').modal('hide');
                            toastr.success(response.message || 'Program updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update program');
                            submitBtn.prop('disabled', false).html('Update Program');
                        }}
                    }},
                    error: function() {{
                        toastr.error('An error occurred');
                        submitBtn.prop('disabled', false).html('Update Program');
                    }}
                }});
            }});
        </script>
        '''
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)



def update_program(request, pk):
    if request.method == 'POST':
        try:
            program = Program.objects.get(pk=pk)
            program.name = request.POST.get('name')
            program.short_name = request.POST.get('short_name')
            program.code = request.POST.get('code')
            program.department_id = request.POST.get('department')
            program.degree_level = request.POST.get('degree_level')
            program.duration_years = request.POST.get('duration_years')
            program.total_credits = request.POST.get('total_credits')
            program.coordinator_id = request.POST.get('coordinator') or None
            program.description = request.POST.get('description')
            program.is_active = request.POST.get('is_active') == 'on'
            program.save()
            
            return JsonResponse({'success': True, 'message': f'Program {program.name} updated successfully'})
        except Program.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Program not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# apps/core/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import College, School, Institution
from .forms import CollegeForm

@login_required
def get_college_detail(request, pk):
    """Return college detail HTML for AJAX modal"""
    try:
        college = College.objects.select_related('institution').get(pk=pk)
        
        html = f'''
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">College Name</div>
                <div class="detail-value"><strong>{college.name}</strong></div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Short Name</div>
                <div class="detail-value">{college.short_name or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Code</div>
                <div class="detail-value">{college.code or '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Institution</div>
                <div class="detail-value">
                    <span class="badge bg-primary">{college.institution.name if college.institution else '—'}</span>
                </div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Dean/Director</div>
                <div class="detail-value">{college.dean.get_full_name() if college.dean else '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Contact Email</div>
                <div class="detail-value">{college.contact_email or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Phone Number</div>
                <div class="detail-value">{college.phone or '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Website</div>
                <div class="detail-value">{college.website or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Established Date</div>
                <div class="detail-value">{college.established_date.strftime('%Y-%m-%d') if college.established_date else '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Status</div>
                <div class="detail-value">
                    {"<span class='badge bg-success'>Active</span>" if college.is_active else "<span class='badge bg-secondary'>Inactive</span>"}
                </div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-12">
                <div class="detail-label">Description</div>
                <div class="detail-value">{college.description or 'No description provided.'}</div>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-12">
                <div class="detail-label">Statistics</div>
                <div class="row mt-2">
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4>{college.schools.count()}</h4>
                            <small class="text-muted">Schools</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4>{college.departments.count()}</h4>
                            <small class="text-muted">Departments</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4>{college.programs.count()}</h4>
                            <small class="text-muted">Programs</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
def get_college_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        college = College.objects.get(pk=pk)
        institutions = Institution.objects.filter(is_active=True)
        
        html = f'''
        <form id="editCollegeForm" method="POST" action="/core/colleges/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label required">College Name</label>
                    <input type="text" name="name" class="form-control" value="{college.name}" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Short Name</label>
                    <input type="text" name="short_name" class="form-control" value="{college.short_name or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Code</label>
                    <input type="text" name="code" class="form-control" value="{college.code or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label required">Institution</label>
                    <select name="institution" class="form-select" required>
                        <option value="">Select Institution</option>
        '''
        
        for inst in institutions:
            selected = 'selected' if college.institution_id == inst.id else ''
            html += f'<option value="{inst.id}" {selected}>{inst.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Established Date</label>
                    <input type="date" name="established_date" class="form-control" value="{college.established_date.strftime('%Y-%m-%d') if college.established_date else ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Dean/Director</label>
                    <input type="text" name="dean" class="form-control" value="{college.dean.get_full_name() if college.dean else ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Contact Email</label>
                    <input type="email" name="contact_email" class="form-control" value="{college.contact_email or ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Phone Number</label>
                    <input type="tel" name="phone" class="form-control" value="{college.phone or ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Website</label>
                    <input type="url" name="website" class="form-control" value="{college.website or ''}">
                </div>
                <div class="col-12">
                    <label class="form-label">Description</label>
                    <textarea name="description" class="form-control" rows="3">{college.description or ''}</textarea>
                </div>
                <div class="col-12">
                    <div class="form-check">
                        <input type="checkbox" name="is_active" class="form-check-input" id="editIsActive" {'checked' if college.is_active else ''}>
                        <label class="form-check-label" for="editIsActive">Active</label>
                    </div>
                </div>
            </div>
            <div class="modal-footer mt-3">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update College</button>
            </div>
        </form>
        
        <script>
            $('#editCollegeForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editCollegeModal')
            }});
            
            $('#editCollegeForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editCollegeModal').modal('hide');
                            toastr.success(response.message || 'College updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update college');
                            submitBtn.prop('disabled', false).html('Update College');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update College');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
def get_college_schools(request, pk):
    """Get schools under a college for AJAX modal"""
    try:
        college = College.objects.get(pk=pk)
        schools = college.schools.filter(is_active=True).select_related('dean__person')
        
        if schools.exists():
            html = '<div class="list-group">'
            for school in schools:
                dean_name = school.dean.get_full_name() if school.dean else 'Not Assigned'
                html += f'''
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{school.name}</strong>
                            <br><small class="text-muted">Code: {school.code or 'N/A'} | Dean: {dean_name}</small>
                        </div>
                        <div>
                            <span class="badge bg-info">{school.departments.count()} Departments</span>
                            <button class="btn btn-sm btn-outline-primary ms-2" onclick="viewSchool({school.id})">
                                <i class="bx bx-show"></i>
                            </button>
                        </div>
                    </div>
                </div>
                '''
            html += '</div>'
        else:
            html = '<div class="text-center py-4"><p class="text-muted">No schools found under this college.</p></div>'
        
        return JsonResponse({'html': html, 'success': True, 'college_name': college.name})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
@csrf_exempt
def update_college(request, pk):
    """Update college via AJAX"""
    if request.method == 'POST':
        try:
            college = College.objects.get(pk=pk)
            college.name = request.POST.get('name')
            college.short_name = request.POST.get('short_name')
            college.code = request.POST.get('code')
            college.institution_id = request.POST.get('institution')
            college.established_date = request.POST.get('established_date') or None
            college.contact_email = request.POST.get('contact_email')
            college.phone = request.POST.get('phone')
            college.website = request.POST.get('website')
            college.description = request.POST.get('description')
            college.is_active = request.POST.get('is_active') == 'on'
            college.save()
            
            return JsonResponse({'success': True, 'message': f'College {college.name} updated successfully'})
        except College.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'College not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@csrf_exempt
def toggle_college_status(request, pk):
    """Toggle college active status via AJAX"""
    if request.method == 'POST':
        try:
            college = College.objects.get(pk=pk)
            college.is_active = not college.is_active
            college.save()
            status_text = 'activated' if college.is_active else 'deactivated'
            return JsonResponse({'success': True, 'message': f'College {college.name} {status_text} successfully'})
        except College.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'College not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def create_college(request):
    """Create college via AJAX"""
    if request.method == 'POST':
        try:
            college = College()
            college.name = request.POST.get('name')
            college.short_name = request.POST.get('short_name')
            college.code = request.POST.get('code')
            college.institution_id = request.POST.get('institution')
            college.established_date = request.POST.get('established_date') or None
            college.contact_email = request.POST.get('contact_email')
            college.phone = request.POST.get('phone')
            college.website = request.POST.get('website')
            college.description = request.POST.get('description')
            college.is_active = request.POST.get('is_active') == 'on'
            college.save()
            
            return JsonResponse({'success': True, 'message': f'College {college.name} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_college_detail(request, pk):
    """Return college detail HTML for AJAX modal"""
    try:
        college = get_object_or_404(College.objects.select_related('institution', 'dean'), pk=pk)
        
        # Get counts
        schools_count = college.schools.filter(is_active=True).count()
        departments_count = college.departments.filter(is_active=True).count()
        programs_count = college.programs.filter(is_active=True).count()
        
        html = f'''
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">College Name</div>
                <div class="detail-value"><strong>{college.name}</strong></div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Short Name</div>
                <div class="detail-value">{college.short_name or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Code</div>
                <div class="detail-value">{college.code or '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Institution</div>
                <div class="detail-value">
                    <span class="badge bg-primary">{college.institution.name if college.institution else '—'}</span>
                </div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Dean/Director</div>
                <div class="detail-value">{college.dean.get_full_name() if college.dean else '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Contact Email</div>
                <div class="detail-value">{college.contact_email or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Phone Number</div>
                <div class="detail-value">{college.phone or '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Website</div>
                <div class="detail-value">{college.website or '—'}</div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Established Date</div>
                <div class="detail-value">{college.established_date.strftime('%Y-%m-%d') if college.established_date else '—'}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Status</div>
                <div class="detail-value">
                    {"<span class='badge bg-success'>Active</span>" if college.is_active else "<span class='badge bg-secondary'>Inactive</span>"}
                </div>
            </div>
        </div>
        '''
        
        if college.description:
            html += f'''
            <div class="row mb-3">
                <div class="col-12">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">{college.description}</div>
                </div>
            </div>
            '''
        
        html += f'''
        <hr>
        <div class="row">
            <div class="col-12">
                <div class="detail-label">Statistics</div>
                <div class="row mt-2">
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4 class="mb-0">{schools_count}</h4>
                            <small class="text-muted">Schools</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4 class="mb-0">{departments_count}</h4>
                            <small class="text-muted">Departments</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <h4 class="mb-0">{programs_count}</h4>
                            <small class="text-muted">Programs</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
def get_college_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        college = get_object_or_404(College, pk=pk)
        institutions = Institution.objects.filter(is_active=True)
        
        html = f'''
        <form id="editCollegeForm" method="POST" action="/core/colleges/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">College Name</label>
                        <input type="text" name="name" class="form-control" value="{college.name}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Short Name</label>
                        <input type="text" name="short_name" class="form-control" value="{college.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Code</label>
                        <input type="text" name="code" class="form-control" value="{college.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label required">Institution</label>
                        <select name="institution" class="form-select" required>
                            <option value="">Select Institution</option>
        '''
        
        for inst in institutions:
            selected = 'selected' if college.institution_id == inst.id else ''
            html += f'<option value="{inst.id}" {selected}>{inst.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Established Date</label>
                        <input type="date" name="established_date" class="form-control" value="">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Dean/Director</label>
                        <input type="text" name="dean" class="form-control" value="{college.dean.get_full_name() if college.dean else ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Contact Email</label>
                        <input type="email" name="contact_email" class="form-control" value="{college.contact_email or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{college.phone or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Website</label>
                        <input type="url" name="website" class="form-control" value="{college.website or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3">{college.description or ''}</textarea>
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input type="checkbox" name="is_active" class="form-check-input" id="editIsActive" {'checked' if college.is_active else ''}>
                            <label class="form-check-label" for="editIsActive">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update College</button>
            </div>
        </form>
        
        <script>
            // Initialize Select2 for the edit form
            $('#editCollegeForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editCollegeModal')
            }});
            
            // Handle form submission
            $('#editCollegeForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editCollegeModal').modal('hide');
                            toastr.success(response.message || 'College updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update college');
                            submitBtn.prop('disabled', false).html('Update College');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update College');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
def get_college_schools(request, pk):
    """Get schools under a college for AJAX modal"""
    try:
        college = get_object_or_404(College, pk=pk)
        schools = college.schools.filter(is_active=True).select_related('dean__person')
        
        if schools.exists():
            html = '<div class="list-group">'
            for school in schools:
                dean_name = school.dean.get_full_name() if school.dean else 'Not Assigned'
                html += f'''
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{school.name}</strong>
                            <br><small class="text-muted">Code: {school.code or 'N/A'} | Dean: {dean_name}</small>
                        </div>
                        <div>
                            <span class="badge bg-info">{school.departments.count()} Departments</span>
                            <button class="btn btn-sm btn-outline-primary ms-2" onclick="viewSchool({school.id})">
                                <i class="bx bx-show"></i>
                            </button>
                        </div>
                    </div>
                </div>
                '''
            html += '</div>'
        else:
            html = '<div class="text-center py-4"><p class="text-muted">No schools found under this college.</p></div>'
        
        return JsonResponse({'html': html, 'success': True, 'college_name': college.name})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)
    
# apps/core/views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import School, College, Staff
from .forms import SchoolModalForm

@login_required
@csrf_exempt
def create_school(request):
    """Create school via AJAX"""
    if request.method == 'POST':
        try:
            school = School()
            school.college_id = request.POST.get('college')
            school.name = request.POST.get('name')
            school.code = request.POST.get('code')
            school.short_name = request.POST.get('short_name')
            school.dean_id = request.POST.get('dean') or None
            school.contact_email = request.POST.get('contact_email')
            school.phone = request.POST.get('phone')
            school.description = request.POST.get('description')
            school.is_active = request.POST.get('is_active') == 'on'
            school.save()
            
            return JsonResponse({'success': True, 'message': f'School {school.name} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_school_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        school = School.objects.select_related('college', 'dean__person').get(pk=pk)
        colleges = College.objects.filter(is_active=True)
        staff_members = Staff.objects.filter(is_active=True).select_related('person')
        
        html = f'''
        <form id="editSchoolForm" method="POST" action="/core/schools/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">School Name</label>
                        <input type="text" name="name" class="form-control" value="{school.name}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Short Name</label>
                        <input type="text" name="short_name" class="form-control" value="{school.short_name or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Code</label>
                        <input type="text" name="code" class="form-control" value="{school.code or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label required">College</label>
                        <select name="college" class="form-select" required>
                            <option value="">Select College</option>
        '''
        
        for college in colleges:
            selected = 'selected' if school.college_id == college.id else ''
            html += f'<option value="{college.id}" {selected}>{college.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Dean/Director</label>
                        <select name="dean" class="form-select">
                            <option value="">Select Dean</option>
        '''
        
        for staff in staff_members:
            selected = 'selected' if school.dean_id == staff.id else ''
            html += f'<option value="{staff.id}" {selected}>{staff.get_full_name()}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Contact Email</label>
                        <input type="email" name="contact_email" class="form-control" value="{school.contact_email or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{school.phone or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3">{school.description or ''}</textarea>
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input type="checkbox" name="is_active" class="form-check-input" id="editIsActive" {'checked' if school.is_active else ''}>
                            <label class="form-check-label" for="editIsActive">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update School</button>
            </div>
        </form>
        
        <script>
            $('#editSchoolForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editSchoolModal')
            }});
            
            $('#editSchoolForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editSchoolModal').modal('hide');
                            toastr.success(response.message || 'School updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update school');
                            submitBtn.prop('disabled', false).html('Update School');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update School');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@login_required
@csrf_exempt
def update_school(request, pk):
    """Update school via AJAX"""
    if request.method == 'POST':
        try:
            school = School.objects.get(pk=pk)
            school.college_id = request.POST.get('college')
            school.name = request.POST.get('name')
            school.code = request.POST.get('code')
            school.short_name = request.POST.get('short_name')
            school.dean_id = request.POST.get('dean') or None
            school.contact_email = request.POST.get('contact_email')
            school.phone = request.POST.get('phone')
            school.description = request.POST.get('description')
            school.is_active = request.POST.get('is_active') == 'on'
            school.save()
            
            return JsonResponse({'success': True, 'message': f'School {school.name} updated successfully'})
        except School.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'School not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# @login_required
# @csrf_exempt
# def toggle_school_status(request, pk):
#     """Toggle school active status via AJAX"""
#     if request.method == 'POST':
#         try:
#             school = School.objects.get(pk=pk)
#             school.is_active = not school.is_active
#             school.save()
#             status_text = 'activated' if school.is_active else 'deactivated'
#             return JsonResponse({'success': True, 'message': f'School {school.name} {status_text} successfully'})
#         except School.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'School not found'})
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})