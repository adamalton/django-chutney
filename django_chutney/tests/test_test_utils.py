# Standard Library
from unittest import skip

# Third Party
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import path
from django.utils.datastructures import MultiValueDict

# Django Chutney
from django_chutney.test_utils import FormHelper


_LAST_SUBMISSION = {
    "method": None,
    "data": MultiValueDict(),
}


def _reset_last_submission():
    _LAST_SUBMISSION["method"] = None
    _LAST_SUBMISSION["data"].clear()


def submit_form_view(request):
    """View to submit a form."""
    data = request.POST if request.method == "POST" else request.GET
    _LAST_SUBMISSION["data"].update(data)
    _LAST_SUBMISSION["method"] = request.method
    return HttpResponse("OK")


urlpatterns = [
    path("my-view/", submit_form_view),
]


class HelperTestCase(FormHelper, TestCase):
    """An example test case which we use to test FormHelper."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This doesn't get set up for us unless we actually run a test via this class
        self.client = Client()


@override_settings(ROOT_URLCONF=__name__)
class FormHelperTestCase(TestCase):
    """Test the FormHelper class."""

    def setUp(self):
        """Set up the test case."""
        _reset_last_submission()

    def _get_form_response(self, html: str):
        """Get a response from a form page."""
        request = {
            # This is what a Django TestCase.client.get() sets as `response.request`
            "PATH_INFO": "/my-view/",
            "REQUEST_METHOD": "GET",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "http",
            "QUERY_STRING": "",
        }
        # Wrap the HTML so that the <form> is *within* the html and can be selected
        html = f"<html><body>{html}</body></html>"
        response = HttpResponse(html)
        response.request = request
        return response

    def _get_submitted_data(self, form_html: str, data: dict = None):
        """Given the HTML of a form, and data to submit, return the data that `submit_form` submits."""
        data = data or {}
        form_response = self._get_form_response(form_html)
        helper = HelperTestCase()
        response = helper.submit_form(form_response, "form", data)
        self.assertIn(response.status_code, (200, 302), response.content.decode("utf8"))
        submitted_data = _LAST_SUBMISSION["data"].copy()
        return submitted_data

    def test_submits_via_correct_form_method(self):
        """Test that the submit_form method submits via the correct form method."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text">
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {"my-text": "my value"})
        self.assertEqual(_LAST_SUBMISSION["method"], "POST")
        self.assertEqual(set(submitted_data.keys()), {"my-text"})
        self.assertEqual(submitted_data["my-text"], "my value")

    def test_submits_supplied_data(self):
        """Test that the submit_form method submits the supplied data."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text">
                <textarea name="my-textarea"></textarea>
            </form>
        """
        form_data = {
            "my-text": "my value",
            "my-textarea": "my textarea value",
        }
        submitted_data = self._get_submitted_data(form_html, form_data)
        self.assertEqual(set(submitted_data.keys()), set(form_data.keys()))
        for key, value in form_data.items():
            self.assertEqual(submitted_data[key], value)

    @skip("Not all of this functionality works yet.")
    def test_submits_default_values(self):
        """Test that the submit_form method submits all the default values for the form."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text" value="some-value">
                <input type="checkbox" name="my-checkbox" value="some-value" checked>
                <input type="checkbox" name="my-checkbox" value="non-checked-value">
                <input type="radio" name="my-radio" value="some-value" checked>
                <input type="radio" name="my-radio" value="non-checked-value">
                <textarea name="my-textarea">some-value</textarea>
                <select name="my-select">
                    <option value="some-value" selected>Selected value</option>
                    <option value="non-checked-value">Non-checked value</option>
                </select>
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {})
        expected_data = {
            "my-text": "some-value",
            "my-checkbox": "some-value",
            "my-radio": "some-value",
            "my-textarea": "some-value",
            "my-select": "some-value",
        }
        self.assertEqual(sorted(submitted_data.keys()), sorted(expected_data.keys()))
        for key, value in expected_data.items():
            self.assertEqual(submitted_data[key], value)
