


## Setup

To start, let's create a new folder and a virtual environment. I use `pyenv virtualenv`:

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

Now let's set everything up to make our first test request to endpoint `GET /`. Here's a simple view for the app:

```python
# rbac/core/views.py
from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the core index.")
```

Set up a URL that points to the view:

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

## Custom user model

It's always a good idea in Django to create a custom model for users. It's hard to change the user model later and it isn't that much work to roll our own model.

Let's first explicitly define our authentication backend and the `User` model we want to use in `settings.py`:

```python
# rbac/settings.py
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
AUTH_USER_MODEL = 'core.User'
```

Now we create our custom user model in `models.py`:

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
        Creates and saves a User with the given email, name and password.
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

I will not explain this in detail as you can find a full example [here](https://docs.djangoproject.com/en/3.1/topics/auth/customizing/#a-full-example) in Django documentation. It suffices to say that our `User` has fields `email` and `name`. The field `email` must be unique and we use that as our user name. We use a UUID as primary key in all the models we create. We also create our own `UserManager` that we can use for creating new users as `User.objects.create_user(email=email, name=name, password=password)`.

Now we can create our first migration to create the user model in database:

```bash
$ python manage.py makemigrations
```