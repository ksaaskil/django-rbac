import typing

from rbac.core.models import User

def create_user(email: str, name: str, password: str) -> User:
    return User.objects.create_user(email=email, name=name, password=password)

def find_user_by_email(email: str) -> typing.Optional[User]:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None
