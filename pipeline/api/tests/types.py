from pydantic import BaseModel

from pipeline.api.cik import PaddedCik


class CompanyResponse(BaseModel):
    cik: PaddedCik
