#!/usr/bin/env python
"""Standalone Django test runner for django-chutney.

Usage:
    python runtests.py
    python runtests.py django_chutney.tests.test_test_utils
"""
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def main(argv=None):
    """Configure minimal Django settings and run the test suite."""
    argv = argv or sys.argv[1:]

    if not settings.configured:
        settings.configure(
            DEBUG=False,
            SECRET_KEY="test-secret-key",
            ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
            ROOT_URLCONF="django_chutney.tests.test_test_utils",
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django_chutney",
                "django_chutney.tests",
            ],
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            MIDDLEWARE=[],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "APP_DIRS": True,
                    "OPTIONS": {"context_processors": []},
                }
            ],
            DEFAULT_AUTO_FIELD="django.db.models.AutoField",
            USE_TZ=True,
        )

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1)
    failures = test_runner.run_tests(argv or ["django_chutney"])
    sys.exit(bool(failures))


if __name__ == "__main__":
    main()

