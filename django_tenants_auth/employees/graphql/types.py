import strawberry
from typing import List, Optional
from datetime import date, datetime


@strawberry.type
class DepartmentType:
    """GraphQL type for Department."""
    id: strawberry.ID
    name: str
    slug: str
    description: str
    parent_id: Optional[strawberry.ID] = None
    parent_name: Optional[str] = None
    manager_id: Optional[strawberry.ID] = None
    manager_name: Optional[str] = None
    employee_count: int = 0
    created_at: str
    updated_at: str


@strawberry.input
class DepartmentInput:
    """Input type for creating/updating departments."""
    name: str
    description: Optional[str] = ""
    parent_id: Optional[strawberry.ID] = None
    manager_id: Optional[strawberry.ID] = None


@strawberry.input
class DepartmentUpdateInput:
    """Input type for updating departments."""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[strawberry.ID] = None
    manager_id: Optional[strawberry.ID] = None


@strawberry.type
class EmployeeType:
    """GraphQL type for Employee."""
    id: strawberry.ID
    name: str
    emp_id: str
    slug: str
    
    # Department & Designation
    department: Optional[DepartmentType] = None
    designation: str
    
    # Compensation
    salary: Optional[float] = None
    commission: Optional[float] = None
    
    # Contact
    mobile_number: str
    
    # Personal
    birth_date: Optional[str] = None
    gender: str
    blood_group: str
    religion: str
    
    # Employment
    appointment_date: Optional[str] = None
    joining_date: Optional[str] = None
    
    # Status
    address: str
    image_path: str
    status: str
    
    # User association
    user_id: Optional[strawberry.ID] = None
    user_email: Optional[str] = None
    has_login: bool = False
    
    # Metadata
    created_by_id: Optional[strawberry.ID] = None
    created_at: str
    updated_at: str


@strawberry.type
class EmployeeListType:
    """Paginated employee list."""
    employees: List[EmployeeType]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@strawberry.input
class EmployeeCreateInput:
    """Input type for creating employees."""
    # Required fields
    name: str
    emp_id: str
    
    # Optional fields
    department_id: Optional[strawberry.ID] = None
    designation: Optional[str] = ""
    salary: Optional[float] = None
    commission: Optional[float] = None
    mobile_number: Optional[str] = ""
    birth_date: Optional[str] = None
    gender: Optional[str] = "male"
    blood_group: Optional[str] = ""
    religion: Optional[str] = ""
    appointment_date: Optional[str] = None
    joining_date: Optional[str] = None
    address: Optional[str] = ""
    image_path: Optional[str] = ""
    status: Optional[str] = "active"
    
    # Auth fields (optional)
    allow_login: Optional[bool] = False
    email: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[strawberry.ID] = None


@strawberry.input
class EmployeeUpdateInput:
    """Input type for updating employees."""
    name: Optional[str] = None
    department_id: Optional[strawberry.ID] = None
    designation: Optional[str] = None
    salary: Optional[float] = None
    commission: Optional[float] = None
    mobile_number: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    religion: Optional[str] = None
    appointment_date: Optional[str] = None
    joining_date: Optional[str] = None
    address: Optional[str] = None
    image_path: Optional[str] = None
    status: Optional[str] = None


@strawberry.input
class EmployeeLoginUpdateInput:
    """Input type for updating employee login status."""
    employee_id: strawberry.ID
    allow_login: bool
    email: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[strawberry.ID] = None


@strawberry.type
class CreateEmployeeResponse:
    """Response type for employee creation."""
    success: bool
    employee: Optional[EmployeeType] = None
    user_id: Optional[strawberry.ID] = None
    user_email: Optional[str] = None
    message: str = ""


@strawberry.type
class UpdateEmployeeResponse:
    """Response type for employee updates."""
    success: bool
    employee: Optional[EmployeeType] = None
    message: str = ""


@strawberry.type
class DeleteEmployeeResponse:
    """Response type for employee deletion."""
    success: bool
    message: str = ""