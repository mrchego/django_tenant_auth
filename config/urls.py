from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView

from config.schema import schema

urlpatterns = [
    path("", include("config.urls_public")),

    path(
        "graphql/",
        csrf_exempt(GraphQLView.as_view(schema=schema)),
        name="graphql",
    ),

    path(settings.ADMIN_URL, admin.site.urls),
    
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
