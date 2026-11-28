"""Keyset pagination: a page holds up to `limit` rows, and `next_cursor` resumes after its last one.

A cursor is the last row's sort key, as base64 of its JSON, opaque to the client.
Each list declares its sort key as a pydantic model,
takes the `page_request` dependency (`dependencies.py`),
fetches `limit + 1` rows after the key,
then returns `build_page` (`pages.py`), which knows from the extra row whether another page follows.
"""
