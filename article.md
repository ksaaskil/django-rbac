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

In this part one, we'll setup a Django project and app for our REST API. We'll add a custom user model and simple tests. You can find the accompanying code [in this repository](https://github.com/ksaaskil/django-rbac).

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

I move the app under the project to keep everything in one place. I don't expect to be adding any extra apps as multiple apps can [lead to problems](https://medium.com/@DoorDash/tips-for-building-high-quality-django-apps-at-scale-a5a25917b2b5) further down the road.

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

## Creating service layer

We create a service layer to add decoupling between views and models as suggested [in this article](https://medium.com/@DoorDash/tips-for-building-high-quality-django-apps-at-scale-a5a25917b2b5). Such a decoupling layer helps to keep models lean and all business logic in one place. Services are also very useful for testing, as we can create resources with services in similar fashion as real users would do.

Let's create services for creating users and finding users:

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

## Adding tests

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
```

## Conclusion

That concludes Part 1. In the next parts, we'll be adding views and tests for logging in users, preventing unwanted users from seeing resources, and finally adding granular role-based access control. See you later!


https://docs.djangoproject.com/en/3.2/topics/auth/default/#django.contrib.auth.authenticate

# Part 2

---
title: Custom user authentication in Django, with tests
published: true
description: Understand how authentication works and how to customize it
tags: python,django,tutorial
series: Granular role-based access control in Django
date: 2021-04-18
canonical_url: https://kimmosaaskilahti.fi/blog/2021-04-18-django-custom-authentication/
---

In the [previous part](https://dev.to/ksaaskil/setting-up-django-rest-api-with-custom-user-model-and-tests-5b8f), we created a custom user model in Django. In this part, I'd like to show how to roll custom authentication. Neither custom user model nor custom authentication are required for the granular role-based access control, but I'd like this series to be a complete tour of authentication and authorization in Django. The code accompanying the series can be found in [GitHub](https://github.com/ksaaskil/django-rbac). So let's get started!

## Django authentication 101

Authentication is the process of figuring out who the user claims to be and verifying the claim. In Django's authentication system, the "low-level" approach to verifying the user identity is to call [`authenticate`](https://docs.djangoproject.com/en/3.2/topics/auth/default/#django.contrib.auth.authenticate) from `django.contrib.auth.authenticate`. This function checks the user identity against each [authentication backend](https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#authentication-backends) configured in [`AUTHENTICATION_BACKENDS`](https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-AUTHENTICATION_BACKENDS) variable of `settings.py`.

By default, Django uses [`ModelBackend`](https://docs.djangoproject.com/en/3.2/ref/contrib/auth/#django.contrib.auth.backends.ModelBackend) as the only authentication backend. It's instructive to look into the implementation of `ModelBackend` in [GitHub](https://github.com/django/django/blob/main/django/contrib/auth/backends.py#L31):

```python
class ModelBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
    ...
```

The `ModelBackend` fetches the appropriate user from the backend using either the given `username` or the `USERNAME_FIELD` defined in user model. The backend then checks the password and also checks if the user can authenticate (checking if the user has `is_active` set to `True`). Quite simple, eh?

As we'll be authenticating our users with their username (e-mail) and password in this series, we could use the `ModelBackend`. However, it's instructive to write our own backend. Also, we'll get rid of all the unnecessary boilerplate in `ModelBackend` coming from Django's default permission system, which we won't need.

## Custom authentication backend

Every authentication backend in Django should have methods `authenticate()` and `get_user()`. The `authenticate()` method should check the credentials it gets and return a user object that matches those credentials if the credentials are valid. If the credentials are not valid, it should return `None`.

Here's a simple implementation of `CheckPasswordBackend`:

```python
# rbac/core/auth.py
import typing

from rbac.core.models import User
from rbac.core import services


class CheckPasswordBackend:
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
```

We use `services.find_user_by_email` method created in the previous post for fetching the user by email. If the password matches, we return the corresponding user. And that's it! Let's set Django to use this backend for authentication:

```python
# rbac/settings.py
AUTHENTICATION_BACKENDS = ["rbac.core.auth.CheckPasswordBackend"]
```

Now, whenever we call `authenticate` from `django.contrib.auth`, we're essentially calling `authenticate()` from `CheckPasswordBackend`.

Why did we also define `get_user` above in `CheckPasswordBackend`? That's a very good question. The answer is that Django documentation says it should be implemented, but I have no idea why. Please drop a comment if you know!

So now we have a great new authentication backend, how do we actually use it? We write a view `auth/login` that allows users to login with their email and password. If the user identity is verified, we log them in by calling [`login()`](https://docs.djangoproject.com/en/3.2/topics/auth/default/#django.contrib.auth.login). This creates a session for the user and stores the `sessionid` in a cookie, allowing the user to perform authenticated requests.

Before implementing the `login` view, let's be responsible developers and write tests. 

### Tests

To test login, we need to create a sample user. We do that in a `pytest` fixture:

```python
# tests/test_views.py
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
```

Now let's use this fixture in two tests. The first test verifies that logging in with invalid password returns 401:

```python
from django.test import Client

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
```

We're using the [Django test client](https://docs.djangoproject.com/en/3.2/topics/testing/tools/#the-test-client) for making requests from tests without actually running the server.

The second test verifies that login succeeds with valid credentials:

```python
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
```

At this point, we can start `pytest-watch` with the command `ptw -- tests/test_views.py` and code until the tests pass. If you haven't added `pytest-watch` to `requirements-dev.txt` yet, you should do it now.

### Login view

Let's now add the view for logging in a user. We expect users to post their email and password in a JSON request body. Here's how we parse the body, authenticate the user, and log them in:

```python
# rbac/core/auth.py
import json

from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def login_view(request):
    body = json.loads(request.body.decode())
    user = authenticate(request, email=body["email"], password=body["password"])

    if user:
        login(request, user)
        return HttpResponse("OK")
    else:
        return HttpResponse("Unauthorized", status=401)
```

If the call to `authenticate` returns a valid user, we login the user, create a session and set the session cookie. Otherwise, we return 401.

Now we need to define the endpoint for our view:

```python
# rbac/core/auth.py
from django.urls.conf import re_path

urlpatterns = [
    re_path("^login$", login_view),
]
```

We also need to define a new route named `auth` in `rbac/urls.py`:

```python
# rbac/core/urls.py

from django.conf.urls import include, re_path
from rbac.core import views

urlpatterns = [
    re_path(r"^$", views.index),
    re_path(r"^auth/", include("rbac.core.auth")),
]
```

With all this done, your tests should pass with flying colors.

Congratulations, you should now have a much deeper understanding of how authentication works in Django! Please leave a comment how you liked the article. In the next parts, we'll work towards role-based access control. See you next time!
