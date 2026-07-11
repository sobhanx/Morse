from re import match

from django.core.exceptions import ValidationError


def phone_validation(value):
    return bool(match(pattern=r"^09\d{9}$", string=value))


def phone_number_validator(value):
    if not phone_validation(value):
        raise ValidationError("شماره تلفن معتبر نمی‌باشد.")
