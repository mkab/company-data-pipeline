from pydantic import BaseModel

from pipeline.api.problems.constants import BLANK_PROBLEM_TYPE


class ProblemDetail(BaseModel):
    type: str = BLANK_PROBLEM_TYPE
    title: str
    status: int
    detail: str


class InvalidParameter(BaseModel):
    """One parameter a validation error names: where it is (such as `["query", "limit"]`), and why."""

    location: list[str | int]
    message: str


class ValidationProblem(ProblemDetail):
    """A 422, with the `errors` extension member listing each invalid parameter."""

    errors: list[InvalidParameter]
