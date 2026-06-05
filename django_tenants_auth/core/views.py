from django.http import JsonResponse

def tenant_debug(request):
    return JsonResponse({
        "tenant": str(request.tenant),
        "schema": request.tenant.schema_name,
        "domain": request.get_host(),
    })
    