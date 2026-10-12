"""
SQLite quirk workaround.

Unlike Postgres, SQLite has no native datetime type — SQLAlchemy's
`DateTime(timezone=True)` stores an ISO string and does not reliably
reattach `tzinfo` when the row is loaded back on a *later* request/session.
A value just created in Python is timezone-aware; the same value read back
from the database afterward is often naive. Comparing an aware and a naive
datetime raises `TypeError: can't compare offset-naive and offset-aware
datetimes` — this bit the refresh-token expiry and account-lockout checks
in backend/services/auth_service.py the moment those values were re-read
from the database in a new request.

Anything loaded from the database and compared against
`datetime.now(timezone.utc)` should go through `ensure_aware_utc` first.
The database only ever stores UTC values (see the `default=` callables on
the affected columns), so treating a naive value as UTC is correct here —
this is not a general-purpose timezone converter.
"""

from datetime import datetime, timezone


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
