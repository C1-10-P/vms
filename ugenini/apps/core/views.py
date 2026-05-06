import csv
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import Institution, College, School, Department, Program, Person, Student, Staff, AcademicUnit, Class, ClassEnrollment
from .forms import InstitutionForm, CollegeForm, SchoolForm, DepartmentForm, ProgramForm, PersonForm, StudentForm, StaffForm, AcademicUnitForm, ClassForm
from .services import DashboardService, InstitutionService, CollegeService, SchoolService, DepartmentService, ProgramService, PersonService
from .data_services import DataExportService


# ============ Dashboard Views ============

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = DashboardService.get_dashboard_stats(self.request.user)
        context['recent_activity'] = DashboardService._get_recent_activity()
        return context


@csrf_exempt
def realtime_stats(request):
    """AJAX endpoint for real-time statistics"""
    if request.method == 'GET':
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.firmware.models import EdgeNode
        
        data = {
            'current_attendance': ClassAttendance.objects.filter(
                scan_time__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'online_devices': EdgeNode.objects.filter(status='online').count(),
            'timestamp': timezone.now().isoformat()
        }
        return JsonResponse(data)


# ============ Institution Views ============

class InstitutionListView(LoginRequiredMixin, ListView):
    model = Institution
    ordering = ['-created_at']
    template_name = 'core/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        return queryset


class InstitutionDetailView(LoginRequiredMixin, DetailView):
    model = Institution
    template_name = 'core/institution_detail.html'
    context_object_name = 'institution'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['colleges'] = self.object.colleges.filter(is_active=True)
        context['total_students'] = Student.objects.filter(institution=self.object).count()
        context['total_staff'] = Staff.objects.filter(institution=self.object).count()
        return context


class InstitutionCreateView(LoginRequiredMixin, CreateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institution_form.html'
    success_url = reverse_lazy('core:institution_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Institution {form.instance.name} created successfully.')
        return super().form_valid(form)


class InstitutionUpdateView(LoginRequiredMixin, UpdateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institution_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:institution_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Institution {form.instance.name} updated successfully.')
        return super().form_valid(form)


class InstitutionDeleteView(LoginRequiredMixin, DeleteView):
    model = Institution
    template_name = 'core/institution_confirm_delete.html'
    success_url = reverse_lazy('core:institution_list')
    
    def delete(self, request, *args, **kwargs):
        institution = self.get_object()
        institution.soft_delete()
        messages.success(request, f'Institution {institution.name} has been archived.')
        return redirect(self.success_url)


@permission_required(VMSPermissions.SYSTEM_MANAGE_USERS)
def institution_restore(request, pk):
    """Restore a soft-deleted institution"""
    institution = Institution.objects.all_including_archived().get(pk=pk)
    institution.restore()
    messages.success(request, f'Institution {institution.name} has been restored.')
    return redirect('core:institution_detail', pk=pk)


# ============ College Views ============

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
        context['staff_members'] = Staff.objects.filter(is_active=True)
        context['total_colleges'] = College.objects.filter(is_active=True).count()
        context['total_schools'] = School.objects.filter(is_active=True).count()
        context['active_colleges'] = College.objects.filter(is_active=True).count()
        context['institutions_count'] = Institution.objects.filter(is_active=True).count()
        return context


class CollegeDetailView(LoginRequiredMixin, DetailView):
    model = College
    template_name = 'core/college_detail.html'
    context_object_name = 'college'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schools'] = self.object.schools.filter(is_active=True)
        return context


class CollegeCreateView(LoginRequiredMixin, CreateView):
    model = College
    form_class = CollegeForm
    template_name = 'core/college_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:college_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'College {form.instance.name} created successfully.')
        return super().form_valid(form)


class CollegeUpdateView(LoginRequiredMixin, UpdateView):
    model = College
    form_class = CollegeForm
    template_name = 'core/college_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:college_detail', kwargs={'pk': self.object.pk})


class CollegeDeleteView(LoginRequiredMixin, DeleteView):
    model = College
    template_name = 'core/college_confirm_delete.html'
    success_url = reverse_lazy('core:college_list')
    
    def delete(self, request, *args, **kwargs):
        college = self.get_object()
        college.soft_delete()
        messages.success(request, f'College {college.name} has been archived.')
        return redirect(self.success_url)


# ============ School Views ============

class SchoolListView(LoginRequiredMixin, ListView):
    model = School
    ordering = ['-created_at']
    template_name = 'core/school_list.html'
    context_object_name = 'schools'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        college_id = self.request.GET.get('college_id')
        if college_id:
            queryset = queryset.filter(college_id=college_id)
        return queryset


class SchoolDetailView(LoginRequiredMixin, DetailView):
    model = School
    template_name = 'core/school_detail.html'
    context_object_name = 'school'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = self.object.departments.filter(is_active=True)
        return context


class SchoolCreateView(LoginRequiredMixin, CreateView):
    model = School
    form_class = SchoolForm
    template_name = 'core/school_form.html'
    success_url = reverse_lazy('core:school_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'School {form.instance.name} created successfully.')
        return super().form_valid(form)


class SchoolUpdateView(LoginRequiredMixin, UpdateView):
    model = School
    form_class = SchoolForm
    template_name = 'core/school_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:school_detail', kwargs={'pk': self.object.pk})


class SchoolDeleteView(LoginRequiredMixin, DeleteView):
    model = School
    template_name = 'core/school_confirm_delete.html'
    success_url = reverse_lazy('core:school_list')


# ============ Department Views ============

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


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'core/department_detail.html'
    context_object_name = 'department'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_members'] = self.object.staff_members.filter(is_active=True)
        context['students'] = self.object.students.filter(is_active=True)[:20]
        return context


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')


class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'


class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Department
    template_name = 'core/department_confirm_delete.html'
    success_url = reverse_lazy('core:department_list')


# ============ Program Views ============

class ProgramListView(LoginRequiredMixin, ListView):
    model = Program
    ordering = ['-created_at']
    template_name = 'core/program_list.html'
    context_object_name = 'programs'
    paginate_by = 20


class ProgramDetailView(LoginRequiredMixin, DetailView):
    model = Program
    template_name = 'core/program_detail.html'
    context_object_name = 'program'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['students'] = self.object.students.filter(is_active=True)[:20]
        context['total_students'] = self.object.students.filter(is_active=True).count()
        return context


class ProgramCreateView(LoginRequiredMixin, CreateView):
    model = Program
    form_class = ProgramForm
    template_name = 'core/program_form.html'
    success_url = reverse_lazy('core:program_list')


class ProgramUpdateView(LoginRequiredMixin, UpdateView):
    model = Program
    form_class = ProgramForm
    template_name = 'core/program_form.html'


class ProgramDeleteView(LoginRequiredMixin, DeleteView):
    model = Program
    template_name = 'core/program_confirm_delete.html'
    success_url = reverse_lazy('core:program_list')


# ============ Person Views ============

class PersonListView(LoginRequiredMixin, ListView):
    model = Person
    ordering = ['-created_at']
    template_name = 'core/person_list.html'
    context_object_name = 'persons'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        person_type = self.request.GET.get('person_type')
        if person_type:
            queryset = queryset.filter(person_type=person_type)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Person
        context['total_persons'] = Person.objects.filter(is_active=True).count()
        context['student_count'] = Person.objects.filter(person_type='student', is_active=True).count()
        context['staff_count'] = Person.objects.filter(person_type='staff', is_active=True).count()
        context['active_count'] = Person.objects.filter(is_active=True).count()
        return context


class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = 'core/person_detail.html'
    context_object_name = 'person'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_object'] = self.object.get_related_object()
        return context


class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = 'core/person_form.html'
    success_url = reverse_lazy('core:person_list')


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = 'core/person_form.html'


class PersonDeleteView(LoginRequiredMixin, DeleteView):
    model = Person
    template_name = 'core/person_confirm_delete.html'
    success_url = reverse_lazy('core:person_list')


# ============ Student Views ============

class StudentListView(LoginRequiredMixin, ListView):
    """List all students"""
    model = Student
    ordering = ['-created_at']
    template_name = 'core/student_list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('person', 'program', 'department')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(student_reg_number__icontains=search) |
                Q(person__first_name__icontains=search) |
                Q(person__last_name__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Program, Staff
        
        context['programs'] = Program.objects.filter(is_active=True)
        context['programs_count'] = Program.objects.filter(is_active=True).count()
        context['staff_members'] = Staff.objects.filter(is_active=True).select_related('person')
        context['active_count'] = Student.objects.filter(status='active', is_active=True).count()
        context['graduating_count'] = Student.objects.filter(
            expected_graduation__year=timezone.now().year, 
            status='active'
        ).count()
        return context


class StudentDetailView(LoginRequiredMixin, DetailView):
    """Student detail view"""
    model = Student
    template_name = 'core/student_detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.classroom.models import ClassAttendance
        context['attendances'] = ClassAttendance.objects.filter(
            student=self.object
        ).select_related('class_obj')[:20]
        return context


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    """Update student"""
    model = Student
    form_class = StudentForm
    template_name = 'core/student_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:student_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Student {form.instance.student_reg_number} updated successfully.')
        return super().form_valid(form)


# ============ Staff Views ============

class StaffListView(LoginRequiredMixin, ListView):
    """List all staff"""
    model = Staff
    ordering = ['-created_at']
    template_name = 'core/staff_list.html'
    context_object_name = 'staff'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('person', 'department')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(staff_number__icontains=search) |
                Q(person__first_name__icontains=search) |
                Q(person__last_name__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Department
        
        context['staff_categories'] = Staff.StaffCategory.choices
        context['departments'] = Department.objects.filter(is_active=True)
        context['total_academic'] = Staff.objects.filter(staff_category='academic', is_active=True).count()
        context['total_administrative'] = Staff.objects.filter(staff_category='administrative', is_active=True).count()
        context['total_technical'] = Staff.objects.filter(staff_category='technical', is_active=True).count()
        return context


class StaffDetailView(LoginRequiredMixin, DetailView):
    """Staff detail view"""
    model = Staff
    template_name = 'core/staff_detail.html'
    context_object_name = 'staff'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Class
        context['classes_teaching'] = Class.objects.filter(
            lecturer=self.object,
            is_active=True
        )[:20]
        return context


class StaffUpdateView(LoginRequiredMixin, UpdateView):
    """Update staff"""
    model = Staff
    form_class = StaffForm
    template_name = 'core/staff_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:staff_detail', kwargs={'pk': self.object.pk})


# ============ Academic Unit Views ============

class AcademicUnitListView(LoginRequiredMixin, ListView):
    """List all academic units"""
    model = AcademicUnit
    ordering = ['-created_at']
    template_name = 'core/academic_unit_list.html'
    context_object_name = 'units'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('department')
        department_id = self.request.GET.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Department, Class
        
        context['departments'] = Department.objects.filter(is_active=True)
        context['total_classes'] = Class.objects.filter(is_active=True).count()
        return context


class AcademicUnitDetailView(LoginRequiredMixin, DetailView):
    """Academic unit detail view"""
    model = AcademicUnit
    template_name = 'core/academic_unit_detail.html'
    context_object_name = 'unit'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = self.object.classes.filter(is_active=True)[:20]
        context['total_classes'] = self.object.classes.filter(is_active=True).count()
        return context


class AcademicUnitCreateView(LoginRequiredMixin, CreateView):
    """Create new academic unit"""
    model = AcademicUnit
    form_class = AcademicUnitForm
    template_name = 'core/academic_unit_form.html'
    success_url = reverse_lazy('core:academic_unit_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Academic Unit {form.instance.code} created successfully.')
        return super().form_valid(form)


class AcademicUnitUpdateView(LoginRequiredMixin, UpdateView):
    """Update academic unit"""
    model = AcademicUnit
    form_class = AcademicUnitForm
    template_name = 'core/academic_unit_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:academic_unit_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Academic Unit {form.instance.code} updated successfully.')
        return super().form_valid(form)


# ============ Class Views ============

class ClassListView(LoginRequiredMixin, ListView):
    """List all classes"""
    model = Class
    ordering = ['-created_at']
    template_name = 'core/class_list.html'
    context_object_name = 'classes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related(
            'academic_unit', 'program', 'lecturer__person'
        )
        program_id = self.request.GET.get('program_id')
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        semester = self.request.GET.get('semester')
        if semester:
            queryset = queryset.filter(semester=semester)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(class_code__icontains=search) |
                Q(academic_unit__name__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Program, AcademicUnit, Staff
        
        context['programs'] = Program.objects.filter(is_active=True)
        context['academic_units'] = AcademicUnit.objects.filter(is_active=True)
        context['lecturers'] = Staff.objects.filter(is_active=True, staff_category='lecturer').select_related('person')
        context['semester_choices'] = [(1, 'Semester 1'), (2, 'Semester 2'), (3, 'Semester 3')]
        context['total_students_enrolled'] = ClassEnrollment.objects.filter(
            class_obj__in=self.get_queryset(),
            status='registered'
        ).count()
        return context


class ClassDetailView(LoginRequiredMixin, DetailView):
    """Class detail view"""
    model = Class
    template_name = 'core/class_detail.html'
    context_object_name = 'class_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import ClassEnrollment
        from apps.classroom.models import ClassAttendance
        
        context['enrolled_students'] = self.object.enrollments.filter(
            status='registered'
        ).select_related('student__person')[:50]
        context['enrollment_count'] = self.object.enrollments.filter(status='registered').count()
        context['recent_attendance'] = ClassAttendance.objects.filter(
            class_obj=self.object
        ).select_related('student__person')[:20]
        context['attendance_percentage'] = self.object.get_attendance_percentage()
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    """Create new class"""
    model = Class
    form_class = ClassForm
    template_name = 'core/class_form.html'
    success_url = reverse_lazy('core:class_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Class {form.instance.class_code} created successfully.')
        return super().form_valid(form)


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    """Update class"""
    model = Class
    form_class = ClassForm
    template_name = 'core/class_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:class_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Class {form.instance.class_code} updated successfully.')
        return super().form_valid(form)


