class SessionScopeError(Exception):
    """Raised inside a `session_scope` block to check that it rolls back."""
