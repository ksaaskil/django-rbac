import json
import typing

from django.contrib.auth import authenticate, login
from django.http import HttpResponse, Http404
from django.urls.conf import re_path
from django.views.decorators.http import require_http_methods

from rbac.core.models import User
from rbac.core import services


class CheckPasswordBackend:
    def authenticate(
        self, request=None, email=None, password=None
    ) -> typing.Optional[User]:
        user = services.find_user_by_email(email=email)

        if not user:
            return None

        return user if user.check_password(password) else None

    def get_user(self, user_id) -> typing.Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


@require_http_methods(["POST"])
def login_view(request):
    body = json.loads(request.body.decode())
    user = authenticate(request, email=body["email"], password=body["password"])

    if user:
        login(request, user)
        return HttpResponse("OK")
    else:
        return HttpResponse("Unauthorized", status=401)


urlpatterns = [
    re_path("login", login_view),
]
