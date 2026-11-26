from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from renewals.models import Relationship, RenewalRequest, RequestStatus
from renewals.services import (
    AccessDenied,
    WorkflowError,
    add_person,
    approve,
    create_draft,
    include_person,
    remove_line,
    return_for_correction,
    submit,
    update_line,
)
from renewals.tests.helpers import make_employee, make_hr, make_period
from renewals.validators import validate_national_id


class RuleTests(TestCase):
    def setUp(self):
        self.employee_user, self.employee, self.self_person = make_employee()
        self.hr = make_hr()
        self.period = make_period("تمدید ۱۴۰۵", date(2026, 3, 21), date(2027, 3, 20), is_open=True)

    def test_closed_period_rejects_a_new_request(self):
        self.period.is_open = False
        self.period.save(update_fields=["is_open"])
        with self.assertRaises(WorkflowError):
            create_draft(self.employee, self.period, self.employee_user)

    def test_database_blocks_a_second_request_for_the_same_employee_and_period(self):
        create_draft(self.employee, self.period, self.employee_user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RenewalRequest.objects.create(employee=self.employee, period=self.period)

    def test_submitted_request_cannot_be_edited_or_approved_twice(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        line = renewal_request.coverage_lines.get()
        submit(renewal_request, self.employee_user)
        with self.assertRaises(WorkflowError):
            update_line(
                line,
                self.employee_user,
                {
                    "first_name": "سارا",
                    "last_name": "تغییریافته",
                    "national_id": "0012345679",
                    "relationship": Relationship.SELF,
                    "birth_date": date(1990, 5, 12),
                },
            )
        line.refresh_from_db()
        self.assertEqual(line.last_name, "کریمی")

        approve(renewal_request, self.hr, comment="")
        renewal_request.refresh_from_db()
        with self.assertRaises(WorkflowError):
            approve(renewal_request, self.hr)

    def test_draft_cannot_be_approved_and_return_needs_a_submitted_request(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        with self.assertRaises(WorkflowError):
            approve(renewal_request, self.hr)
        with self.assertRaises(WorkflowError):
            return_for_correction(renewal_request, self.hr, "زود است")

    def test_employee_cannot_approve_and_hr_cannot_submit_for_them(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        submit(renewal_request, self.employee_user)
        with self.assertRaises(AccessDenied):
            approve(renewal_request, self.employee_user)
        with self.assertRaises(AccessDenied):
            submit(renewal_request, self.hr)

    def test_self_line_cannot_be_removed(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        line = renewal_request.coverage_lines.get(relationship=Relationship.SELF)
        with self.assertRaises(WorkflowError):
            remove_line(line, self.employee_user)
        self.assertTrue(renewal_request.coverage_lines.filter(pk=line.pk).exists())

    def test_removed_dependent_can_be_added_back_to_the_same_request(self):
        child = self.employee.insured_people.create(
            first_name="آرمین",
            last_name="کریمی",
            national_id="0023456787",
            relationship=Relationship.CHILD,
            birth_date=date(2016, 7, 19),
        )
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        line = renewal_request.coverage_lines.get(person=child)
        remove_line(line, self.employee_user)
        restored = include_person(renewal_request, self.employee_user, child)
        self.assertEqual(restored.national_id, child.national_id)
        self.assertEqual(renewal_request.coverage_lines.filter(person=child).count(), 1)

    def test_national_id_cannot_be_repeated_with_different_digits(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        with self.assertRaises(WorkflowError):
            add_person(
                renewal_request,
                self.employee_user,
                {
                    "first_name": "محسن",
                    "last_name": "اعلایی",
                    "national_id": "۰۰۱۲۳۴۵۶۷۹",
                    "relationship": Relationship.SPOUSE,
                    "birth_date": date(1992, 1, 1),
                },
            )
        self.assertEqual(renewal_request.coverage_lines.count(), 1)

    def test_invalid_national_id_is_rejected(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        with self.assertRaises(WorkflowError):
            add_person(
                renewal_request,
                self.employee_user,
                {
                    "first_name": "مریم",
                    "last_name": "کریمی",
                    "national_id": "1234567890",
                    "relationship": Relationship.SPOUSE,
                    "birth_date": date(1991, 3, 15),
                },
            )
        with self.assertRaises(Exception):
            validate_national_id("0000000000")

    def test_only_one_period_can_be_open(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_period("دوره دیگر", date(2027, 3, 21), date(2028, 3, 20), is_open=True)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get("/employee/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_report_counts_approved_people(self):
        renewal_request = create_draft(self.employee, self.period, self.employee_user)
        add_person(
            renewal_request,
            self.employee_user,
            {
                "first_name": "مریم",
                "last_name": "کریمی",
                "national_id": "0087654326",
                "relationship": Relationship.SPOUSE,
                "birth_date": date(1991, 3, 15),
            },
        )
        submit(renewal_request, self.employee_user)
        approve(renewal_request, self.hr, comment="")
        self.client.force_login(self.hr)
        response = self.client.get(f"/hr/report/?period={self.period.pk}")
        self.assertContains(response, 'id="approved-people">2<')
        self.assertContains(response, 'id="status-approved">1<')


class SeedCommandTests(TestCase):
    def test_seed_command_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_demo")
        call_command("seed_demo")
        self.assertEqual(RenewalRequest.objects.filter(status=RequestStatus.APPROVED).count(), 2)
        self.assertEqual(RenewalRequest.objects.count(), 2)
        self.assertTrue(self.client.login(username="sara.karimi", password="Renew-Sara-1405"))
        self.assertTrue(self.client.login(username="hr.nazari", password="Renew-HR-1405"))
        self.assertTrue(self.client.login(username="reza.ahmadi", password="Renew-Reza-1405"))