class ClassEnrollView(LoginRequiredMixin, UpdateView):
    """Enroll students in class"""
    model = Class
    ordering = ['-created_at']
    template_name = 'core/class_enroll.html'
    fields = ['students']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_students'] = Student.objects.filter(
            program=self.object.program,
            is_active=True,
            status='active'
        ).select_related('person')[:100]
        context['enrolled_students'] = self.object.students.filter(is_active=True)
        return context
    
    def get_success_url(self):
        return reverse_lazy('core:class_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Students enrolled in {form.instance.class_code} successfully.')
        return super().form_valid(form)



# ============ API Endpoints ============

@csrf_exempt
def api_search(request):
    """Global search API endpoint"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    results = []
    
    # Search institutions
    institutions = Institution.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query),
        is_active=True
    )[:5]
    for inst in institutions:
        results.append({
            'type': 'institution',
            'id': inst.id,
            'name': inst.name,
            'url': reverse('core:institution_detail', kwargs={'pk': inst.id})
        })
    
    # Search persons
    persons = Person.objects.filter(
        Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query),
        is_active=True
    )[:5]
    for person in persons:
        results.append({
            'type': 'person',
            'id': person.id,
            'name': person.full_name,
            'url': reverse('core:person_detail', kwargs={'pk': person.id})
        })
    
    return JsonResponse({'results': results})


@csrf_exempt
def api_hierarchy(request):
    """Get institution hierarchy as JSON"""
    institutions = Institution.objects.filter(is_active=True).prefetch_related(
        'colleges__schools__departments'
    )
    
    data = []
    for inst in institutions:
        inst_data = {
            'id': inst.id,
            'name': inst.name,
            'code': inst.code,
            'colleges': []
        }
        for college in inst.colleges.filter(is_active=True):
            college_data = {
                'id': college.id,
                'name': college.name,
                'code': college.code,
                'schools': []
            }
            for school in college.schools.filter(is_active=True):
                school_data = {
                    'id': school.id,
                    'name': school.name,
                    'code': school.code,
                    'departments': []
                }
                for dept in school.departments.filter(is_active=True):
                    school_data['departments'].append({
                        'id': dept.id,
                        'name': dept.name,
                        'code': dept.code
                    })
                college_data['schools'].append(school_data)
            inst_data['colleges'].append(college_data)
        data.append(inst_data)
    
    return JsonResponse({'hierarchy': data})

def toggle_person_status(request, pk):
    if request.method == 'POST':
        try:
            person = Person.objects.get(pk=pk)
            person.is_active = not person.is_active
            person.save()
            return JsonResponse({'success': True, 'message': f'Person {person.full_name()} status updated'})
        except Person.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Person not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# ============ Export Views ============

@permission_required(VMSPermissions.SYSTEM_VIEW_LOGS)
def export_students_csv(request):
    """Export students to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Registration Number', 'First Name', 'Last Name', 'Email', 'Phone',
        'Program', 'Department', 'Current Year', 'Status', 'Admission Date'
    ])
    
    students = Student.objects.select_related('person', 'program', 'department').filter(is_active=True)
    for student in students:
        writer.writerow([
            student.student_reg_number,
            student.person.first_name,
            student.person.last_name,
            student.person.email,
            student.person.phone_number,
            student.program.name,
            student.department.name,
            student.current_year,
            student.status,
            student.admission_date
        ])
    
    return response


