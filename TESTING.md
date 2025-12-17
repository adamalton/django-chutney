Testing
=======

To run tests for local development:

* Install a virtualenv: `python -m venv .venv`
* Activate the virtualenv: `source .venv/bin/activate`
* Install this page and its requirements: `pip install -e .[bs4]`
* Run tests: `python runtests.py`