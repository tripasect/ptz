from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from renewals.models import CoverageLine, RenewalRequest


class RoleRequiredMixin(LoginRequiredMixin):
    """Send anonymous users to login. Show a Persian page when the role is wrong."""

    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self._role_ok(request.user):
            return render(request, "renewals/forbidden.html", status=403)
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)

    def _role_ok(self, user):
        raise NotImplementedError


class EmployeeRequiredMixin(RoleRequiredMixin):
    def _role_ok(self, user):
        return getattr(user, "employee", None) is not None


class HRRequiredMixin(RoleRequiredMixin):
    def _role_ok(self, user):
        from django.conf import settings

        return user.groups.filter(name=settings.HR_GROUP_NAME).exists()


def owned_request(user, pk):
    employee = getattr(user, "employee", None)
    if employee is None:
        return None
    return (
        RenewalRequest.objects.select_related("employee", "period")
        .filter(pk=pk, employee=employee)
        .first()
    )


def owned_line(user, request_pk, line_pk):
    employee = getattr(user, "employee", None)
    if employee is None:
        return None
    return (
        CoverageLine.objects.select_related("request", "request__employee", "request__period", "person")
        .filter(pk=line_pk, request_id=request_pk, request__employee=employee)
        .first()
    )


def missing(request):
    return render(request, "renewals/not_found.html", status=404)
