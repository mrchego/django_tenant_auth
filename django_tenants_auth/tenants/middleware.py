# django_tenants_auth/tenants/middleware.py
from django_tenants.utils import get_tenant_model
from django.contrib.auth.models import AnonymousUser


class TenantSlugHeaderMiddleware:
    """
    Allows selecting the active tenant via an 'X-Tenant-Slug' header.

    If the header is present and the user is authenticated,
    the tenant will be set to the one matching the slug,
    provided the user is a member of that tenant.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_slug = request.headers.get("X-Tenant-Slug")

        if tenant_slug and request.user.is_authenticated:
            Tenant = get_tenant_model()
            try:
                tenant = request.user.tenants.get(slug=tenant_slug)
                request.tenant = tenant
            except Tenant.DoesNotExist:
                # Tenant not found or user not a member – ignore
                pass

        return self.get_response(request)