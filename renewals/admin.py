from django.contrib import admin

from renewals.models import CoverageLine, Decision, Employee, InsuredPerson, RenewalPeriod, RenewalRequest

admin.site.site_header = "داده آزمایشی تمدید بیمه"
admin.site.site_title = "تمدید بیمه"


class CoverageLineInline(admin.TabularInline):
    model = CoverageLine
    extra = 0


class DecisionInline(admin.TabularInline):
    model = Decision
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("personnel_code", "first_name", "last_name", "organizational_unit")
    search_fields = ("personnel_code", "first_name", "last_name")


@admin.register(InsuredPerson)
class InsuredPersonAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "national_id", "relationship", "employee")
    search_fields = ("national_id", "first_name", "last_name")


@admin.register(RenewalPeriod)
class RenewalPeriodAdmin(admin.ModelAdmin):
    list_display = ("title", "coverage_start", "coverage_end", "is_open")


@admin.register(RenewalRequest)
class RenewalRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "status", "submitted_at", "created_at")
    list_filter = ("status", "period")
    inlines = [CoverageLineInline, DecisionInline]