@permission_required(VMSPermissions.SYSTEM_VIEW_LOGS)
def export_staff_csv(request):
    """Export staff to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="staff.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Staff Number', 'First Name', 'Last Name', 'Email', 'Phone',
        'Department', 'Job Title', 'Category', 'Employment Type', 'Joined Date'
    ])
    
    staff_members = Staff.objects.select_related('person', 'department').filter(is_active=True)
    for staff in staff_members:
        writer.writerow([
            staff.staff_number,
            staff.person.first_name,
            staff.person.last_name,
            staff.person.email,
            staff.person.phone_number,
            staff.department.name,
            staff.job_title,
            staff.get_staff_category_display(),
            staff.get_employment_type_display(),
            staff.joined_date
        ])
    
    return response


# ============ API Endpoints ============

@csrf_exempt
def api_search(request):
    """Global search API endpoint"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    results = []
    
    # Search students
    students = Student.objects.filter(
        Q(student_reg_number__icontains=query) |
        Q(person__first_name__icontains=query) |
        Q(person__last_name__icontains=query),
        is_active=True
    ).select_related('person')[:5]
    
    for student in students:
        results.append({
            'type': 'student',
            'id': student.id,
            'name': student.person.full_name,
            'identifier': student.student_reg_number,
            'url': reverse('core:student_detail', kwargs={'pk': student.id})
        })
    
    # Search staff
    staff_members = Staff.objects.filter(
        Q(staff_number__icontains=query) |
        Q(person__first_name__icontains=query) |
        Q(person__last_name__icontains=query),
        is_active=True
    ).select_related('person')[:5]
    
    for staff in staff_members:
        results.append({
            'type': 'staff',
            'id': staff.id,
            'name': staff.person.full_name,
            'identifier': staff.staff_number,
            'url': reverse('core:staff_detail', kwargs={'pk': staff.id})
        })
    
    return JsonResponse({'results': results})


