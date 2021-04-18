import json
import typing
from django.contrib import auth

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth import authenticate, login, get_user_model
from django.http import HttpResponse, Http404
from django.urls import path
from django.conf.urls import include, url
from django.urls.conf import re_path
from django.views import View
from django.views.decorators.http import require_http_methods

from rbac.core import views
from rbac.core.models import User
from rbac.core import services


@require_http_methods(["POST"])
def login_view(request):
    body = json.loads(request.body.decode())
    user = authenticate(request, email=body["email"], password=body["password"])

    if user:
        login(request, user)
        return HttpResponse("OK")
    else:
        return HttpResponse("Unauthorized", status=401)


class CheckPasswordBackend(BaseBackend):
    def authenticate(
        self, request=None, email=None, password=None
    ) -> typing.Optional[User]:
        try:
            user = services.find_user_by_email(email=email)
        except Http404:
            return None

        return user if user.check_password(password) else None

    def get_user(self, user_id) -> typing.Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


urlpatterns = [
    re_path("login", login_view),
]
