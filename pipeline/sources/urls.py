from urllib.parse import urlsplit, urlunsplit


def url_without_query(url: str) -> str:
    """Return `url` without its query string or fragment."""
    return urlunsplit(urlsplit(url)._replace(query="", fragment=""))
