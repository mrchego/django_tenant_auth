import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django_tenants_auth.tenants.models import User


class JWTAuthenticationMiddleware:
    """
    Authenticate users from JWT Bearer token WITHOUT breaking session auth.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If user is already authenticated (e.g., via session), do nothing
        if not request.user.is_authenticated:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=["HS256"],
                    )
                    if payload.get("type") == "access":
                        user = User.objects.get(id=payload["user_id"])
                        if user.is_active:
                            request.user = user
                except (
                    jwt.ExpiredSignatureError,
                    jwt.InvalidTokenError,
                    User.DoesNotExist,
                ):
                    pass  # keep AnonymousUser

        response = self.get_response(request)
        return response