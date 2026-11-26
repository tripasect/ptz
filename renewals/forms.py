from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from renewals.dates import format_jalali, parse_jalali
from renewals.models import Relationship
from renewals.validators import normalize_national_id, validate_national_id


class JalaliDateField(forms.DateField):
    widget = forms.TextInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={"placeholder": "1370/01/01", "inputmode": "numeric"}),
        )
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return parse_jalali(value)
        except (ValueError, TypeError, OverflowError):
            raise ValidationError("تاریخ را به صورت 1370/01/01 وارد کنید.") from None

    def prepare_value(self, value):
        if isinstance(value, (date, datetime)):
            return format_jalali(value)
        return value


class CoverageLineForm(forms.Form):
    first_name = forms.CharField(label="نام", max_length=100)
    last_name = forms.CharField(label="نام خانوادگی", max_length=100)
    national_id = forms.CharField(
        label="کد ملی",
        max_length=10,
        min_length=10,
        validators=[validate_national_id],
    )
    relationship = forms.ChoiceField(label="نسبت", choices=Relationship.choices)
    birth_date = JalaliDateField(label="تاریخ تولد")

    def __init__(self, *args, lock_self=False, allow_self=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_self = lock_self
        if lock_self:
            self.fields["relationship"].disabled = True
            self.fields["relationship"].initial = Relationship.SELF
        elif not allow_self:
            self.fields["relationship"].choices = [
                choice for choice in Relationship.choices if choice[0] != Relationship.SELF
            ]
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " input").strip()
        self.fields["national_id"].widget.attrs["dir"] = "ltr"
        birth_date = self.fields["birth_date"]
        birth_date.widget.attrs["dir"] = "ltr"
        birth_date.widget.attrs["autocomplete"] = "off"
        birth_date.widget.attrs["class"] = (
            birth_date.widget.attrs.get("class", "") + " jalali-picker"
        ).strip()

    def clean_national_id(self):
        return normalize_national_id(self.cleaned_data["national_id"])

    def clean_birth_date(self):
        value = self.cleaned_data["birth_date"]
        today = timezone.localdate()
        if value > today:
            raise forms.ValidationError("تاریخ تولد نمی‌تواند در آینده باشد.")
        if value.year < 1900:
            raise forms.ValidationError("تاریخ تولد معتبر نیست.")
        return value

    def clean_relationship(self):
        if self.lock_self:
            return Relationship.SELF
        return self.cleaned_data["relationship"]


class ReturnForm(forms.Form):
    comment = forms.CharField(
        label="دلیل بازگشت",
        min_length=3,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={"required": "دلیل بازگشت الزامی است."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comment"].widget.attrs["class"] = "input"


class ApproveForm(forms.Form):
    comment = forms.CharField(
        label="توضیح (اختیاری)",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2, "class": "input"}),
    )
