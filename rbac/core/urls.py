from django.urls import path
from django.conf.urls import include, url, re_path
from rbac.core import views

urlpatterns = [
    re_path(r"^$", views.index),
    re_path(r"^auth/", include("rbac.core.auth")),
]
