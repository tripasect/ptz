"""Renewal data model.

An employee has a living roster (`InsuredPerson`). A request does not point at
that roster alone. Each selected person is copied onto a `CoverageLine`.

Editing someone during this year's draft updates the current line and the
living roster. Lines already stored on earlier requests are separate rows and
stay as they were. That is what keeps last year's record recoverable.
"""
from django.conf import settings
from django.db import models


class Relationship(models.TextChoices):
    SELF = "self", "خود"
    SPOUSE = "spouse", "همسر"
    CHILD = "child", "فرزند"
    # The minimum field list names self/spouse/child. The business rules also
    # name parents, so parent is a real relationship and the README says so.
    PARENT = "parent", "والدین"


RELATION_SORT = {
    Relationship.SELF: 0,
    Relationship.SPOUSE: 1,
    Relationship.CHILD: 2,
    Relationship.PARENT: 3,
}


class RequestStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    SUBMITTED = "submitted", "ارسال‌شده"
    NEEDS_CORRECTION = "needs_correction", "نیازمند اصلاح"
    APPROVED = "approved", "تأیید نهایی"


EDITABLE_STATUSES = {RequestStatus.DRAFT, RequestStatus.NEEDS_CORRECTION}


class DecisionAction(models.TextChoices):
    SUBMITTED = "submitted", "ارسال"
    RETURNED = "returned", "بازگشت برای اصلاح"
    APPROVED = "approved", "تأیید نهایی"


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
    )
    personnel_code = models.CharField("کد پرسنلی", max_length=32, unique=True)
    first_name = models.CharField("نام", max_length=100)
    last_name = models.CharField("نام خانوادگی", max_length=100)
    organizational_unit = models.CharField("واحد سازمانی", max_length=150)

    class Meta:
        verbose_name = "کارمند"
        verbose_name_plural = "کارکنان"
        ordering = ["personnel_code"]

    def __str__(self):
        return f"{self.personnel_code} — {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class InsuredPerson(models.Model):
    """Current roster entry. Not the historical enrollment."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="insured_people",
        verbose_name="کارمند",
    )
    first_name = models.CharField("نام", max_length=100)
    last_name = models.CharField("نام خانوادگی", max_length=100)
    national_id = models.CharField("کد ملی", max_length=10, unique=True)
    relationship = models.CharField("نسبت", max_length=16, choices=Relationship.choices)
    birth_date = models.DateField("تاریخ تولد")

    class Meta:
        verbose_name = "فرد بیمه‌شده"
        verbose_name_plural = "افراد بیمه‌شده"
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(relationship=Relationship.SELF),
                name="one_self_per_employee",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class RenewalPeriod(models.Model):
    title = models.CharField("عنوان دوره", max_length=150, unique=True)
    coverage_start = models.DateField("شروع پوشش")
    coverage_end = models.DateField("پایان پوشش")
    is_open = models.BooleanField(
        "باز برای ثبت درخواست",
        default=False,
        help_text="فقط یک دوره می‌تواند باز باشد. درخواست جدید فقط روی دوره باز ساخته می‌شود.",
    )

    class Meta:
        verbose_name = "دوره تمدید"
        verbose_name_plural = "دوره‌های تمدید"
        ordering = ["-coverage_start"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(coverage_end__gte=models.F("coverage_start")),
                name="period_end_on_or_after_start",
            ),
            models.UniqueConstraint(
                fields=["is_open"],
                condition=models.Q(is_open=True),
                name="single_open_period",
            ),
        ]

    def __str__(self):
        return self.title


class RenewalRequest(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="کارمند",
    )
    period = models.ForeignKey(
        RenewalPeriod,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="دوره",
    )
    status = models.CharField(
        "وضعیت",
        max_length=32,
        choices=RequestStatus.choices,
        default=RequestStatus.DRAFT,
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("زمان به‌روزرسانی", auto_now=True)
    submitted_at = models.DateTimeField("آخرین ارسال", null=True, blank=True)

    class Meta:
        verbose_name = "درخواست تمدید"
        verbose_name_plural = "درخواست‌های تمدید"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period"],
                name="one_request_per_employee_period",
            ),
        ]

    def __str__(self):
        return f"{self.employee.full_name} — {self.period.title}"

    @property
    def is_editable(self):
        return self.status in EDITABLE_STATUSES

    @property
    def is_reviewable(self):
        return self.status == RequestStatus.SUBMITTED


class CoverageLine(models.Model):
    """Person as selected on one request, stored as a copy of their details."""

    request = models.ForeignKey(
        RenewalRequest,
        on_delete=models.CASCADE,
        related_name="coverage_lines",
        verbose_name="درخواست",
    )
    person = models.ForeignKey(
        InsuredPerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coverage_lines",
        verbose_name="فرد زنده",
    )
    first_name = models.CharField("نام", max_length=100)
    last_name = models.CharField("نام خانوادگی", max_length=100)
    national_id = models.CharField("کد ملی", max_length=10)
    relationship = models.CharField("نسبت", max_length=16, choices=Relationship.choices)
    birth_date = models.DateField("تاریخ تولد")

    class Meta:
        verbose_name = "فرد انتخاب‌شده"
        verbose_name_plural = "افراد انتخاب‌شده"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "national_id"],
                name="unique_national_id_per_request",
            ),
            models.UniqueConstraint(
                fields=["request"],
                condition=models.Q(relationship=Relationship.SELF),
                name="one_self_per_request",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} — {self.request_id}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Decision(models.Model):
    request = models.ForeignKey(
        RenewalRequest,
        on_delete=models.CASCADE,
        related_name="decisions",
        verbose_name="درخواست",
    )
    action = models.CharField("اقدام", max_length=16, choices=DecisionAction.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="renewal_decisions",
        verbose_name="اقدام‌کننده",
    )
    comment = models.TextField("توضیح", blank=True)
    created_at = models.DateTimeField("زمان", auto_now_add=True)

    class Meta:
        verbose_name = "تصمیم"
        verbose_name_plural = "تاریخچه تصمیم‌ها"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.request_id}"

    @property
    def actor_label(self):
        employee = getattr(self.actor, "employee", None)
        if employee is not None:
            return employee.full_name
        full_name = self.actor.get_full_name().strip()
        return full_name or self.actor.get_username()
