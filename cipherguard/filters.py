from datetime import datetime

from flask import current_app

DISPLAY_DATE = "%d %b %Y"
DISPLAY_TIME = "%H:%M"


def register(app):
    app.add_template_filter(money, "money")
    app.add_template_filter(moment, "moment")
    app.add_template_filter(day, "day")
    app.add_template_filter(clock, "clock")
    app.add_template_filter(initials, "initials")
    app.add_template_filter(thousands, "thousands")


def money(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return "{}{:,.2f}".format(current_app.config["CURRENCY_SYMBOL"], amount)


def moment(value):
    parsed = _parse(value)
    if parsed is None:
        return value or ""
    return parsed.strftime(DISPLAY_DATE + ", " + DISPLAY_TIME)


def day(value):
    parsed = _parse(value)
    if parsed is None:
        return value or ""
    return parsed.strftime(DISPLAY_DATE)


def clock(value):
    parsed = _parse(value)
    if parsed is None:
        return value or ""
    return parsed.strftime(DISPLAY_TIME)


def initials(value):
    text = (value or "").strip()
    if not text:
        return "?"
    parts = text.split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def thousands(value):
    try:
        return "{:,}".format(int(value))
    except (TypeError, ValueError):
        return value


def _parse(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