@csrf_exempt
def api_hierarchy(request):
    """Get institution hierarchy as JSON"""
    institutions = Institution.objects.filter(is_active=True).prefetch_related(
        'colleges__schools__departments'
    )
    
    data = []
    for inst in institutions:
        inst_data = {
            'id': inst.id,
            'name': inst.name,
            'code': inst.code,
            'colleges': []
        }
        for college in inst.colleges.filter(is_active=True):
            college_data = {
                'id': college.id,
                'name': college.name,
                'code': college.code,
                'schools': []
            }
            for school in college.schools.filter(is_active=True):
                school_data = {
                    'id': school.id,
                    'name': school.name,
                    'code': school.code,
                    'departments': []
                }
                for dept in school.departments.filter(is_active=True):
                    school_data['departments'].append({
                        'id': dept.id,
                        'name': dept.name,
                        'code': dept.code
                    })
                college_data['schools'].append(school_data)
            inst_data['colleges'].append(college_data)
        data.append(inst_data)
    
    return JsonResponse({'hierarchy': data})


queryset = Class.objects.annotate(
    enrollments_count=Count('enrollments')
)


units = AcademicUnit.objects.annotate(
    classes_count=Count('classes')
)

def toggle_academic_unit_status(request, pk):
    if request.method == 'POST':
        try:
            unit = AcademicUnit.objects.get(pk=pk)
            unit.is_active = not unit.is_active
            unit.save()
            return JsonResponse({'success': True, 'message': f'Unit {unit.code} status updated'})
        except AcademicUnit.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Unit not found'})
    return JsonResponse({'success': False})


