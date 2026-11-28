from pydantic import BaseModel

from pipeline.cik import PaddedCik


class CompanyResponse(BaseModel):
    cik: PaddedCik
