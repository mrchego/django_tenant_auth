import strawberry
from strawberry_django import DjangoModelType
from django_tenants_auth.authentication.graphql.mutations import AuthMutation
from django_tenants_auth.authentication.graphql.queries import AuthQuery
from django_tenants_auth.rbac.graphql.mutations import RBACMutation
from django_tenants_auth.rbac.graphql.queries import RBACQuery
from django_tenants_auth.employees.graphql.mutations import EmployeeMutation
from django_tenants_auth.employees.graphql.queries import EmployeeQuery


@strawberry.type
class Query(AuthQuery, RBACQuery, EmployeeQuery):
    """Root query combining all domain queries."""
    
    @strawberry.field
    def hello(self) -> str:
        return "Hello from multi-tenant SaaS!"


@strawberry.type
class Mutation(AuthMutation, RBACMutation, EmployeeMutation):
    """Root mutation combining all domain mutations."""
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)