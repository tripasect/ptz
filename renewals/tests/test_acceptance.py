from datetime import date

from django.test import TestCase

from renewals.models import Relationship, RenewalRequest, RequestStatus
from renewals.services import add_person, create_draft
from renewals.tests.helpers import make_employee, make_hr, make_period

SPOUSE = {
    "first_name": "مریم",
    "last_name": "کریمی",
    "national_id": "0087654326",
    "relationship": Relationship.SPOUSE,
    "birth_date": date(1991, 3, 15),
}


class AcceptanceTests(TestCase):
    def setUp(self):
        self.employee_user, self.employee, self.self_person = make_employee()
        self.other_user, self.other, _ = make_employee(
            username="reza",
            personnel_code="1002",
            national_id="0499370899",
        )
        self.hr = make_hr()
        self.period = make_period("تمدید ۱۴۰۵", date(2026, 3, 21), date(2027, 3, 20), is_open=True)

    def test_scenario_1_employee_adds_spouse_and_hr_approves(self):
        self.client.force_login(self.employee_user)
        self.client.post("/employee/requests/new/")
        renewal_request = RenewalRequest.objects.get(employee=self.employee, period=self.period)
        response = self.client.post(
            f"/employee/requests/{renewal_request.pk}/lines/add/",
            {
                "first_name": "مریم",
                "last_name": "کریمی",
                "national_id": "0087654326",
                "relationship": Relationship.SPOUSE,
                "birth_date": "1991-03-15",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(f"/employee/requests/{renewal_request.pk}/submit/")

        self.client.force_login(self.hr)
        self.client.post(
            f"/hr/requests/{renewal_request.pk}/approve/",
            {"comment": "مدارک کامل است"},
        )

        renewal_request.refresh_from_db()
        self.assertEqual(renewal_request.status, RequestStatus.APPROVED)
        self.assertTrue(
            renewal_request.coverage_lines.filter(relationship=Relationship.SPOUSE, first_name="مریم").exists()
        )
        actions = list(renewal_request.decisions.values_list("action", flat=True))
        self.assertEqual(actions, ["submitted", "approved"])

    def test_scenario_2_hr_returns_request_and_employee_resubmits(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        add_person(renewal_request, self.employee_user, SPOUSE)
        self.client.force_login(self.employee_user)
        self.client.post(f"/employee/requests/{renewal_request.pk}/submit/")

        self.client.force_login(self.hr)
        self.client.post(
            f"/hr/requests/{renewal_request.pk}/return/",
            {"comment": "نام همسر ناقص است"},
        )
        renewal_request.refresh_from_db()
        self.assertEqual(renewal_request.status, RequestStatus.NEEDS_CORRECTION)

        line = renewal_request.coverage_lines.get(relationship=Relationship.SPOUSE)
        self.client.force_login(self.employee_user)
        response = self.client.post(
            f"/employee/requests/{renewal_request.pk}/lines/{line.pk}/edit/",
            {
                "first_name": "مریم",
                "last_name": "محمدی",
                "national_id": "0087654326",
                "relationship": Relationship.SPOUSE,
                "birth_date": "1991-03-15",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(f"/employee/requests/{renewal_request.pk}/submit/")

        renewal_request.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(renewal_request.status, RequestStatus.SUBMITTED)
        self.assertEqual(line.last_name, "محمدی")
        self.assertEqual(
            list(renewal_request.decisions.values_list("action", flat=True)),
            ["submitted", "returned", "submitted"],
        )
        self.assertEqual(renewal_request.decisions.get(action="returned").comment, "نام همسر ناقص است")

    def test_scenario_3_employee_cannot_open_another_employees_request(self):
        own = create_draft(self.employee, self.period, self.employee_user)
        self.period.is_open = False
        self.period.save(update_fields=["is_open"])
        other_period = make_period("تمدید ویژه", date(2026, 3, 21), date(2027, 3, 20), is_open=True)
        other_request = create_draft(self.other, other_period, self.other_user)
        other_line = other_request.coverage_lines.get(relationship=Relationship.SELF)

        self.client.force_login(self.employee_user)
        detail = self.client.get(f"/employee/requests/{other_request.pk}/")
        edit = self.client.post(
            f"/employee/requests/{other_request.pk}/lines/{other_line.pk}/edit/",
            {
                "first_name": "نفوذ",
                "last_name": "غیرمجاز",
                "national_id": "0499370899",
                "relationship": Relationship.SELF,
                "birth_date": "1985-01-30",
            },
        )
        other_person = self.other.insured_people.get()
        include = self.client.post(f"/employee/requests/{own.pk}/lines/include/{other_person.pk}/")
        hr_page = self.client.get("/hr/")
        report_page = self.client.get("/hr/report/")

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(edit.status_code, 404)
        self.assertEqual(include.status_code, 404)
        self.assertEqual(hr_page.status_code, 403)
        self.assertEqual(report_page.status_code, 403)
        self.assertContains(detail, "پیدا نشد", status_code=404)
        other_line.refresh_from_db()
        self.assertEqual(other_line.first_name, "سارا")
        self.assertFalse(own.coverage_lines.filter(national_id="0499370899").exists())

    def test_scenario_4_second_request_in_the_same_period_is_rejected(self):
        self.client.force_login(self.employee_user)
        first = self.client.post("/employee/requests/new/")
        second = self.client.post("/employee/requests/new/", follow=True)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(RenewalRequest.objects.filter(employee=self.employee, period=self.period).count(), 1)
        self.assertContains(second, "قبلاً درخواست ثبت شده")

    def test_scenario_5_editing_the_new_period_keeps_the_previous_period(self):
        child = self.employee.insured_people.create(
            first_name="آرمین",
            last_name="کریمی",
            national_id="0023456787",
            relationship=Relationship.CHILD,
            birth_date=date(2016, 7, 19),
        )
        self.period.is_open = False
        self.period.save(update_fields=["is_open"])
        previous = make_period("تمدید ۱۴۰۴", date(2025, 3, 21), date(2026, 3, 20), is_open=True)
        old_request = create_draft(self.employee, previous, self.employee_user)
        self.client.force_login(self.employee_user)
        self.client.post(f"/employee/requests/{old_request.pk}/submit/")
        self.client.force_login(self.hr)
        self.client.post(f"/hr/requests/{old_request.pk}/approve/", {"comment": "تأیید دوره قبل"})

        previous.is_open = False
        previous.save(update_fields=["is_open"])
        self.period.is_open = True
        self.period.save(update_fields=["is_open"])

        self.client.force_login(self.employee_user)
        self.client.post("/employee/requests/new/")
        new_request = RenewalRequest.objects.get(employee=self.employee, period=self.period)
        new_child = new_request.coverage_lines.get(national_id="0023456787")
        self.client.post(
            f"/employee/requests/{new_request.pk}/lines/{new_child.pk}/edit/",
            {
                "first_name": "کیان",
                "last_name": "کریمی",
                "national_id": "0023456787",
                "relationship": Relationship.CHILD,
                "birth_date": "2016-07-19",
            },
        )

        old_child = old_request.coverage_lines.get(person=child)
        old_child.refresh_from_db()
        new_child.refresh_from_db()
        old_page = self.client.get(f"/employee/requests/{old_request.pk}/")

        self.assertEqual(old_child.first_name, "آرمین")
        self.assertEqual(new_child.first_name, "کیان")
        self.assertContains(old_page, "آرمین")
        self.assertNotContains(old_page, "کیان")
