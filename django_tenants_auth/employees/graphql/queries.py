import strawberry
from typing import List, Optional
from strawberry.types import Info
from django_tenants_auth.authentication.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator

from django_tenants_auth.employees.models import Employee, Department
from django_tenants_auth.employees.graphql.types import (
    EmployeeType,
    EmployeeListType,
    DepartmentType,
)
from django_tenants_auth.employees.services import EmployeeService


@strawberry.type
class EmployeeQuery:
    
    @strawberry.field
    @login_required
    def employees(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        department_id: Optional[strawberry.ID] = None,
        status: Optional[str] = None,
        designation: Optional[str] = None,
        gender: Optional[str] = None,
        order_by: Optional[str] = "-created_at",
    ) -> EmployeeListType:
        """
        Get paginated list of employees with filters.
        
        Filters:
        - search: Search in name, emp_id, mobile_number
        - department_id: Filter by department
        - status: Filter by status (active, inactive, etc.)
        - designation: Filter by designation
        - gender: Filter by gender
        - order_by: Field to order by (prefix with - for descending)
        """
        tenant = info.context.request.tenant
        
        # Build queryset with optimizations
        queryset = Employee.objects.select_related(
            'department', 'user', 'created_by'
        ).all()
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(emp_id__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if designation:
            queryset = queryset.filter(designation__icontains=designation)
        
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Apply ordering
        if order_by:
            queryset = queryset.order_by(order_by)
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Map to GraphQL types
        employees = []
        for emp in page_obj:
            employees.append(EmployeeService._map_employee_to_type(emp))
        
        return EmployeeListType(
            employees=employees,
            total_count=paginator.count,
            page=page,
            page_size=page_size,
            total_pages=paginator.num_pages,
        )
    
    @strawberry.field
    @login_required
    def employee(
        self,
        info: Info,
        id: Optional[strawberry.ID] = None,
        emp_id: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> Optional[EmployeeType]:
        """
        Get a single employee by ID, employee ID, or slug.
        """
        tenant = info.context.request.tenant
        
        queryset = Employee.objects.select_related(
            'department', 'user', 'created_by'
        )
        
        if id:
            employee = queryset.filter(id=id).first()
        elif emp_id:
            employee = queryset.filter(emp_id=emp_id).first()
        elif slug:
            employee = queryset.filter(slug=slug).first()
        else:
            return None
        
        if employee:
            return EmployeeService._map_employee_to_type(employee)
        
        return None
    
    @strawberry.field
    @login_required
    def employee_stats(self, info: Info) -> 'EmployeeStatsType':
        """
        Get employee statistics for dashboard.
        """
        tenant = info.context.request.tenant
        
        total = Employee.objects.count()
        active = Employee.objects.filter(status='active').count()
        inactive = Employee.objects.filter(status='inactive').count()
        on_leave = Employee.objects.filter(status='on_leave').count()
        terminated = Employee.objects.filter(status='terminated').count()
        
        # Department distribution
        departments = Department.objects.annotate(
            employee_count=Count('employees')
        ).values('name', 'employee_count')
        
        return EmployeeStatsType(
            total_employees=total,
            active_employees=active,
            inactive_employees=inactive,
            on_leave_employees=on_leave,
            terminated_employees=terminated,
            department_distribution=[
                DepartmentDistribution(
                    department_name=d['name'],
                    count=d['employee_count']
                )
                for d in departments
            ]
        )
    
    @strawberry.field
    @login_required
    def departments(
        self,
        info: Info,
        parent_id: Optional[strawberry.ID] = None,
    ) -> List[DepartmentType]:
        """
        Get all departments, optionally filtered by parent.
        """
        tenant = info.context.request.tenant
        
        queryset = Department.objects.select_related(
            'parent', 'manager'
        ).prefetch_related('employees')
        
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        
        departments = []
        for dept in queryset:
            departments.append(DepartmentType(
                id=str(dept.id),
                name=dept.name,
                slug=dept.slug,
                description=dept.description or "",
                parent_id=str(dept.parent_id) if dept.parent_id else None,
                parent_name=dept.parent.name if dept.parent else None,
                manager_id=str(dept.manager_id) if dept.manager_id else None,
                manager_name=dept.manager.name if dept.manager else None,
                employee_count=dept.employees.count(),
                created_at=dept.created_at.isoformat(),
                updated_at=dept.updated_at.isoformat(),
            ))
        
        return departments
    
    @strawberry.field
    @login_required
    def department(
        self,
        info: Info,
        id: Optional[strawberry.ID] = None,
        slug: Optional[str] = None,
    ) -> Optional[DepartmentType]:
        """
        Get a single department by ID or slug.
        """
        tenant = info.context.request.tenant
        
        queryset = Department.objects.select_related('parent', 'manager')
        
        if id:
            dept = queryset.filter(id=id).first()
        elif slug:
            dept = queryset.filter(slug=slug).first()
        else:
            return None
        
        if dept:
            return DepartmentType(
                id=str(dept.id),
                name=dept.name,
                slug=dept.slug,
                description=dept.description or "",
                parent_id=str(dept.parent_id) if dept.parent_id else None,
                parent_name=dept.parent.name if dept.parent else None,
                manager_id=str(dept.manager_id) if dept.manager_id else None,
                manager_name=dept.manager.name if dept.manager else None,
                employee_count=dept.employees.count(),
                created_at=dept.created_at.isoformat(),
                updated_at=dept.updated_at.isoformat(),
            )
        
        return None


@strawberry.type
class DepartmentDistribution:
    """Department distribution in stats."""
    department_name: str
    count: int


@strawberry.type
class EmployeeStatsType:
    """Employee statistics for dashboard."""
    total_employees: int
    active_employees: int
    inactive_employees: int
    on_leave_employees: int
    terminated_employees: int
    department_distribution: List[DepartmentDistribution]