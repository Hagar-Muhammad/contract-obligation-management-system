# The Arabic letters below are intentional, not look-alikes of Latin ones.
# ruff: noqa: RUF001, RUF002
"""Text search that works on Arabic as well as English (FR-SEARCH-01, decision D-16).

Both the stored text (in SQL, `search_normalize()`, created by migration 0008) and the typed query (here, in Python)
go through the same normalisation, so that:

- case is ignored;
- Arabic diacritics (tashkeel) and the tatweel are ignored: "مُحَمَّد" finds "محمد";
- alef forms are one letter (أ إ آ ٱ → ا), ta marbuta matches ha (ة → ه), alef maqsura matches ya (ى → ي):
  "احمد" finds "أحمد", "مؤسسه" finds "مؤسسة".

The typed text is matched literally: % and _ are not wildcards.
"""

import re
from typing import Any

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.orm import QueryableAttribute

# Keep in step with search_normalize() in alembic/versions/*_0008_search.py (tests check both agree).
_DIACRITICS = re.compile("[\u064b-\u0652\u0670\u0640]")
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})


def normalize(text: str) -> str:
    return _DIACRITICS.sub("", text).translate(_LETTERS).lower()


def _like_pattern(query: str) -> str:
    escaped = normalize(query.strip()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def text_matches(query: str, *columns: QueryableAttribute[Any] | ColumnElement[Any]) -> ColumnElement[bool]:
    """True when any of the columns contains the query, after normalising both sides."""
    pattern = _like_pattern(query)
    return or_(*(func.search_normalize(column).like(pattern, escape="\\") for column in columns))
