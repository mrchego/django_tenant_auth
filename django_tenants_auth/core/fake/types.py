import strawberry


@strawberry.type
class Developer:
    name: str
    level: str
    coffee_cups: int


developers = [
    Developer(
        name="MrChego",
        level="Junior Wizard",
        coffee_cups=3,
    )
]