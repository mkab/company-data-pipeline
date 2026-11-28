class UnexpectedPayloadError(Exception):
    """A successful response whose body is not the dataset's envelope."""
