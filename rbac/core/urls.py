from django.urls import path
from rbac.core import views

urlpatterns = [
    path('', views.index)
]