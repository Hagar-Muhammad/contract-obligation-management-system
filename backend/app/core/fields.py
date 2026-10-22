"""Reusable request-field cleaners (docs/api-standards.md §7)."""

from pydantic import BeforeValidator


def _strip_blank(value: object) -> object:
    """Trim text; an empty or whitespace-only value means "not given"."""
    if isinstance(value, str):
        return value.strip() or None
    return value


def _identifier(value: object) -> object:
    """Official numbers (national ID, registration no.): no spaces, upper case, so duplicates are found."""
    if isinstance(value, str):
        return "".join(value.split()).upper() or None
    return value


CleanText = BeforeValidator(_strip_blank)
Identifier = BeforeValidator(_identifier)
