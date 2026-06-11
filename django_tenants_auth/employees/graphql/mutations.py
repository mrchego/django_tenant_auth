import strawberry
from typing import List, Optional
from strawberry.types import Info
from django_tenants_auth.authentication.decorators import login_required

from django_tenants_auth.employees.services import EmployeeService
from django_tenants_auth.employees.graphql.types import (
    EmployeeCreateInput,
    EmployeeType,
    EmployeeUpdateInput,
    EmployeeLoginUpdateInput,
    CreateEmployeeResponse,
    UpdateEmployeeResponse,
    DeleteEmployeeResponse,
    DepartmentInput,
    DepartmentUpdateInput,
    DepartmentType,
)


@strawberry.type
class EmployeeMutation:
    
    @strawberry.mutation
    @login_required
    def create_employee(
        self,
        info: Info,
        input: EmployeeCreateInput,
    ) -> CreateEmployeeResponse:
        """
        Create a new employee with optional user account.
        
        If allow_login is True, an auth user account will be created
        and associated with the employee record.
        """
        try:
            user = info.context.request.user
            tenant = info.context.request.tenant
            
            result = EmployeeService.create_employee(
                tenant=tenant,
                created_by=user,
                name=input.name,
                emp_id=input.emp_id,
                department_id=str(input.department_id) if input.department_id else None,
                designation=input.designation or "",
                salary=input.salary,
                commission=input.commission,
                mobile_number=input.mobile_number or "",
                birth_date=input.birth_date,
                gender=input.gender or "male",
                blood_group=input.blood_group or "",
                religion=input.religion or "",
                appointment_date=input.appointment_date,
                joining_date=input.joining_date,
                address=input.address or "",
                image_path=input.image_path or "",
                status=input.status or "active",
                allow_login=input.allow_login or False,
                email=input.email,
                password=input.password,
                role_id=str(input.role_id) if input.role_id else None,
            )
            
            employee = EmployeeService.get_employee_by_id(result["employee"]["id"])
            
            return CreateEmployeeResponse(
                success=True,
                employee=EmployeeService._map_employee_to_type(employee) if employee else None,
                user_id=result["user"]["id"] if result.get("user") else None,
                user_email=result["user"]["email"] if result.get("user") else None,
                message="Employee created successfully"
            )
        except Exception as e:
            return CreateEmployeeResponse(
                success=False,
                message=f"Failed to create employee: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def update_employee(
        self,
        info: Info,
        input: EmployeeUpdateInput,
    ) -> UpdateEmployeeResponse:
        try:
            tenant = info.context.request.tenant
            updated_by = info.context.request.user

            # Build dict of only provided (non-None) fields
            data = {
                field: value
                for field, value in input.__dict__.items()
                if value is not None
            }

            employee_id = data.pop("employee_id")

            result = EmployeeService.update_employee(
                tenant=tenant,
                employee_id=str(employee_id),
                updated_by=updated_by,
                **data
            )

            # Use the service's built-in mapper to create the full EmployeeType
            employee_type = EmployeeService._map_employee_to_type(result["employee"])

            return UpdateEmployeeResponse(
                success=True,
                employee=employee_type,
                message="Employee updated successfully"
            )

        except Exception as e:
            return UpdateEmployeeResponse(
                success=False,
                employee=None,
                message=f"Failed to update employee: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def update_employee_login(
        self,
        info: Info,
        input: EmployeeLoginUpdateInput,
    ) -> UpdateEmployeeResponse:
        """
        Update employee login status.
        
        Can enable login (create user account) or disable login 
        (deactivate user account) for an employee.
        """
        try:
            tenant = info.context.request.tenant
            
            result = EmployeeService.update_employee_login(
                tenant=tenant,
                employee_id=str(input.employee_id),
                allow_login=input.allow_login,
                email=input.email,
                password=input.password,
                role_id=str(input.role_id) if input.role_id else None,
            )
            
            employee = EmployeeService.get_employee_by_id(result["employee"]["id"])
            
            return UpdateEmployeeResponse(
                success=True,
                employee=EmployeeService._map_employee_to_type(employee) if employee else None,
                message="Employee login status updated successfully"
            )
        except Exception as e:
            return UpdateEmployeeResponse(
                success=False,
                message=f"Failed to update employee login: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def delete_employee(
        self,
        info: Info,
        employee_id: strawberry.ID,
    ) -> DeleteEmployeeResponse:
        """
        Delete an employee.

        Removes employee from tenant schema,
        cleans RBAC,
        and safely deactivates unused user accounts.
        """

        try:

            tenant = info.context.request.tenant
            deleted_by = info.context.request.user


            EmployeeService.delete_employee(
                tenant=tenant,
                employee_id=str(employee_id),
                deleted_by=deleted_by,
            )


            return DeleteEmployeeResponse(
                success=True,
                message="Employee deleted successfully"
            )


        except Exception as e:

            return DeleteEmployeeResponse(
                success=False,
                message=f"Failed to delete employee: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def bulk_update_employee_status(
        self,
        info: Info,
        employee_ids: List[strawberry.ID],
        status: str,
    ) -> UpdateEmployeeResponse:
        """
        Bulk update employee status.
        
        Status can be: active, inactive, on_leave, terminated
        """
        try:
            tenant = info.context.request.tenant
            
            count = EmployeeService.bulk_update_status(
                tenant=tenant,
                employee_ids=[str(eid) for eid in employee_ids],
                status=status,
            )
            
            return UpdateEmployeeResponse(
                success=True,
                message=f"Successfully updated {count} employee(s) to {status}"
            )
        except Exception as e:
            return UpdateEmployeeResponse(
                success=False,
                message=f"Failed to update employees: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def create_department(
        self,
        info: Info,
        input: DepartmentInput,
    ) -> UpdateEmployeeResponse:
        """
        Create a new department.
        """
        try:
            tenant = info.context.request.tenant
            
            result = EmployeeService.create_department(
                tenant=tenant,
                name=input.name,
                description=input.description or "",
                parent_id=str(input.parent_id) if input.parent_id else None,
                manager_id=str(input.manager_id) if input.manager_id else None,
            )
            
            return UpdateEmployeeResponse(
                success=True,
                message=f"Department '{result['name']}' created successfully"
            )
        except Exception as e:
            return UpdateEmployeeResponse(
                success=False,
                message=f"Failed to create department: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def update_department(
        self,
        info: Info,
        department_id: strawberry.ID,
        input: DepartmentUpdateInput,
    ) -> UpdateEmployeeResponse:
        """
        Update an existing department.
        """
        try:
            tenant = info.context.request.tenant
            
            result = EmployeeService.update_department(
                tenant=tenant,
                department_id=str(department_id),
                **{k: v for k, v in input.__dict__.items() if v is not None}
            )
            
            return UpdateEmployeeResponse(
                success=True,
                message="Department updated successfully"
            )
        except Exception as e:
            return UpdateEmployeeResponse(
                success=False,
                message=f"Failed to update department: {str(e)}"
            )
    
    @strawberry.mutation
    @login_required
    def delete_department(
        self,
        info: Info,
        department_id: strawberry.ID,
    ) -> DeleteEmployeeResponse:
        """
        Delete a department.
        
        Employees in this department will have their department set to None.
        """
        try:
            tenant = info.context.request.tenant
            
            EmployeeService.delete_department(
                tenant=tenant,
                department_id=str(department_id),
            )
            
            return DeleteEmployeeResponse(
                success=True,
                message="Department deleted successfully"
            )
        except Exception as e:
            return DeleteEmployeeResponse(
                success=False,
                message=f"Failed to delete department: {str(e)}"
            )