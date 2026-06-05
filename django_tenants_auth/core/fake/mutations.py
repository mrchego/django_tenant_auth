import strawberry

from .types import Developer, developers


@strawberry.type
class Mutation:

    @strawberry.mutation
    def activate_super_developer_mode(
        self,
        name: str,
    ) -> Developer:

        developer = Developer(
            name=name,
            level="10x Code Ninja 🥷",
            coffee_cups=999,
        )

        developers.append(developer)

        return developer