from datetime import date

from django.contrib.auth.models import Group, User

from renewals.models import Employee, InsuredPerson, Relationship, RenewalPeriod


def make_user(username, first_name="کاربر", last_name="آزمایشی"):
    return User.objects.create_user(
        username=username,
        password="test-pass-123",
        first_name=first_name,
        last_name=last_name,
    )


def make_employee(username="sara", personnel_code="1001", national_id="0012345679"):
    user = make_user(username, first_name="سارا", last_name="کریمی")
    employee = Employee.objects.create(
        user=user,
        personnel_code=personnel_code,
        first_name="سارا",
        last_name="کریمی",
        organizational_unit="فناوری اطلاعات",
    )
    person = InsuredPerson.objects.create(
        employee=employee,
        first_name="سارا",
        last_name="کریمی",
        national_id=national_id,
        relationship=Relationship.SELF,
        birth_date=date(1990, 5, 12),
    )
    return user, employee, person


def make_hr(username="hr"):
    user = make_user(username, first_name="مینا", last_name="نظری")
    group, _ = Group.objects.get_or_create(name="hr")
    user.groups.add(group)
    return user


def make_period(title, start, end, is_open=False):
    return RenewalPeriod.objects.create(
        title=title,
        coverage_start=start,
        coverage_end=end,
        is_open=is_open,
    )
