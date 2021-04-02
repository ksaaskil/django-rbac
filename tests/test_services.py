import pytest

from rbac.core.services import create_user, find_user_by_email

@pytest.mark.django_db
def test_create_user():
    email = "test@example.com"
    name = "Jane Doe"
    password = "some-clever-password"

    user = create_user(email=email, name=name, password=password)

    assert user.email == email

    found_user = find_user_by_email(email=email)

    assert found_user == user
