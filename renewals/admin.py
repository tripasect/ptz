from django.contrib import admin
from django.db import models

from renewals.dates import format_jalali
from renewals.forms import JalaliDateField
from renewals.models import CoverageLine, Decision, Employee, InsuredPerson, RenewalPeriod, RenewalRequest

JALALI_FIELDS = {models.DateField: {"form_class": JalaliDateField}}

admin.site.site_header = "سامانهٔ تمدید بیمهٔ تکمیلی"
admin.site.site_title = "سامانهٔ تمدید بیمهٔ تکمیلی"


class CoverageLineInline(admin.TabularInline):
    model = CoverageLine
    extra = 0
    formfield_overrides = JALALI_FIELDS


class DecisionInline(admin.TabularInline):
    model = Decision
    extra = 0
    readonly_fields = ("acted_at",)
    exclude = ("created_at",)

    @admin.display(description="زمان")
    def acted_at(self, obj):
        if obj is None or obj.pk is None:
            return ""
        return format_jalali(obj.created_at, with_time=True)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("personnel_code", "first_name", "last_name", "organizational_unit")
    search_fields = ("personnel_code", "first_name", "last_name")


@admin.register(InsuredPerson)
class InsuredPersonAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "national_id", "relationship", "born", "employee")
    search_fields = ("national_id", "first_name", "last_name")
    formfield_overrides = JALALI_FIELDS

    @admin.display(description="تاریخ تولد", ordering="birth_date")
    def born(self, obj):
        return format_jalali(obj.birth_date)


@admin.register(RenewalPeriod)
class RenewalPeriodAdmin(admin.ModelAdmin):
    list_display = ("title", "start_jalali", "end_jalali", "is_open")
    formfield_overrides = JALALI_FIELDS

    @admin.display(description="شروع پوشش", ordering="coverage_start")
    def start_jalali(self, obj):
        return format_jalali(obj.coverage_start)

    @admin.display(description="پایان پوشش", ordering="coverage_end")
    def end_jalali(self, obj):
        return format_jalali(obj.coverage_end)


@admin.register(RenewalRequest)
class RenewalRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "status", "sent_at", "opened_at")
    list_filter = ("status", "period")
    readonly_fields = ("sent_at", "opened_at")
    exclude = ("submitted_at", "created_at")
    inlines = [CoverageLineInline, DecisionInline]

    @admin.display(description="آخرین ارسال", ordering="submitted_at")
    def sent_at(self, obj):
        return format_jalali(obj.submitted_at, with_time=True)

    @admin.display(description="زمان ایجاد", ordering="created_at")
    def opened_at(self, obj):
        return format_jalali(obj.created_at, with_time=True)
