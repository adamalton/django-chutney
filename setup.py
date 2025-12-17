#!/usr/bin/env python
from setuptools import find_packages, setup
import os
import re

PACKAGES = find_packages()
REQUIREMENTS = ["django >=3.2,<6.0"]
TEST_REQUIREMENTS = ["BeautifulSoup4"]
EXTRAS_REQUIRE = {
    "bs4": ["BeautifulSoup4"],
}
CLASSIFIERS = [
    "License :: OSI Approved :: MIT License",
    "Framework :: Django",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]


DESCRIPTION = "Tasty accompaniments to go with the Django web framework."
LONG_DESCRIPTION = open(os.path.join(os.path.dirname(__file__), "README.md")).read()

VERSION = "{{VERSION_PLACEHOLDER}}"
if not re.match(r"^v\d+\.\d+\.\d+$", VERSION):
    # In tests, where we haven't replaced the version placeholder, just use a default version
    VERSION = "1.0.0"

setup(
    name="django-chutney",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Adam Alton",
    author_email="270255+adamalton@users.noreply.github.com",
    url="https://github.com/adamalton/django-chutney",
    packages=PACKAGES,
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    extras_require=EXTRAS_REQUIRE,
    # test_suite="runtests.runtests",
    keywords=["django"],
    classifiers=CLASSIFIERS,
)
