import json
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command

from psycopg import connect
from psycopg import sql

from tenant_users.tenants.tasks import provision_tenant
from tenant_users.tenants.utils import create_public_tenant

from django_tenants_auth.tenants.models import User


class Command(BaseCommand):
    help = "Recreates database and provisions demo tenants"

    root_user = None
    public_tenant = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tenants_file = (
            Path(settings.BASE_DIR)
            / "django_tenants_auth"
            / "tenants"
            / "data"
            / "tenants.json"
        )

        with open(tenants_file, "r") as f:
            self.tenants_data = json.load(f)

    def handle(self, *args, **options):
        # SAFETY CHECK
        if not settings.DEBUG:
            raise Exception(
                "populate_db cannot run outside DEBUG mode."
            )

        # Reset database
        self.drop_and_recreate_db()

        # Apply shared schema migrations
        call_command(
            "migrate_schemas",
            "--shared",
            "--noinput",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Shared schema migrated."
            )
        )

        # Create public tenant
        self.create_public_tenant()

        # Apply tenant schema migrations
        call_command(
            "migrate_schemas",
            "--tenant",
            "--noinput",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Tenant schemas migrated."
            )
        )

        # Create demo tenants
        self.create_private_tenants()

        self.stdout.write(
            self.style.SUCCESS(
                "Database successfully populated."
            )
        )

    def drop_and_recreate_db(self):
        db = settings.DATABASES["default"]

        db_name = db["NAME"]

        conn = connect(
            dbname="postgres",
            user=db["USER"],
            password=db["PASSWORD"],
            host=db["HOST"],
            port=db["PORT"],
        )

        conn.autocommit = True

        cur = conn.cursor()

        # Kill active connections
        cur.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s
            AND pid <> pg_backend_pid();
            """,
            [db_name],
        )

        # Drop DB
        cur.execute(
            sql.SQL(
                "DROP DATABASE IF EXISTS {}"
            ).format(
                sql.Identifier(db_name)
            )
        )

        # Recreate DB
        cur.execute(
            sql.SQL(
                "CREATE DATABASE {}"
            ).format(
                sql.Identifier(db_name)
            )
        )

        cur.close()
        conn.close()

    def create_public_tenant(self):
        self.stdout.write(
            "Creating public tenant..."
        )

        tenant_data = self.tenants_data[0]

        public_tenant, public_domain, root_user = create_public_tenant(
            domain_url=settings.BASE_DOMAIN,
            tenant_extra_data={
                "slug": tenant_data["subdomain"],
            },
            owner_email=tenant_data["owner"]["email"],
            is_superuser=True,
            is_staff=True,
            password=tenant_data["owner"]["password"],
            is_verified=True,
        )

        self.public_tenant = public_tenant
        self.root_user = root_user

        self.stdout.write(
            self.style.SUCCESS(
                f"Public tenant '{public_tenant.schema_name}' created."
            )
        )

    def create_private_tenants(self):
        tenants = self.tenants_data[1:]

        for tenant_data in tenants:
            self.stdout.write(
                f"Creating tenant '{tenant_data['schema_name']}'..."
            )

            # Create tenant owner
            tenant_owner = User.objects.create_user(
                email=tenant_data["owner"]["email"],
                password=tenant_data["owner"]["password"],
            )

            tenant_owner.is_verified = True
            tenant_owner.save()

            # Provision tenant
            tenant, domain = provision_tenant(
                tenant_name=tenant_data["name"],
                tenant_slug=tenant_data["subdomain"],
                schema_name=tenant_data["schema_name"],
                owner=tenant_owner,
                is_superuser=True,
                is_staff=True,
            )

            # Add root user to tenant
            tenant.add_user(
                self.root_user,
                is_superuser=True,
                is_staff=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Tenant '{tenant.schema_name}' created."
                )
            )