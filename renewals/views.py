from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from renewals.access import (
    EmployeeRequiredMixin,
    HRRequiredMixin,
    missing,
    owned_line,
    owned_request,
)
from renewals.forms import ApproveForm, CoverageLineForm, ReturnForm
from renewals.models import InsuredPerson, RenewalPeriod, RenewalRequest, RequestStatus
from renewals.queries import employee_dashboard, hr_requests, period_report, request_detail
from renewals.services import (
    AccessDenied,
    WorkflowError,
    add_person,
    approve,
    create_draft,
    include_person,
    open_period,
    remove_line,
    return_for_correction,
    submit,
    update_line,
)


class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        from django.conf import settings

        if request.user.groups.filter(name=settings.HR_GROUP_NAME).exists():
            return redirect("hr_request_list")
        if getattr(request.user, "employee", None) is not None:
            return redirect("employee_dashboard")
        return render(request, "renewals/forbidden.html", status=403)


class StaffLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class StaffLogoutView(LogoutView):
    pass


class EmployeeDashboardView(EmployeeRequiredMixin, View):
    def get(self, request):
        context = employee_dashboard(request.user.employee)
        return render(request, "renewals/employee/dashboard.html", context)


class RequestCreateView(EmployeeRequiredMixin, View):
    def get(self, request):
        period = open_period()
        return render(
            request,
            "renewals/employee/request_create.html",
            {"open_period": period},
        )

    def post(self, request):
        period = open_period()
        if period is None:
            messages.error(request, "دوره تمدید بازی برای ثبت درخواست وجود ندارد.")
            return redirect("employee_dashboard")
        try:
            renewal_request = create_draft(request.user.employee, period, request.user)
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("employee_dashboard")
        messages.success(
            request,
            "پیش‌نویس ساخته شد. افراد تحت پوشش سال قبل روی این درخواست کپی شدند.",
        )
        return redirect("employee_request_detail", pk=renewal_request.pk)


class RequestDetailView(EmployeeRequiredMixin, View):
    def get(self, request, pk):
        renewal_request = owned_request(request.user, pk)
        if renewal_request is None:
            return missing(request)
        return render(
            request,
            "renewals/employee/request_detail.html",
            request_detail(renewal_request),
        )


class RequestSubmitView(EmployeeRequiredMixin, View):
    def post(self, request, pk):
        renewal_request = owned_request(request.user, pk)
        if renewal_request is None:
            return missing(request)
        try:
            submit(renewal_request, request.user)
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("employee_request_detail", pk=pk)
        messages.success(request, "درخواست برای منابع انسانی ارسال شد.")
        return redirect("employee_request_detail", pk=pk)


class LineAddView(EmployeeRequiredMixin, View):
    template_name = "renewals/employee/member_form.html"

    def get(self, request, pk):
        renewal_request = owned_request(request.user, pk)
        if renewal_request is None:
            return missing(request)
        blocked = _editable_redirect(request, renewal_request)
        if blocked:
            return blocked
        self_exists = renewal_request.employee.insured_people.filter(relationship="self").exists()
        form = CoverageLineForm(allow_self=not self_exists)
        return render(request, self.template_name, {"form": form, "renewal_request": renewal_request, "mode": "add"})

    def post(self, request, pk):
        renewal_request = owned_request(request.user, pk)
        if renewal_request is None:
            return missing(request)
        blocked = _editable_redirect(request, renewal_request)
        if blocked:
            return blocked
        self_exists = renewal_request.employee.insured_people.filter(relationship="self").exists()
        form = CoverageLineForm(request.POST, allow_self=not self_exists)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "renewal_request": renewal_request, "mode": "add"},
            )
        try:
            add_person(renewal_request, request.user, form.cleaned_data)
        except WorkflowError as exc:
            form.add_error(None, exc.message)
            return render(
                request,
                self.template_name,
                {"form": form, "renewal_request": renewal_request, "mode": "add"},
            )
        messages.success(request, "فرد به درخواست اضافه شد.")
        return redirect("employee_request_detail", pk=pk)


class LineIncludeView(EmployeeRequiredMixin, View):
    def post(self, request, pk, person_id):
        renewal_request = owned_request(request.user, pk)
        if renewal_request is None:
            return missing(request)
        person = InsuredPerson.objects.filter(
            pk=person_id,
            employee=request.user.employee,
        ).first()
        if person is None:
            return missing(request)
        try:
            include_person(renewal_request, request.user, person)
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("employee_request_detail", pk=pk)
        messages.success(request, "فرد به پوشش این دوره اضافه شد.")
        return redirect("employee_request_detail", pk=pk)


