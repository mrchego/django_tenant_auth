from typing import Optional, Dict, Any, List
from django.db import transaction
from django.db.models import Q
from django_tenants.utils import schema_context
from django.utils.text import slugify

from django_tenants_auth.employees.models import Employee, Department
from django_tenants_auth.tenants.models import User, Tenant
from django_tenants_auth.rbac.services import RBACService
from django_tenants_auth.employees.graphql.types import DepartmentType, EmployeeType


class EmployeeService:
    """Service layer for employee management."""
    
    @staticmethod
    def _map_employee_to_type(employee: Employee) -> EmployeeType:
        """Map Employee model to EmployeeType GraphQL type."""
        return EmployeeType(
            id=str(employee.id),
            name=employee.name,
            emp_id=employee.emp_id,
            slug=employee.slug,
            department=DepartmentType(
                id=str(employee.department.id),
                name=employee.department.name,
                slug=employee.department.slug,
                description=employee.department.description or "",
                parent_id=str(employee.department.parent_id) if employee.department.parent_id else None,
                parent_name=employee.department.parent.name if employee.department.parent else None,
                manager_id=str(employee.department.manager_id) if employee.department.manager_id else None,
                manager_name=employee.department.manager.name if employee.department.manager else None,
                employee_count=employee.department.employees.count(),
                created_at=employee.department.created_at.isoformat(),
                updated_at=employee.department.updated_at.isoformat(),
            ) if employee.department else None,
            designation=employee.designation or "",
            salary=float(employee.salary) if employee.salary else None,
            commission=float(employee.commission) if employee.commission else None,
            mobile_number=employee.mobile_number or "",
            birth_date=employee.birth_date.isoformat() if employee.birth_date else None,
            gender=employee.gender,
            blood_group=employee.blood_group or "",
            religion=employee.religion or "",
            appointment_date=employee.appointment_date.isoformat() if employee.appointment_date else None,
            joining_date=employee.joining_date.isoformat() if employee.joining_date else None,
            address=employee.address or "",
            image_path=employee.image_path or "",
            status=employee.status,
            user_id=str(employee.user_id) if employee.user_id else None,
            user_email=employee.user.email if employee.user else None,
            has_login=employee.user is not None and employee.user.is_active,
            created_by_id=str(employee.created_by_id) if employee.created_by_id else None,
            created_at=employee.created_at.isoformat(),
            updated_at=employee.updated_at.isoformat(),
        )
    
    @staticmethod
    def get_employee_by_id(employee_id: str) -> Optional[Employee]:
        """Get employee by ID with related fields."""
        try:
            return Employee.objects.select_related(
                'department', 'user', 'created_by'
            ).get(id=employee_id)
        except Employee.DoesNotExist:
            return None
    
    @staticmethod
    def create_employee(
        *,
        tenant: Tenant,
        created_by: User,
        # Employee fields
        name: str,
        emp_id: str,
        department_id: Optional[str] = None,
        designation: str = "",
        salary: Optional[float] = None,
        commission: Optional[float] = None,
        mobile_number: str = "",
        birth_date: Optional[str] = None,
        gender: str = "male",
        blood_group: str = "",
        religion: str = "",
        appointment_date: Optional[str] = None,
        joining_date: Optional[str] = None,
        address: str = "",
        image_path: str = "",
        status: str = "active",
        # Auth fields (optional)
        allow_login: bool = False,
        email: Optional[str] = None,
        password: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create employee with optional user account.
        """
        with schema_context(tenant.schema_name):
            with transaction.atomic():
                # Create user if login is allowed
                user = None
                if allow_login and email and password:
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        is_verified=True,
                    )
                    # Add user to tenant
                    tenant.add_user(user)
                    
                    # Assign role if specified
                    if role_id:
                        from django_tenants_auth.rbac.models import Role
                        role = Role.objects.get(id=role_id)
                        RBACService.assign_role_to_user(
                            user=user,
                            role=role,
                            assigned_by=created_by,
                        )
                
                # Get department if specified
                department = None
                if department_id:
                    department = Department.objects.get(id=department_id)
                
                # Create employee
                employee = Employee.objects.create(
                    name=name,
                    emp_id=emp_id,
                    slug=slugify(f"{name}-{emp_id}"),
                    department=department,
                    designation=designation,
                    salary=salary,
                    commission=commission,
                    mobile_number=mobile_number,
                    birth_date=birth_date,
                    gender=gender,
                    blood_group=blood_group,
                    religion=religion,
                    appointment_date=appointment_date,
                    joining_date=joining_date,
                    address=address,
                    image_path=image_path,
                    status=status,
                    user=user,
                    created_by=created_by,
                )
                
                return {
                    "employee": {
                        "id": str(employee.id),
                        "name": employee.name,
                        "emp_id": employee.emp_id,
                        "slug": employee.slug,
                    },
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                    } if user else None,
                }
    
    @staticmethod
    def update_employee(
        *,
        tenant: Tenant,
        employee_id: str,
        **fields,
    ) -> Dict[str, Any]:
        """Update employee fields."""
        with schema_context(tenant.schema_name):
            employee = Employee.objects.get(id=employee_id)
            
            # Handle department separately
            department_id = fields.pop('department_id', None)
            if department_id:
                employee.department = Department.objects.get(id=department_id)
            
            # Update other fields
            for field, value in fields.items():
                if hasattr(employee, field) and value is not None:
                    setattr(employee, field, value)
            
            employee.save()
            
            return {
                "employee": EmployeeService._map_employee_to_type(employee)
            }
    
    @staticmethod
    def update_employee_login(
        *,
        tenant: Tenant,
        employee_id: str,
        allow_login: bool,
        email: Optional[str] = None,
        password: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update employee login status.
        """
        with schema_context(tenant.schema_name):
            employee = Employee.objects.get(id=employee_id)
            
            if allow_login and not employee.user:
                # Create user account
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    is_verified=True,
                )
                tenant.add_user(user)
                employee.user = user
                
                if role_id:
                    from django_tenants_auth.rbac.models import Role
                    role = Role.objects.get(id=role_id)
                    RBACService.assign_role_to_user(
                        user=user,
                        role=role,
                    )
                
            elif not allow_login and employee.user:
                # Deactivate user but keep employee record
                employee.user.is_active = False
                employee.user.save()
                employee.user = None
            
            employee.save()
            
            return {
                "employee": {
                    "id": str(employee.id),
                    "has_login": employee.user is not None and employee.user.is_active,
                }
            }
    
    @staticmethod
    def delete_employee(
        *,
        tenant: Tenant,
        employee_id: str,
    ) -> bool:
        """Delete an employee."""
        with schema_context(tenant.schema_name):
            employee = Employee.objects.get(id=employee_id)
            
            # Deactivate associated user if exists
            if employee.user:
                employee.user.is_active = False
                employee.user.save()
            
            employee.delete()
            return True
    
    @staticmethod
    def bulk_update_status(
        *,
        tenant: Tenant,
        employee_ids: List[str],
        status: str,
    ) -> int:
        """Bulk update employee status."""
        with schema_context(tenant.schema_name):
            count = Employee.objects.filter(
                id__in=employee_ids
            ).update(status=status)
            return count
    
    @staticmethod
    def create_department(
        *,
        tenant: Tenant,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        manager_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new department."""
        with schema_context(tenant.schema_name):
            parent = None
            if parent_id:
                parent = Department.objects.get(id=parent_id)
            
            manager = None
            if manager_id:
                manager = Employee.objects.get(id=manager_id)
            
            department = Department.objects.create(
                name=name,
                slug=slugify(name),
                description=description,
                parent=parent,
                manager=manager,
            )
            
            return {
                "id": str(department.id),
                "name": department.name,
                "slug": department.slug,
            }
    
    @staticmethod
    def update_department(
        *,
        tenant: Tenant,
        department_id: str,
        **fields,
    ) -> Dict[str, Any]:
        """Update a department."""
        with schema_context(tenant.schema_name):
            department = Department.objects.get(id=department_id)
            
            # Handle foreign keys separately
            parent_id = fields.pop('parent_id', None)
            if parent_id:
                department.parent = Department.objects.get(id=parent_id)
            
            manager_id = fields.pop('manager_id', None)
            if manager_id:
                department.manager = Employee.objects.get(id=manager_id)
            
            # Update other fields
            for field, value in fields.items():
                if hasattr(department, field) and value is not None:
                    setattr(department, field, value)
            
            department.save()
            
            return {"success": True}
    
    @staticmethod
    def delete_department(
        *,
        tenant: Tenant,
        department_id: str,
    ) -> bool:
        """Delete a department."""
        with schema_context(tenant.schema_name):
            department = Department.objects.get(id=department_id)
            
            # Remove department from employees
            Employee.objects.filter(department=department).update(department=None)
            
            # Handle child departments
            Department.objects.filter(parent=department).update(parent=department.parent)
            
            department.delete()
            return True