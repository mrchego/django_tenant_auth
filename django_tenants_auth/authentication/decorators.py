from functools import wraps

from graphql import GraphQLError


def login_required(resolver):
    @wraps(resolver)
    def wrapper(*args, info, **kwargs):
        request = info.context.request

        if not request.user.is_authenticated:
            raise GraphQLError("Authentication required.")

        return resolver(*args, info, **kwargs)

    return wrapper