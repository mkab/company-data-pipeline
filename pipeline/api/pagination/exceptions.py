class InvalidCursorError(ValueError):
    """A cursor that is not base64 of a valid sort key, such as one edited by hand."""
