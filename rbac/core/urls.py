from django.conf.urls import include, re_path
from rbac.core import views

urlpatterns = [
    re_path(r"^$", views.index),
    re_path(r"^auth/", include("rbac.core.auth")),
]
