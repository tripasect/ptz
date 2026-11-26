"""Jalali dates for anything a person sees or types.

Values stay Gregorian in the database. Conversion happens at the form and template edge.
"""
from datetime import date, datetime

import jdatetime
from django.utils import timezone

_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def format_jalali(value, with_time=False):
    if not value:
        return ""
    if not isinstance(value, (date, datetime)):
        return value
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        converted = jdatetime.datetime.fromgregorian(datetime=value.replace(tzinfo=None))
        if with_time:
            return (
                f"{converted.year:04d}/{converted.month:02d}/{converted.day:02d} "
                f"{converted.hour:02d}:{converted.minute:02d}"
            )
        return f"{converted.year:04d}/{converted.month:02d}/{converted.day:02d}"
    converted = jdatetime.date.fromgregorian(date=value)
    return f"{converted.year:04d}/{converted.month:02d}/{converted.day:02d}"


def parse_jalali(value):
    """Return a Gregorian date from a Jalali string such as 1370/01/01."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().translate(_DIGIT_TRANSLATION).replace("-", "/")
    parts = text.split("/")
    if len(parts) != 3:
        raise ValueError("incomplete")
    year, month, day = (int(part) for part in parts)
    return jdatetime.date(year, month, day).togregorian()
