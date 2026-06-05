import strawberry
from typing import List

from .types import Developer, developers
from .mutations import Mutation


@strawberry.type
class Query:

    @strawberry.field
    def developers(self) -> List[Developer]:
        return developers


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)