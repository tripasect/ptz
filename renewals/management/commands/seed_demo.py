"""Create the two demo roles and two renewal periods.

Re-running the command resets the demo passwords and will not duplicate an
existing history. Delete db.sqlite3 first if you want a clean database.
"""
from datetime import date

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from renewals.models import Employee, InsuredPerson, Relationship, RenewalPeriod
from renewals.services import approve, create_draft, submit

EMPLOYEE_PASSWORD = "Renew-Sara-1405"
OTHER_EMPLOYEE_PASSWORD = "Renew-Reza-1405"
HR_PASSWORD = "Renew-HR-1405"


class Command(BaseCommand):
    help = "ساخت کاربران آزمایشی کارمند و منابع انسانی، به همراه دو دوره تمدید."

    def handle(self, *args, **options):
        hr_user = _user(
            username="hr.nazari",
            password=HR_PASSWORD,
            first_name="مینا",
            last_name="نظری",
        )
        group, _ = Group.objects.get_or_create(name=settings.HR_GROUP_NAME)
        hr_user.groups.add(group)

        sara = _employee(
            username="sara.karimi",
            password=EMPLOYEE_PASSWORD,
            personnel_code="1001",
            first_name="سارا",
            last_name="کریمی",
            organizational_unit="فناوری اطلاعات",
        )
        reza = _employee(
            username="reza.ahmadi",
            password=OTHER_EMPLOYEE_PASSWORD,
            personnel_code="1002",
            first_name="رضا",
            last_name="احمدی",
            organizational_unit="مالی",
        )
        _person(sara, "سارا", "کریمی", "0012345679", Relationship.SELF, date(1990, 5, 12))
        _person(sara, "آرمین", "کریمی", "0023456787", Relationship.CHILD, date(2016, 7, 19))
        _person(reza, "رضا", "احمدی", "0499370899", Relationship.SELF, date(1985, 1, 30))
        _person(reza, "فاطمه", "احمدی", "0044455569", Relationship.PARENT, date(1958, 9, 1))

        previous, _ = RenewalPeriod.objects.get_or_create(
            title="تمدید ۱۴۰۴",
            defaults={
                "coverage_start": date(2025, 3, 21),
                "coverage_end": date(2026, 3, 20),
                "is_open": False,
            },
        )
        current, _ = RenewalPeriod.objects.get_or_create(
            title="تمدید ۱۴۰۵",
            defaults={
                "coverage_start": date(2026, 3, 21),
                "coverage_end": date(2027, 3, 20),
                "is_open": False,
            },
        )

        if previous.requests.exists():
            self.stdout.write(self.style.WARNING("درخواست‌های دوره قبل از قبل وجود دارند؛ تاریخچه دوباره ساخته نشد."))
        else:
            if RenewalPeriod.objects.filter(is_open=True).exclude(pk=previous.pk).exists():
                raise CommandError("یک دوره دیگر باز است. برای ساخت تاریخچه اولیه، پایگاه را از نو بسازید.")
            with transaction.atomic():
                previous.is_open = True
                previous.save(update_fields=["is_open"])
                for employee in (sara, reza):
                    renewal_request = create_draft(employee, previous, employee.user)
                    submit(renewal_request, employee.user)
                    approve(renewal_request, hr_user, comment="تأیید پوشش دوره قبل")
                previous.is_open = False
                previous.save(update_fields=["is_open"])
                current.is_open = True
                current.save(update_fields=["is_open"])
            self.stdout.write(self.style.SUCCESS("تاریخچه تأییدشده دوره ۱۴۰۴ ساخته شد و دوره ۱۴۰۵ باز شد."))

        self.stdout.write("")
        self.stdout.write("کارمند: sara.karimi / %s" % EMPLOYEE_PASSWORD)
        self.stdout.write("کارمند دوم (برای آزمون دسترسی): reza.ahmadi / %s" % OTHER_EMPLOYEE_PASSWORD)
        self.stdout.write("منابع انسانی: hr.nazari / %s" % HR_PASSWORD)
        self.stdout.write("همسر نمونه برای افزودن در دوره جدید: مریم کریمی، کد ملی 0087654326، تولد 1369/12/24")


def _user(username, password, first_name, last_name):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"first_name": first_name, "last_name": last_name},
    )
    user.first_name = first_name
    user.last_name = last_name
    user.set_password(password)
    user.save()
    return user


def _employee(username, password, personnel_code, first_name, last_name, organizational_unit):
    user = _user(username, password, first_name, last_name)
    employee, _ = Employee.objects.get_or_create(
        user=user,
        defaults={
            "personnel_code": personnel_code,
            "first_name": first_name,
            "last_name": last_name,
            "organizational_unit": organizational_unit,
        },
    )
    employee.personnel_code = personnel_code
    employee.first_name = first_name
    employee.last_name = last_name
    employee.organizational_unit = organizational_unit
    employee.save()
    return employee


def _person(employee, first_name, last_name, national_id, relationship, birth_date):
    person, _ = InsuredPerson.objects.get_or_create(
        national_id=national_id,
        defaults={
            "employee": employee,
            "first_name": first_name,
            "last_name": last_name,
            "relationship": relationship,
            "birth_date": birth_date,
        },
    )
    return person
