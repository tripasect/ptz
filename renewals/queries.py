"""Read models for the panels and the period report."""
from django.db.models import Count

from renewals.models import RELATION_SORT, CoverageLine, RenewalRequest, RequestStatus


def sort_members(items):
    return sorted(
        items,
        key=lambda item: (
            RELATION_SORT.get(item.relationship, 9),
            item.last_name,
            item.first_name,
        ),
    )


def employee_dashboard(employee):
    from renewals.services import open_period

    period = open_period()
    requests = list(employee.requests.select_related("period"))
    open_request = None
    if period is not None:
        open_request = next((item for item in requests if item.period_id == period.id), None)
    return {
        "employee": employee,
        "roster": sort_members(employee.insured_people.all()),
        "requests": requests,
        "open_period": period,
        "open_request": open_request,
    }


def request_detail(renewal_request):
    lines = sort_members(renewal_request.coverage_lines.all())
    selected_person_ids = [line.person_id for line in lines if line.person_id]
    available = sort_members(
        renewal_request.employee.insured_people.exclude(pk__in=selected_person_ids)
    )
    history = list(renewal_request.decisions.select_related("actor"))
    latest_return = next(
        (item for item in reversed(history) if item.action == "returned"),
        None,
    )
    return {
        "renewal_request": renewal_request,
        "lines": lines,
        "available_people": available,
        "history": history,
        "latest_return": latest_return,
    }


def hr_requests(period_id=None, status=None):
    queryset = RenewalRequest.objects.select_related("employee", "period").annotate(
        member_count=Count("coverage_lines")
    )
    if period_id:
        queryset = queryset.filter(period_id=period_id)
    if status in RequestStatus.values:
        queryset = queryset.filter(status=status)
    return queryset


def period_report(period):
    grouped = {
        row["status"]: row["total"]
        for row in RenewalRequest.objects.filter(period=period)
        .values("status")
        .annotate(total=Count("id"))
    }
    rows = [
        {"status": status, "label": label, "total": grouped.get(status, 0)}
        for status, label in RequestStatus.choices
    ]
    approved_people = CoverageLine.objects.filter(
        request__period=period,
        request__status=RequestStatus.APPROVED,
    ).count()
    return {
        "period": period,
        "rows": rows,
        "request_total": sum(row["total"] for row in rows),
        "approved_people": approved_people,
    }