def staff_create(request):
    if request.method == 'POST':
        try:
            # Create person first
            person = Person.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                date_of_birth=request.POST.get('date_of_birth') or None,
                person_type='staff'
            )
            
            # Create staff
            staff = Staff.objects.create(
                person=person,
                staff_number=request.POST.get('staff_number'),
                staff_category=request.POST.get('staff_category'),
                job_title=request.POST.get('job_title'),
                department_id=request.POST.get('department') or None,
                is_active=request.POST.get('is_active') == 'on'
            )
            
            return JsonResponse({'success': True, 'message': f'Staff {person.get_full_name()} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@csrf_exempt
def toggle_staff_status(request, pk):
    if request.method == 'POST':
        try:
            staff = Staff.objects.get(pk=pk)
            staff.is_active = not staff.is_active
            staff.save()
            return JsonResponse({'success': True})
        except Staff.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Staff not found'})
    return JsonResponse({'success': False})


def get_staff_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        staff = Staff.objects.select_related('person', 'department').get(pk=pk)
        departments = Department.objects.filter(is_active=True)
        
        html = f'''
        <form id="editStaffForm" method="POST" action="/core/staff/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">First Name</label>
                        <input type="text" name="first_name" class="form-control" value="{staff.person.first_name or ''}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label required">Last Name</label>
                        <input type="text" name="last_name" class="form-control" value="{staff.person.last_name or ''}" required>
                    </div>
                    <div class="col-12">
                        <label class="form-label required">Email</label>
                        <input type="email" name="email" class="form-control" value="{staff.person.email or ''}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{staff.person.phone or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Staff Number</label>
                        <input type="text" name="staff_number" class="form-control" value="{staff.staff_number or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label required">Staff Category</label>
                        <select name="staff_category" class="form-select" required>
                            <option value="academic" {'selected' if staff.staff_category == 'academic' else ''}>Academic</option>
                            <option value="administrative" {'selected' if staff.staff_category == 'administrative' else ''}>Administrative</option>
                            <option value="technical" {'selected' if staff.staff_category == 'technical' else ''}>Technical</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Department</label>
                        <select name="department" class="form-select">
                            <option value="">Select Department</option>
        '''
        for dept in departments:
            selected = 'selected' if staff.department_id == dept.id else ''
            html += f'<option value="{dept.id}" {selected}>{dept.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Job Title</label>
                        <input type="text" name="job_title" class="form-control" value="{staff.job_title or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Date of Birth</label>
                        <input type="date" name="date_of_birth" class="form-control" value="{staff.person.date_of_birth|date:'Y-m-d' if staff.person.date_of_birth else ''}">
                    </div>
                    <div class="col-md-6">
                        <div class="form-check mt-2">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if staff.is_active else ''}>
                            <label class="form-check-label">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Staff</button>
            </div>
        </form>
        <script>
            $('#editStaffForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this), btn = form.find('button[type="submit"]');
                btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                $.ajax({{
                    url: form.attr('action'), method: 'POST', data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editStaffModal').modal('hide');
                            toastr.success(response.message || 'Staff updated successfully');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{ toastr.error(response.error || 'Failed to update'); btn.prop('disabled', false).html('Update Staff'); }}
                    }}, error: function() {{ toastr.error('An error occurred'); btn.prop('disabled', false).html('Update Staff'); }}
                }});
            }});
            $('#editStaffForm .form-select').select2({{theme: 'bootstrap-5', width: '100%', dropdownParent: $('#editStaffModal')}});
        </script>
        '''
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

def student_create(request):
    if request.method == 'POST':
        try:
            # Create person first
            person = Person.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                person_type='student'
            )
            
            # Create student
            student = Student.objects.create(
                person=person,
                student_reg_number=request.POST.get('student_reg_number'),
                program_id=request.POST.get('program'),
                current_year=request.POST.get('current_year') or 1,
                status=request.POST.get('status') or 'active',
                enrollment_date=request.POST.get('enrollment_date') or None,
                expected_graduation=request.POST.get('expected_graduation') or None,
                is_active=request.POST.get('is_active') == 'on'
            )
            
            return JsonResponse({'success': True, 'message': f'Student {person.get_full_name()} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@csrf_exempt
def toggle_student_status(request, pk):
    if request.method == 'POST':
        try:
            student = Student.objects.get(pk=pk)
            student.is_active = not student.is_active
            student.save()
            return JsonResponse({'success': True})
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
    return JsonResponse({'success': False})


def get_student_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        student = Student.objects.select_related('person', 'program').get(pk=pk)
        programs = Program.objects.filter(is_active=True)
        
        html = f'''
        <form id="editStudentForm" method="POST" action="/core/students/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label required">First Name</label>
                        <input type="text" name="first_name" class="form-control" value="{student.person.first_name or ''}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label required">Last Name</label>
                        <input type="text" name="last_name" class="form-control" value="{student.person.last_name or ''}" required>
                    </div>
                    <div class="col-12">
                        <label class="form-label required">Email</label>
                        <input type="email" name="email" class="form-control" value="{student.person.email or ''}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-control" value="{student.person.phone or ''}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Registration Number</label>
                        <input type="text" name="student_reg_number" class="form-control" value="{student.student_reg_number or ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label required">Program</label>
                        <select name="program" class="form-select" required>
                            <option value="">Select Program</option>
        '''
        for program in programs:
            selected = 'selected' if student.program_id == program.id else ''
            html += f'<option value="{program.id}" {selected}>{program.name}</option>'
        
        html += f'''
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Current Year</label>
                        <select name="current_year" class="form-select">
                            <option value="1" {'selected' if student.current_year == 1 else ''}>Year 1</option>
                            <option value="2" {'selected' if student.current_year == 2 else ''}>Year 2</option>
                            <option value="3" {'selected' if student.current_year == 3 else ''}>Year 3</option>
                            <option value="4" {'selected' if student.current_year == 4 else ''}>Year 4</option>
                            <option value="5" {'selected' if student.current_year == 5 else ''}>Year 5</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Status</label>
                        <select name="status" class="form-select">
                            <option value="active" {'selected' if student.status == 'active' else ''}>Active</option>
                            <option value="inactive" {'selected' if student.status == 'inactive' else ''}>Inactive</option>
                            <option value="graduated" {'selected' if student.status == 'graduated' else ''}>Graduated</option>
                            <option value="suspended" {'selected' if student.status == 'suspended' else ''}>Suspended</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Enrollment Date</label>
                        <input type="date" name="enrollment_date" class="form-control" value="{student.enrollment_date|date:'Y-m-d' if student.enrollment_date else ''}">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Expected Graduation</label>
                        <input type="date" name="expected_graduation" class="form-control" value="{student.expected_graduation|date:'Y-m-d' if student.expected_graduation else ''}">
                    </div>
                    <div class="col-md-6">
                        <div class="form-check mt-2">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if student.is_active else ''}>
                            <label class="form-check-label">Active Student</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Student</button>
            </div>
        </form>
        <script>
            $('#editStudentForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this), btn = form.find('button[type="submit"]');
                btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                $.ajax({{
                    url: form.attr('action'), method: 'POST', data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editStudentModal').modal('hide');
                            toastr.success(response.message || 'Student updated successfully');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{ toastr.error(response.error || 'Failed to update'); btn.prop('disabled', false).html('Update Student'); }}
                    }}, error: function() {{ toastr.error('An error occurred'); btn.prop('disabled', false).html('Update Student'); }}
                }});
            }});
            $('#editStudentForm .form-select').select2({{theme: 'bootstrap-5', width: '100%', dropdownParent: $('#editStudentModal')}});
        </script>
        '''
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

def update_student(request, pk):
    if request.method == 'POST':
        try:
            student = Student.objects.select_related('person').get(pk=pk)
            
            # Update person
            student.person.first_name = request.POST.get('first_name')
            student.person.last_name = request.POST.get('last_name')
            student.person.email = request.POST.get('email')
            student.person.phone = request.POST.get('phone')
            student.person.save()
            
            # Update student
            student.student_reg_number = request.POST.get('student_reg_number')
            student.program_id = request.POST.get('program')
            student.current_year = request.POST.get('current_year')
            student.status = request.POST.get('status')
            student.enrollment_date = request.POST.get('enrollment_date') or None
            student.expected_graduation = request.POST.get('expected_graduation') or None
            student.is_active = request.POST.get('is_active') == 'on'
            student.save()
            
            return JsonResponse({'success': True, 'message': f'Student {student.person.get_full_name()} updated successfully'})
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

def student_create(request):
    if request.method == 'POST':
        try:
            # Get or create person
            person_id = request.POST.get('person')
            if person_id:
                person = Person.objects.get(id=person_id)
            else:
                # Create new person
                person = Person.objects.create(
                    first_name=request.POST.get('first_name', ''),
                    last_name=request.POST.get('last_name', ''),
                    email=request.POST.get('email', ''),
                    phone=request.POST.get('phone', ''),
                    person_type='student'
                )
            
            # Create student
            student = Student.objects.create(
                person=person,
                student_reg_number=request.POST.get('student_reg_number'),
                program_id=request.POST.get('program'),
                current_year=request.POST.get('current_year') or 1,
                current_semester=request.POST.get('current_semester') or 1,
                admission_date=request.POST.get('admission_date') or None,
                expected_graduation=request.POST.get('expected_graduation') or None,
                mode_of_study=request.POST.get('mode_of_study') or 'full_time',
                status=request.POST.get('status') or 'active',
                supervisor_id=request.POST.get('supervisor') or None,
                class_representative=request.POST.get('class_representative') == 'on',
                has_disability=request.POST.get('has_disability') == 'on',
                disability_description=request.POST.get('disability_description'),
                is_active=True
            )
            
            # Update person with additional info if provided
            if request.POST.get('first_name'):
                person.first_name = request.POST.get('first_name')
                person.last_name = request.POST.get('last_name')
                person.email = request.POST.get('email')
                person.phone = request.POST.get('phone')
                person.save()
            
            return JsonResponse({'success': True, 'message': f'Student {person.get_full_name()} created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

# def get_college_schools(request, pk):
#     """Get schools under a college for AJAX modal"""
#     try:
#         college = College.objects.get(pk=pk)
#         schools = college.schools.filter(is_active=True)
        
#         html = '<div class="list-group">'
#         for school in schools:
#             html += f'''
#             <div class="list-group-item d-flex justify-content-between align-items-center">
#                 <div>
#                     <strong>{school.name}</strong>
#                     <br><small class="text-muted">{school.code|default:"No code"}</small>
#                 </div>
#                 <div>
#                     <span class="badge bg-info">{school.departments.count()} Departments</span>
#                     <button class="btn btn-sm btn-outline-primary ms-2" onclick="viewSchool({school.id})">
#                         <i class="bx bx-show"></i>
#                     </button>
#                 </div>
#             </div>
#             '''
#         html += '</div>'
        
#         if not schools:
#             html = '<div class="text-center py-4"><p class="text-muted">No schools found under this college.</p></div>'
        
#         return JsonResponse({'html': html, 'success': True})
#     except Exception as e:
#         return JsonResponse({'error': str(e), 'success': False}, status=400)