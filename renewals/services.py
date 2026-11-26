"""State changes for a renewal request.

Views call these functions. Templates never decide whether a transition is legal.
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from renewals.models import (
    CoverageLine,
    Decision,
    DecisionAction,
    InsuredPerson,
    Relationship,
    RenewalPeriod,
    RenewalRequest,
    RequestStatus,
)
from renewals.validators import validate_national_id

class WorkflowError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class AccessDenied(WorkflowError):
    pass


def create_draft(employee, period, actor):
    _require_owner_employee(employee, actor)
    if not period.is_open:
        raise WorkflowError("دوره تمدید برای ثبت درخواست باز نیست.")
    if RenewalRequest.objects.filter(employee=employee, period=period).exists():
        raise WorkflowError("برای این دوره قبلاً درخواست ثبت شده است.")

    try:
        with transaction.atomic():
            renewal_request = RenewalRequest.objects.create(
                employee=employee,
                period=period,
                status=RequestStatus.DRAFT,
            )
            for person in employee.insured_people.all():
                _copy_line(renewal_request, person)
    except IntegrityError as exc:
        raise WorkflowError("برای این دوره قبلاً درخواست ثبت شده است.") from exc
    return renewal_request


def add_person(renewal_request, actor, payload):
    _require_owner(renewal_request, actor)
    _require_editable(renewal_request)
    data = _clean_member(payload)
    if (
        data["relationship"] == Relationship.SELF
        and renewal_request.employee.insured_people.filter(relationship=Relationship.SELF).exists()
    ):
        raise WorkflowError("اطلاعات خود کارمند از قبل ثبت شده است.")
    _reject_duplicate_national_id(renewal_request, data["national_id"])

    try:
        with transaction.atomic():
            person = InsuredPerson.objects.create(employee=renewal_request.employee, **data)
            line = _copy_line(renewal_request, person)
            _sync_employee_name(renewal_request.employee, line)
            renewal_request.save()
    except IntegrityError as exc:
        raise WorkflowError("این کد ملی قبلاً ثبت شده است.") from exc
    return line


def include_person(renewal_request, actor, person):
    _require_owner(renewal_request, actor)
    _require_editable(renewal_request)
    if person.employee_id != renewal_request.employee_id:
        raise AccessDenied("شما به این فرد دسترسی ندارید.")
    if renewal_request.coverage_lines.filter(person=person).exists():
        raise WorkflowError("این فرد از قبل در درخواست انتخاب شده است.")
    _reject_duplicate_national_id(renewal_request, person.national_id)
    with transaction.atomic():
        line = _copy_line(renewal_request, person)
        renewal_request.save()
    return line


def update_line(line, actor, payload):
    renewal_request = line.request
    _require_owner(renewal_request, actor)
    _require_editable(renewal_request)
    data = _clean_member(payload)
    if line.relationship == Relationship.SELF and data["relationship"] != Relationship.SELF:
        raise WorkflowError("نسبت خود کارمند قابل تغییر نیست.")
    if line.relationship != Relationship.SELF and data["relationship"] == Relationship.SELF:
        raise WorkflowError("نسبت خود فقط یک بار در درخواست ثبت می‌شود.")
    _reject_duplicate_national_id(renewal_request, data["national_id"], line=line, person=line.person)

    with transaction.atomic():
        for field, value in data.items():
            setattr(line, field, value)
        line.save()
        if line.person_id:
            person = line.person
            for field, value in data.items():
                setattr(person, field, value)
            try:
                with transaction.atomic():
                    person.save()
            except IntegrityError as exc:
                raise WorkflowError("این کد ملی قبلاً ثبت شده است.") from exc
        _sync_employee_name(renewal_request.employee, line)
        renewal_request.save()
    return line


def remove_line(line, actor):
    renewal_request = line.request
    _require_owner(renewal_request, actor)
    _require_editable(renewal_request)
    if line.relationship == Relationship.SELF:
        raise WorkflowError("حذف خود کارمند از پوشش این دوره مجاز نیست.")
    with transaction.atomic():
        line.delete()
        renewal_request.save()


def submit(renewal_request, actor):
    _require_owner(renewal_request, actor)
    if renewal_request.status not in (RequestStatus.DRAFT, RequestStatus.NEEDS_CORRECTION):
        raise WorkflowError("ارسال درخواست در این وضعیت مجاز نیست.")
    if not renewal_request.coverage_lines.filter(relationship=Relationship.SELF).exists():
        raise WorkflowError("درخواست باید شامل خود کارمند باشد.")

    comment = ""
    if renewal_request.status == RequestStatus.NEEDS_CORRECTION:
        comment = "ارسال مجدد پس از اصلاح"
    with transaction.atomic():
        renewal_request.status = RequestStatus.SUBMITTED
        renewal_request.submitted_at = timezone.now()
        renewal_request.save()
        Decision.objects.create(
            request=renewal_request,
            action=DecisionAction.SUBMITTED,
            actor=actor,
            comment=comment,
        )
    return renewal_request


def return_for_correction(renewal_request, actor, comment):
    _require_hr(actor)
    if renewal_request.status != RequestStatus.SUBMITTED:
        raise WorkflowError("فقط درخواست ارسال‌شده را می‌توان برای اصلاح برگرداند.")
    reason = (comment or "").strip()
    if len(reason) < 3:
        raise WorkflowError("دلیل بازگشت الزامی است.")
    with transaction.atomic():
        renewal_request.status = RequestStatus.NEEDS_CORRECTION
        renewal_request.save()
        Decision.objects.create(
            request=renewal_request,
            action=DecisionAction.RETURNED,
            actor=actor,
            comment=reason,
        )
    return renewal_request


def approve(renewal_request, actor, comment=""):
    _require_hr(actor)
    if renewal_request.status != RequestStatus.SUBMITTED:
        raise WorkflowError("فقط درخواست ارسال‌شده قابل تأیید نهایی است.")
    note = (comment or "").strip()
    with transaction.atomic():
        renewal_request.status = RequestStatus.APPROVED
        renewal_request.save()
        Decision.objects.create(
            request=renewal_request,
            action=DecisionAction.APPROVED,
            actor=actor,
            comment=note,
        )
    return renewal_request


def open_period():
    return RenewalPeriod.objects.filter(is_open=True).first()


def _copy_line(renewal_request, person):
    return CoverageLine.objects.create(
        request=renewal_request,
        person=person,
        first_name=person.first_name,
        last_name=person.last_name,
        national_id=person.national_id,
        relationship=person.relationship,
        birth_date=person.birth_date,
    )


def _clean_member(payload):
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    national_id = (payload.get("national_id") or "").strip()
    relationship = payload.get("relationship")
    birth_date = payload.get("birth_date")
    if not first_name or not last_name:
        raise WorkflowError("نام و نام خانوادگی الزامی است.")
    if relationship not in Relationship.values:
        raise WorkflowError("نسبت نامعتبر است.")
    if birth_date is None:
        raise WorkflowError("تاریخ تولد الزامی است.")
    if birth_date > timezone.localdate():
        raise WorkflowError("تاریخ تولد نمی‌تواند در آینده باشد.")
    if birth_date.year < 1900:
        raise WorkflowError("تاریخ تولد معتبر نیست.")
    try:
        validate_national_id(national_id)
    except ValidationError as exc:
        raise WorkflowError(exc.messages[0]) from exc
    return {
        "first_name": first_name,
        "last_name": last_name,
        "national_id": national_id,
        "relationship": relationship,
        "birth_date": birth_date,
    }


def _reject_duplicate_national_id(renewal_request, national_id, line=None, person=None):
    lines = renewal_request.coverage_lines.filter(national_id=national_id)
    if line is not None:
        lines = lines.exclude(pk=line.pk)
    if lines.exists():
        raise WorkflowError("این کد ملی در همین درخواست تکرار شده است.")
    people = InsuredPerson.objects.filter(national_id=national_id)
    if person is not None:
        people = people.exclude(pk=person.pk)
    if people.exists():
        raise WorkflowError("این کد ملی برای فرد دیگری ثبت شده است.")


def _sync_employee_name(employee, line):
    if line.relationship != Relationship.SELF:
        return
    employee.first_name = line.first_name
    employee.last_name = line.last_name
    employee.save(update_fields=["first_name", "last_name"])
    user = employee.user
    user.first_name = line.first_name
    user.last_name = line.last_name
    user.save(update_fields=["first_name", "last_name"])


def _require_editable(renewal_request):
    if not renewal_request.is_editable:
        raise WorkflowError("در این وضعیت ویرایش درخواست مجاز نیست.")


def _require_owner(renewal_request, actor):
    _require_owner_employee(renewal_request.employee, actor)


def _require_owner_employee(employee, actor):
    owned = getattr(actor, "employee", None)
    if owned is None or owned.pk != employee.pk:
        raise AccessDenied("شما به این درخواست دسترسی ندارید.")


def _require_hr(actor):
    from django.conf import settings

    group_name = getattr(settings, "HR_GROUP_NAME", "hr")
    if not actor.is_authenticated or not actor.groups.filter(name=group_name).exists():
        raise AccessDenied("فقط کارشناس منابع انسانی مجاز به این اقدام است.")
