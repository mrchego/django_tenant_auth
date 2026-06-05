from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from tenant_users.tenants.utils import get_public_schema_name

from django_tenants_auth.rbac.services import PermissionSeeder
from django_tenants_auth.tenants.models import Tenant


class Command(BaseCommand):
    help = "Seed permissions and permission groups across all tenant schemas"

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Seed only a specific schema (default: all schemas)',
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema')
        
        if schema_name:
            # Seed a specific schema
            self.seed_schema(schema_name)
        else:
            # Seed all schemas
            public_schema = get_public_schema_name()
            
            # Seed public schema first
            self.stdout.write(f"Seeding public schema: {public_schema}")
            with schema_context(public_schema):
                result = PermissionSeeder.seed_permissions_and_groups()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Public schema seeded: {result}"
                    )
                )
            
            # Seed all tenant schemas
            tenants = Tenant.objects.exclude(schema_name=public_schema)
            for tenant in tenants:
                self.seed_schema(tenant.schema_name)
        
        self.stdout.write(
            self.style.SUCCESS("Permission seeding completed successfully")
        )
    
    def seed_schema(self, schema_name):
        """Seed permissions for a specific schema."""
        self.stdout.write(f"Seeding schema: {schema_name}")
        
        try:
            with schema_context(schema_name):
                result = PermissionSeeder.seed_permissions_and_groups()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Schema '{schema_name}' seeded: {result}"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error seeding schema '{schema_name}': {str(e)}"
                )
            )