"""
CSV formula injection protection (OWASP-documented: a cell value starting
with `=`, `+`, `-`, `@`, tab, or carriage return is interpreted as a
formula by Excel/Google Sheets when the file is opened, not as literal
text). Anything exported as CSV that ever echoes user-controlled text
(dataset text, misclassified sample text) needs this — a user could
otherwise craft input that runs a formula (including calling out to
external URLs via a webservice formula) on whoever opens the export.

The API itself is unaffected (JSON responses are never formula-interpreted
by anything); this only matters for the CSV export endpoints.
"""

_FORMULA_TRIGGER_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: object) -> object:
    """Prefixes a leading single quote onto any string starting with a
    formula-trigger character, which Excel/Sheets render as literal text
    instead of evaluating. Non-strings pass through unchanged."""
    if isinstance(value, str) and value.startswith(_FORMULA_TRIGGER_PREFIXES):
        return "'" + value
    return value


def sanitize_csv_row(row: dict) -> dict:
    return {key: sanitize_csv_cell(value) for key, value in row.items()}
