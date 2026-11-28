class CompanyNotFoundError(Exception):
    """No curated company has this CIK."""

    def __init__(self, cik: int) -> None:
        super().__init__(cik)
        self.cik = cik
