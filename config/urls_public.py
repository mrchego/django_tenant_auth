from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView

from config.schema import schema

urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="pages/home.html"
        ),
        name="home",
    ),
    path(settings.ADMIN_URL, admin.site.urls),

    path(
        "graphql/",
        csrf_exempt(
            GraphQLView.as_view(schema=schema)
        ),
        name="public-graphql",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]