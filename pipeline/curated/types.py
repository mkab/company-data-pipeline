from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ColumnShape:
    """A column as PostgreSQL's `information_schema.columns` describes it, such as `bigint` for its type."""

    table: str
    column: str
    data_type: str
    is_nullable: bool

    def describe(self) -> str:
        nullability = "null" if self.is_nullable else "not null"
        return f"{self.table}.{self.column} {self.data_type} {nullability}"
