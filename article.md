---
title: Creating Django REST API with custom user model and tests
published: true
description: Prepare for change by building for flexibility
tags: python,django
series: Granular role-based access control in Django
date: 2021-04-02
canonical_url: https://kimmosaaskilahti.fi/blog/2021-04-02-django-custom-user/
---

In this short series of articles, I'd like to share how to implement granular, resource-level role-based access control in Django. We'll build a REST API that returns 401s (Unauthorized) for unauthenticated users, 404s for authenticated users not authorized to view given resources, and 403s (Forbidden) for users authorized to view resources but forbidden to perform given actions.

We'll be using vanilla Django without extra frameworks or dependencies throughout. This doesn't mean you shouldn't use publicly available packages, but sticking to pure Django is a good choice when you want to learn things and when you need the most flexibility. Remember, though, that user authentication is one place where you don't want to mess things up: the more code you write, the better test suite you'll need!

In this part one, we'll setup a Django project and app for our REST API. We'll add a custom user model and simple tests.

## Creating the project and app

To start, let's create a new folder and a virtual environment. I use [`pyenv virtualenv`](https://github.com/pyenv/pyenv-virtualenv) to create virtual environments:

```bash
$ mkdir django-rbac && cd django-rbac
$ pyenv virtualenv 3.8.1 django-rbac-3.8.1
$ pyenv local django-rbac.3.8.1
```

Let's install Django and create a project called `rbac`: 

```bash
# django-rbac/
$ printf "django==3.1.7\n" > requirements.txt
$ pip install -r requirements.txt
$ django-admin startproject rbac .
```

Modify `settings.py` so that it only contains the apps and middlewares we need:

```python
# rbac/settings.py
INSTALLED_APPS = [
    'rbac.core',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]
```

We'll create the `rbac.core` app soon below. We use Django's [authentication system](https://docs.djangoproject.com/en/3.1/topics/auth/default/) for authenticating users, which requires us to include `django.contrib.auth` app and `django.contrib.auth.middleware.AuthenticationMiddleware` middleware. We also need `django.contrib.sessions` app and `SessionMiddleware` for managing user sessions. We also include [`CommonMiddleware`](https://docs.djangoproject.com/en/3.1/ref/middleware/#module-django.middleware.common) and [`SecurityMiddleware`](https://docs.djangoproject.com/en/3.1/ref/middleware/#module-django.middleware.security) even if not strictly required. 

Our views and models will live under `core` app. Let's create such an app and move it under `rbac`:

```bash
$ python manage.py startapp core
$ mv core rbac/
```

Let us modify `apps.py` in the app to use name `rbac.core` instead of `core`:

```python
# rbac/core/apps.py
class CoreConfig(AppConfig):
    name = 'rbac.core'
```

Now let's set everything up for our first endpoint `GET /`. Here's a simple view for the app:

```python
# rbac/core/views.py
from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the core index.")
```

Set up a URL to point to the view:

```python
# rbac/core/urls.py
from django.urls import path

from rbac.core import views

urlpatterns = [
    path('', views.index)
]
```

Setup URLs in project to point to our new app:

```python
# rbac/urls.py
from django.urls import include, path

urlpatterns = [
    path('', include('rbac.core.urls')),
]
```

The project and app are now setup. Before moving further, let's create a custom model for users.

## Custom user model

It's always a good idea in Django to create a custom model for users. It's hard to change the user model later and it isn't that much work to roll our own model. A custom model gives the most flexibility later on.

Let's first explicitly define our authentication backend and the `User` model we want to use in `settings.py`:

```python
# rbac/settings.py
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
AUTH_USER_MODEL = 'core.User'
```

Now we create our custom user model in `models.py` by defining `User` and `UserManager`:

```python
# rbac/core/models.py
import uuid

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager
)

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        """
        Create and save a user with the given email, name and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            name=name
        )

        user.set_password(password)
        user.save()
        return user

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )

    name = models.CharField(max_length=32, blank=False, null=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email

```

I will not try to explain this in detail as you can find a full example [here](https://docs.djangoproject.com/en/3.1/topics/auth/customizing/#a-full-example) in Django documentation. Our `User` has fields `email` and `name`. The field `email` must be unique and we use that as our user name. We use a UUID as primary key in all the models we create. We also create our own `UserManager` that we can use for creating new users as `User.objects.create_user(email=email, name=name, password=password)`.

Now let's create our first migration to create the user model in database:

```bash
$ python manage.py makemigrations
```

At this point, you could configure your database. We'll be using `sqlite3` in this article for simplicity. See [this article](https://dev.to/ksaaskil/setting-up-django-app-with-postgres-database-and-health-check-2cpd) how to configure Django to use Postgres database and how to setup a simple health-check endpoint.

## Try it out

Let's run our server:

```bash
$ python manage.py runserver
```

Open another terminal tab and make a request to your server at `http://localhost:8000`:

```bash
$ curl http://localhost:8000
Hello, world. You're at the core index.
```

## Creating services and tests

We create a service layer to add decoupling between views and models. Let's create services for creating users and finding users:

```python
# rbac/core/services.py
import typing

from rbac.core.models import User

def create_user(email: str, name: str, password: str) -> User:
    return User.objects.create_user(email=email, name=name, password=password)

def find_user_by_email(email: str) -> typing.Optional[User]:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None
```

Now we can do the **very important** thing we know every developer must do and add tests for our project. Let's first install [`pytest`](https://docs.pytest.org/en/stable/) and [`pytest-django`](https://pypi.org/project/pytest-django/):

```bash
$ printf "pytest\npytest-django\n" > requirements-dev.txt
$ pip install -r requirements-dev.txt
```

Configure `pytest.ini`:

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = rbac.settings
```

Let's create a simple test for creating a user:

```python
# tests/test_services.py
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
```

Now you can run the test and see it pass:

```bash
$ pytest
============================================================================= test session starts ==============================================================================
platform darwin -- Python 3.8.1, pytest-6.2.2, py-1.10.0, pluggy-0.13.1
django: settings: rbac.settings (from ini)
rootdir: /Users/ksaaskil/git/django-rbac, configfile: pytest.ini
plugins: django-4.1.0
collected 1 item

tests/test_services.py .                                                                                                                                                 [100%]

============================================================================== 1 passed in 0.35s ===============================================================================
```

