from django.urls import path
from django.shortcuts import render
from . import views
from . import views_institution

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('realtime-stats/', views.realtime_stats, name='realtime_stats'),
    
    #  Institution URLs 
    path('institutions/', views_institution.InstitutionListView.as_view(), name='institution_list'),
    path('institutions/create/', views_institution.InstitutionCreateView.as_view(), name='institution_create'),
    path('institutions/<int:pk>/', views_institution.InstitutionDetailView.as_view(), name='institution_detail'),
    path('institutions/<int:pk>/edit/', views_institution.InstitutionUpdateView.as_view(), name='institution_edit'),
    path('institutions/<int:pk>/delete/', views_institution.InstitutionDeleteView.as_view(), name='institution_delete'),
    # path('institutions/<int:pk>/restore/', views_institution.institution_restore, name='institution_restore'),
    
    #  College URLs 
    path('colleges/', views_institution.CollegeListView.as_view(), name='college_list'),
    path('colleges/create/', views_institution.CollegeCreateView.as_view(), name='college_create'),
    path('colleges/<int:pk>/detail/', views_institution.CollegeDetailView.as_view(), name='college_detail'),
    path('colleges/<int:pk>/edit/', views_institution.CollegeUpdateView.as_view(), name='college_edit'),
    path('colleges/<int:pk>/toggle-status/', views_institution.toggle_college_status, name='college_toggle_status'),
    path('schools/<int:pk>/update/', views_institution.update_school, name='school_update'),
    path('schools/<int:pk>/edit/', views_institution.get_school_edit_form, name='school_edit'),
    # path('colleges/<int:pk>/schools/', views_institution.get_college_schools, name='college_schools'),
    path('colleges/<int:pk>/delete/', views_institution.CollegeDeleteView.as_view(), name='college_delete'),

    path('colleges/create/', views_institution.create_college, name='college_create'),
    path('colleges/<int:pk>/detail/', views_institution.get_college_detail, name='college_detail'),
    path('colleges/<int:pk>/edit-form/', views_institution.get_college_edit_form, name='college_edit_form'),
    path('colleges/<int:pk>/update/', views_institution.update_college, name='college_update'),
  
    path('colleges/<int:pk>/schools/', views_institution.get_college_schools, name='college_schools'),
    
    #  School URLs 
    path('schools/', views_institution.SchoolListView.as_view(), name='school_list'),
    path('schools/create/', views_institution.SchoolCreateView.as_view(), name='school_create'),
    path('schools/<int:pk>/', views_institution.SchoolDetailView.as_view(), name='school_detail'),
    path('schools/<int:pk>/edit/', views_institution.SchoolUpdateView.as_view(), name='school_edit'),
    path('schools/<int:pk>/toggle-status/', views_institution.toggle_school_status, name='school_toggle_status'),
    path('schools/<int:pk>/delete/', views_institution.SchoolDeleteView.as_view(), name='school_delete'),

    # path('schools/create/', views_institution.create_school, name='school_create'),
    path('schools/<int:pk>/edit-form/', views_institution.get_school_edit_form, name='school_edit_form'),
    path('schools/<int:pk>/update/', views_institution.update_school, name='school_update'),
   
    
    #  Department URLs 
    path('departments/', views_institution.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views_institution.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/', views_institution.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/edit/', views_institution.DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/edit/', views_institution.get_department_edit_form, name='department_edit'),
    path('departments/<int:pk>/update/', views_institution.update_department, name='department_update'),
    path('departments/<int:pk>/toggle-status/', views_institution.toggle_department_status, name='department_toggle_status'),
    path('departments/<int:pk>/delete/', views_institution.DepartmentDeleteView.as_view(), name='department_delete'),
    
    #  Program URLs 
    path('programs/', views_institution.ProgramListView.as_view(), name='program_list'),
    path('programs/create/', views_institution.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/', views_institution.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/<int:pk>/edit/', views_institution.ProgramUpdateView.as_view(), name='program_edit'),
    path('programs/<int:pk>/delete/', views_institution.ProgramDeleteView.as_view(), name='program_delete'),
    path('programs/<int:pk>/edit/', views_institution.get_program_edit_form, name='program_edit'),
    path('programs/<int:pk>/update/', views_institution.update_program, name='program_update'),
    path('programs/<int:pk>/toggle-status/', views_institution.toggle_program_status, name='program_toggle_status'),
    path('programs/<int:pk>/delete/', views_institution.ProgramDeleteView.as_view(), name='program_delete'),
    
    #  Person URLs 
    path('persons/', views.PersonListView.as_view(), name='person_list'),
    path('persons/create/', views.PersonCreateView.as_view(), name='person_create'),
    path('persons/<int:pk>/', views.PersonDetailView.as_view(), name='person_detail'),
    path('persons/<int:pk>/edit/', views.PersonUpdateView.as_view(), name='person_edit'),
    # path('persons/<int:pk>/edit/', views.get_person_edit_form, name='person_edit'),
    # path('persons/<int:pk>/update/', views.update_person, name='person_update'),
    path('persons/<int:pk>/toggle-status/', views.toggle_person_status, name='person_toggle_status'),
    path('persons/<int:pk>/delete/', views.PersonDeleteView.as_view(), name='person_delete'),
    
    #  Student URLs 
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('students/<int:pk>/edit/', views.get_student_edit_form, name='student_edit'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:pk>/toggle-status/', views.toggle_student_status, name='student_toggle_status'),
    path('students/<int:pk>/update/', views.update_student, name='student_update'),
    # path('students/<int:pk>/edit/', views.get_student_edit_form, name='student_edit'),
    # path('students/<int:pk>/update/', views.update_student, name='student_update'),
    # path('students/<int:pk>/toggle-status/', views.toggle_student_status, name='student_toggle_status'),
    
    #  Staff URLs 
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/<int:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    path('staff/<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),
    path('staff/<int:pk>/edit/', views.get_staff_edit_form, name='staff_edit'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/toggle-status/', views.toggle_staff_status, name='staff_toggle_status'),
    
    #  Academic URLs 
    path('academic-units/', views.AcademicUnitListView.as_view(), name='academic_unit_list'),
    path('academic-units/create/', views.AcademicUnitCreateView.as_view(), name='academic_unit_create'),
    path('academic-units/<int:pk>/', views.AcademicUnitDetailView.as_view(), name='academic_unit_detail'),
    path('academic-units/<int:pk>/edit/', views.AcademicUnitUpdateView.as_view(), name='academic_unit_edit'),
    path('academic-units/<int:pk>/toggle-status/', views.toggle_academic_unit_status, name='toggle_academic_unit_status'),
    
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/create/', views.ClassCreateView.as_view(), name='class_create'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/<int:pk>/edit/', views.ClassUpdateView.as_view(), name='class_edit'),
    path('classes/<int:pk>/enroll/', views.ClassEnrollView.as_view(), name='class_enroll'),
    
    #  API Endpoints 
    path('api/search/', views.api_search, name='api_search'),
    path('api/hierarchy/', views.api_hierarchy, name='api_hierarchy'),
]

# Error handlers
# def handler404(request, exception):
#     return render(request, '404.html', status=404)

# def handler500(request):
#     return render(request, '500.html', status=500)

# def handler403(request, exception):
#     return render(request, '403.html', status=403)