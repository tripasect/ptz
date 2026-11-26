import re

from django.core.exceptions import ValidationError

NATIONAL_ID_PATTERN = re.compile(r"^\d{10}$")


def validate_national_id(value: str) -> None:
    """Iranian national ID: 10 digits plus the standard check digit.

    Document eligibility is out of scope. This only rejects malformed identifiers
    so a typo does not become the key of a coverage snapshot.
    """
    if value is None or not NATIONAL_ID_PATTERN.match(str(value)):
        raise ValidationError("کد ملی باید دقیقاً ۱۰ رقم باشد.")
    if len(set(value)) == 1:
        raise ValidationError("کد ملی معتبر نیست.")
    total = sum(int(value[index]) * (10 - index) for index in range(9))
    remainder = total % 11
    expected = remainder if remainder < 2 else 11 - remainder
    if int(value[9]) != expected:
        raise ValidationError("کد ملی معتبر نیست.")
