from django.test import Client
import pytest

from rbac.core.services import create_user

TEST_USER_NAME = "Jane Doe"
TEST_USER_EMAIL = "jane@example.org"
TEST_USER_PASSWORD = "aösdkfjgösdgäs"


@pytest.fixture
def sample_user():
    user = create_user(
        name=TEST_USER_NAME, email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD
    )
    return user


@pytest.mark.django_db
def test_login_succeeds_with_valid_credentials(sample_user):
    client = Client()
    assert "sessionid" not in client.cookies
    response = client.post(
        "/auth/login",
        dict(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert "sessionid" in client.cookies


@pytest.mark.django_db
def test_login_fails_with_invalid_credentials(sample_user):
    client = Client()
    response = client.post(
        "/auth/login",
        dict(email=TEST_USER_EMAIL, password="wrong-password"),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "sessionid" not in client.cookies
