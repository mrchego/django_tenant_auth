from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from django_tenants_auth.rbac.services import RBACService
from django_tenants_auth.tenants.models import Tenant


class Command(BaseCommand):
    help = "Seed default roles for all existing tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Seed roles for a specific tenant slug',
        )

    def handle(self, *args, **options):
        tenant_slug = options.get('tenant')
        
        if tenant_slug:
            tenants = Tenant.objects.filter(slug=tenant_slug)
            if not tenants.exists():
                self.stdout.write(
                    self.style.ERROR(f"Tenant with slug '{tenant_slug}' not found")
                )
                return
        else:
            tenants = Tenant.objects.all()
        
        for tenant in tenants:
            self.stdout.write(f"Seeding roles for tenant: {tenant.name} ({tenant.schema_name})")
            
            try:
                with schema_context(tenant.schema_name):
                    roles = RBACService.seed_default_roles(tenant)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created/Updated roles for '{tenant.name}': "
                            f"{', '.join(roles.keys())}"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error seeding roles for '{tenant.name}': {str(e)}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS("Role seeding completed successfully")
        )