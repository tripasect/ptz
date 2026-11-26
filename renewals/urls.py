from django.urls import path

from renewals.views import (
    EmployeeDashboardView,
    HRApproveView,
    HRReportView,
    HRRequestDetailView,
    HRRequestListView,
    HRReturnView,
    HomeView,
    LineAddView,
    LineEditView,
    LineIncludeView,
    LineRemoveView,
    RequestCreateView,
    RequestDetailView,
    RequestSubmitView,
    StaffLoginView,
    StaffLogoutView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("accounts/login/", StaffLoginView.as_view(), name="login"),
    path("accounts/logout/", StaffLogoutView.as_view(), name="logout"),
    path("employee/", EmployeeDashboardView.as_view(), name="employee_dashboard"),
    path("employee/requests/new/", RequestCreateView.as_view(), name="employee_request_create"),
    path("employee/requests/<int:pk>/", RequestDetailView.as_view(), name="employee_request_detail"),
    path("employee/requests/<int:pk>/submit/", RequestSubmitView.as_view(), name="employee_request_submit"),
    path("employee/requests/<int:pk>/lines/add/", LineAddView.as_view(), name="employee_line_add"),
    path(
        "employee/requests/<int:pk>/lines/include/<int:person_id>/",
        LineIncludeView.as_view(),
        name="employee_line_include",
    ),
    path(
        "employee/requests/<int:pk>/lines/<int:line_id>/edit/",
        LineEditView.as_view(),
        name="employee_line_edit",
    ),
    path(
        "employee/requests/<int:pk>/lines/<int:line_id>/remove/",
        LineRemoveView.as_view(),
        name="employee_line_remove",
    ),
    path("hr/", HRRequestListView.as_view(), name="hr_request_list"),
    path("hr/report/", HRReportView.as_view(), name="hr_report"),
    path("hr/requests/<int:pk>/", HRRequestDetailView.as_view(), name="hr_request_detail"),
    path("hr/requests/<int:pk>/return/", HRReturnView.as_view(), name="hr_request_return"),
    path("hr/requests/<int:pk>/approve/", HRApproveView.as_view(), name="hr_request_approve"),
]
