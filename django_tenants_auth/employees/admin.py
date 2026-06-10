from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django_tenants_auth.core.admin import TimeStampedModelAdmin
from django_tenants_auth.employees.models import Employee, Department


class DepartmentAdminForm(forms.ModelForm):
    """Custom form for Department admin."""
    
    class Meta:
        model = Department
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        manager = cleaned_data.get('manager')
        
        # Prevent circular parent references
        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise forms.ValidationError("A department cannot be its own parent.")
        
        # Ensure manager belongs to this department or is None
        if manager and manager.department and manager.department != self.instance:
            raise forms.ValidationError(
                "Manager must belong to this department or have no department."
            )
        
        return cleaned_data


@admin.register(Department)
class DepartmentAdmin(TimeStampedModelAdmin):
    form = DepartmentAdminForm
    list_display = ['name', 'slug', 'parent', 'manager', 'employee_count', 'created_at']
    list_filter = ['parent']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = TimeStampedModelAdmin.readonly_fields + ['employee_count_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Hierarchy', {
            'fields': ('parent', 'manager')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'employee_count_display'),
            'classes': ('collapse',),
        }),
    )
    
    def employee_count(self, obj):
        return obj.employees.count()
    employee_count.short_description = 'Employees'
    
    def employee_count_display(self, obj):
        """Readonly display for employee count."""
        return obj.employees.count()
    employee_count_display.short_description = 'Number of Employees'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetching."""
        return super().get_queryset(request).prefetch_related('employees')


class EmployeeAdminForm(forms.ModelForm):
    """Custom form for Employee admin with validation."""
    
    class Meta:
        model = Employee
        fields = '__all__'
    
    def clean_emp_id(self):
        emp_id = self.cleaned_data.get('emp_id')
        if emp_id and Employee.objects.filter(emp_id=emp_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An employee with this ID already exists.")
        return emp_id
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        status = cleaned_data.get('status')
        
        # If employee is terminated, ensure they don't have an active user account
        if status == 'terminated' and user and user.is_active:
            raise forms.ValidationError(
                "Cannot set status to 'terminated' while user account is active. "
                "Please deactivate the user account first."
            )
        
        # Validate salary and commission
        salary = cleaned_data.get('salary')
        commission = cleaned_data.get('commission')
        
        if salary is not None and salary < 0:
            raise forms.ValidationError("Salary cannot be negative.")
        
        if commission is not None and commission < 0:
            raise forms.ValidationError("Commission cannot be negative.")
        
        # Validate dates
        appointment_date = cleaned_data.get('appointment_date')
        joining_date = cleaned_data.get('joining_date')
        
        if appointment_date and joining_date and joining_date < appointment_date:
            raise forms.ValidationError("Joining date cannot be before appointment date.")
        
        return cleaned_data


@admin.register(Employee)
class EmployeeAdmin(TimeStampedModelAdmin):
    form = EmployeeAdminForm
    list_display = [
        'emp_id', 'name', 'department', 'designation', 
        'status', 'has_user_account', 'mobile_number', 'created_at'
    ]
    list_filter = [
        'status', 'gender', 'department', 'designation',
        'blood_group', 'religion'
    ]
    search_fields = [
        'name', 'emp_id', 'mobile_number', 'designation',
        'user__email'
    ]
    readonly_fields = TimeStampedModelAdmin.readonly_fields + ['slug', 'has_user_account_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'emp_id', 'department', 
                'designation', 'status'
            )
        }),
        ('Contact Information', {
            'fields': ('mobile_number', 'address')
        }),
        ('Personal Information', {
            'fields': (
                'birth_date', 'gender', 'blood_group', 
                'religion', 'image_path'
            ),
            'classes': ('collapse',),
        }),
        ('Employment Details', {
            'fields': (
                'appointment_date', 'joining_date', 
                'salary', 'commission'
            ),
            'classes': ('collapse',),
        }),
        ('User Account', {
            'fields': ('user', 'has_user_account_display'),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def has_user_account(self, obj):
        """Display whether employee has a user account."""
        if obj.user:
            return f"✓ {obj.user.email}"
        return "✗ No account"
    has_user_account.short_description = 'User Account'

    def has_user_account_display(self, obj):
        """Readonly display for user account status."""
        return "Yes" if obj.user else "No"
    has_user_account_display.short_description = 'Has User Account'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'department', 'user', 'created_by'
        )
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new employee."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_employees', 'deactivate_employees', 'export_as_csv']
    
    def activate_employees(self, request, queryset):
        """Bulk activate selected employees."""
        count = queryset.update(status='active')
        self.message_user(
            request,
            f"Successfully activated {count} employee(s)."
        )
    activate_employees.short_description = "Activate selected employees"
    
    def deactivate_employees(self, request, queryset):
        """Bulk deactivate selected employees."""
        count = queryset.update(status='inactive')
        self.message_user(
            request,
            f"Successfully deactivated {count} employee(s)."
        )
    deactivate_employees.short_description = "Deactivate selected employees"
    
    def export_as_csv(self, request, queryset):
        """Export selected employees as CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="employees.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Name', 'Department', 'Designation',
            'Status', 'Email', 'Mobile', 'Joining Date'
        ])
        
        for employee in queryset.select_related('department', 'user'):
            writer.writerow([
                employee.emp_id,
                employee.name,
                employee.department.name if employee.department else '',
                employee.designation,
                employee.status,
                employee.user.email if employee.user else '',
                employee.mobile_number,
                employee.joining_date,
            ])
        
        return response
    export_as_csv.short_description = "Export selected as CSV"