class LineEditView(EmployeeRequiredMixin, View):
    template_name = "renewals/employee/member_form.html"

    def get(self, request, pk, line_id):
        line = owned_line(request.user, pk, line_id)
        if line is None:
            return missing(request)
        blocked = _editable_redirect(request, line.request)
        if blocked:
            return blocked
        form = CoverageLineForm(initial=_line_initial(line), lock_self=line.relationship == "self")
        return render(
            request,
            self.template_name,
            {"form": form, "renewal_request": line.request, "mode": "edit", "line": line},
        )

    def post(self, request, pk, line_id):
        line = owned_line(request.user, pk, line_id)
        if line is None:
            return missing(request)
        blocked = _editable_redirect(request, line.request)
        if blocked:
            return blocked
        form = CoverageLineForm(
            request.POST,
            initial=_line_initial(line),
            lock_self=line.relationship == "self",
        )
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "renewal_request": line.request, "mode": "edit", "line": line},
            )
        try:
            update_line(line, request.user, form.cleaned_data)
        except WorkflowError as exc:
            form.add_error(None, exc.message)
            return render(
                request,
                self.template_name,
                {"form": form, "renewal_request": line.request, "mode": "edit", "line": line},
            )
        messages.success(request, "اطلاعات فرد در این درخواست به‌روز شد.")
        return redirect("employee_request_detail", pk=pk)


class LineRemoveView(EmployeeRequiredMixin, View):
    def post(self, request, pk, line_id):
        line = owned_line(request.user, pk, line_id)
        if line is None:
            return missing(request)
        try:
            remove_line(line, request.user)
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("employee_request_detail", pk=pk)
        messages.success(request, "فرد از پوشش این دوره خارج شد. سوابق دوره‌های قبل دست نخورده است.")
        return redirect("employee_request_detail", pk=pk)


class HRRequestListView(HRRequiredMixin, View):
    def get(self, request):
        period_id = request.GET.get("period") or ""
        status = request.GET.get("status") or ""
        periods = RenewalPeriod.objects.all()
        selected_period = None
        if period_id.isdigit():
            selected_period = periods.filter(pk=int(period_id)).first()
        context = {
            "requests": hr_requests(
                period_id=selected_period.pk if selected_period else None,
                status=status or None,
            ),
            "periods": periods,
            "statuses": RequestStatus.choices,
            "selected_period": period_id if selected_period else "",
            "selected_status": status if status in RequestStatus.values else "",
        }
        return render(request, "renewals/hr/request_list.html", context)


class HRRequestDetailView(HRRequiredMixin, View):
    def get(self, request, pk):
        renewal_request = (
            RenewalRequest.objects.select_related("employee", "period").filter(pk=pk).first()
        )
        if renewal_request is None:
            return missing(request)
        context = request_detail(renewal_request)
        context["return_form"] = ReturnForm()
        context["approve_form"] = ApproveForm()
        return render(request, "renewals/hr/request_detail.html", context)


class HRReturnView(HRRequiredMixin, View):
    def post(self, request, pk):
        renewal_request = get_object_or_404(RenewalRequest, pk=pk)
        form = ReturnForm(request.POST)
        if not form.is_valid():
            context = request_detail(renewal_request)
            context["return_form"] = form
            context["approve_form"] = ApproveForm()
            return render(request, "renewals/hr/request_detail.html", context)
        try:
            return_for_correction(renewal_request, request.user, form.cleaned_data["comment"])
        except AccessDenied as exc:
            messages.error(request, exc.message)
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("hr_request_detail", pk=pk)
        else:
            messages.success(request, "درخواست برای اصلاح به کارمند برگردانده شد.")
        return redirect("hr_request_detail", pk=pk)


class HRApproveView(HRRequiredMixin, View):
    def post(self, request, pk):
        renewal_request = get_object_or_404(RenewalRequest, pk=pk)
        form = ApproveForm(request.POST)
        if not form.is_valid():
            context = request_detail(renewal_request)
            context["approve_form"] = form
            context["return_form"] = ReturnForm()
            return render(request, "renewals/hr/request_detail.html", context)
        try:
            approve(renewal_request, request.user, form.cleaned_data["comment"])
        except WorkflowError as exc:
            messages.error(request, exc.message)
            return redirect("hr_request_detail", pk=pk)
        messages.success(request, "درخواست تأیید نهایی شد.")
        return redirect("hr_request_detail", pk=pk)


class HRReportView(HRRequiredMixin, View):
    def get(self, request):
        periods = list(RenewalPeriod.objects.all())
        period_id = request.GET.get("period") or ""
        period = None
        if period_id.isdigit():
            period = next((item for item in periods if item.pk == int(period_id)), None)
        if period is None:
            period = next((item for item in periods if item.is_open), None) or (periods[0] if periods else None)
        context = {"periods": periods, "report": period_report(period) if period else None}
        return render(request, "renewals/hr/report.html", context)


def _editable_redirect(request, renewal_request):
    if renewal_request.is_editable:
        return None
    messages.error(request, "در این وضعیت ویرایش درخواست مجاز نیست.")
    return redirect("employee_request_detail", pk=renewal_request.pk)


def _line_initial(line):
    return {
        "first_name": line.first_name,
        "last_name": line.last_name,
        "national_id": line.national_id,
        "relationship": line.relationship,
        "birth_date": line.birth_date,
    }
