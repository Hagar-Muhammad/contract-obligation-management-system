"""Recurring obligations (FR-OBL-06, BR-08): RFC 5545 RRULE text, counted from the series' first due date."""

from datetime import date, datetime, time

from dateutil.rrule import rrule, rrulestr

# Deadlines repeat weekly at most often; daily or hourly rules would flood the obligation list.
_ALLOWED_FREQUENCIES = {"WEEKLY", "MONTHLY", "YEARLY"}
MAX_RULE_LENGTH = 500


class InvalidRecurrenceError(ValueError):
    pass


def _parse(rule: str, first_due: date) -> rrule:
    text = rule.strip().upper().removeprefix("RRULE:")
    if (
        not text
        or len(text) > MAX_RULE_LENGTH
        or any(part in text for part in ("DTSTART", "\n", "\r", "EXDATE"))
    ):
        raise InvalidRecurrenceError("Use a single RRULE, e.g. FREQ=MONTHLY;INTERVAL=3.")
    try:
        parsed = rrulestr(text, dtstart=datetime.combine(first_due, time()))
    except (ValueError, TypeError) as exc:
        raise InvalidRecurrenceError("This repeat rule is not valid.") from exc
    parts = dict(part.split("=", 1) for part in text.split(";") if "=" in part)
    if not isinstance(parsed, rrule) or parts.get("FREQ") not in _ALLOWED_FREQUENCIES:
        raise InvalidRecurrenceError("An obligation can repeat weekly, monthly or yearly.")
    return parsed


def normalise(rule: str, first_due: date) -> str:
    """Validate a rule (BR-08) and return it in canonical form."""
    parsed = _parse(rule, first_due)
    # Only look one step ahead: most rules never end, so counting occurrences would never finish.
    if parsed.after(datetime.combine(first_due, time()), inc=False) is None:
        raise InvalidRecurrenceError("This rule never repeats; leave it empty for a one-time obligation.")
    return rule.strip().upper().removeprefix("RRULE:")


def next_due(rule: str, first_due: date, after: date) -> date | None:
    """The first occurrence strictly after `after`, or None when the series has ended (COUNT/UNTIL)."""
    following = _parse(rule, first_due).after(datetime.combine(after, time()), inc=False)
    return following.date() if following else None
