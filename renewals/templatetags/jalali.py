from django import template

from renewals.dates import format_jalali

register = template.Library()


@register.filter(name="jalali")
def jalali_filter(value, mode="date"):
    return format_jalali(value, with_time=mode == "datetime")
